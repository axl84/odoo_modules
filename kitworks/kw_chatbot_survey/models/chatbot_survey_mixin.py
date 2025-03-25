import logging
from odoo import models, fields, api, _
from odoo.tools import datetime

_logger = logging.getLogger(__name__)


class ChatbotSurveyMixin(models.AbstractModel):
    _name = 'kw.chatbot.survey.mixin'
    _description = 'kw.chatbot.survey.mixin'

    def get_action_code(self, conversation, question_id):
        self.ensure_one()
        action = conversation.action_code(
            record=conversation,
            code=question_id.code.strip())
        if action and action.get('message'):
            return action.get('message')
        return False

    @staticmethod
    def get_provider(conversation_id):
        provider = ''
        if conversation_id:
            provider = conversation_id.chat_id.messenger_id.provider
        return provider

    survey_id = fields.Many2one(
        comodel_name='survey.survey', string='Survey', ondelete='cascade', )
    entity_model_id = fields.Many2one(
        related='survey_id.kw_entity_model_id',
        comodel_name='ir.model', string='Entity model', )
    message_start_survey = fields.Text(
        translate=True,
        default='Press the button to start the survey')
    message_end_survey = fields.Text(
        translate=True,
        default='Thank you for your participation')
    return_step_type = fields.Selection(
        selection=[('step', 'Step'), ('notification', 'Notification')],
        default='step', )
    name_button_start_survey = fields.Char(
        translate=True, default='Start Survey', )
    kw_close_quiz_button_name = fields.Char(
        translate=True, string='Close Quiz Button',
        default='Close Quiz')
    name_button_after_end_survey = fields.Char(
        translate=True, default='End Survey')
    send_end_survey_button = fields.Boolean(
        default='True')
    is_survey_send_text = fields.Boolean(
        default=False)

    @api.onchange('survey_id')
    def onchange_survey_for_message(self):
        for obj in self:
            if obj.survey_id:
                obj.message_start_survey = obj.survey_id.message_start_survey
                obj.message_end_survey = obj.survey_id.message_end_survey

    def check_date_format(self, date_string, f="%Y-%m-%d"):
        self.ensure_one()
        try:
            datetime.strptime(date_string, f)
            return True
        except ValueError:
            return False

    def kw_validate_answer_data(self, conversation, text):
        if conversation.survey_question_id.question_type == 'numerical_box':
            try:
                if isinstance(text, str):
                    text = text.replace(',', '.')
                text = float(text)
            except ValueError:
                conversation.send_message(
                    text=_('Numeric should be integer or float'))
                return False
        if conversation.survey_question_id.question_type == 'date':
            if not self.check_date_format(text):
                conversation.send_message(
                    text=_('Date should be in format "2021-12-30"'))
                return False
        if conversation.survey_question_id.question_type == 'datetime':
            if not self.check_date_format(text, '%Y-%m-%d %H:%M:%S'):
                conversation.send_message(
                    text=_('Datetime should be in format'
                           ' "2021-12-30 17:17:17"'))
                return False
        return True

    def kw_save_answer(self, conversation, text):
        self.ensure_one()
        if not conversation.user_input_id:
            return False
        if conversation.survey_question_id.question_type \
                == 'numerical_box' and isinstance(text, str):
            text = text.replace(',', '.')
        self.env['survey.user_input.line'].create({
            'user_input_id': conversation.user_input_id.id,
            'question_id': conversation.survey_question_id.id, })
        if text:
            conversation.sudo().user_input_id._save_lines(
                conversation.survey_question_id,
                text, '{}'.format(conversation.survey_question_id.id))
        if len(conversation.question_and_page_ids) == 0:
            user_input = conversation.sudo().user_input_id
            user_input._mark_done()
            if user_input.kw_entity_model and user_input.kw_entity_res_id:
                record = self.env[user_input.kw_entity_model].sudo().browse(
                    user_input.kw_entity_res_id)
                if record:
                    return record
        return False

    def prepare_data_quiz(self, conversation):
        survey_id = self.survey_id
        conversation.survey_id = survey_id.id
        if not survey_id:
            return False
        if not conversation.question_and_page_ids \
                and not conversation.is_quiz_start:
            conversation.sudo().is_quiz_start = True
            conversation.sudo().question_and_page_ids = \
                [(6, 0, survey_id.question_and_page_ids.filtered(
                    lambda x: not x.is_page).ids)]
            conversation.sudo().user_input_id = \
                self.env['survey.user_input'].sudo().create({
                    'survey_id': self.survey_id.id,
                    'state': 'in_progress'})
        if self.survey_id.users_login_required \
                and not conversation.user_input_id.partner_id:
            conversation.user_input_id.sudo().partner_id = \
                conversation.sender_id.partner_id
        return True

    def end_quiz(self, conversation, bot, message, **kwargs):
        conversation.sudo().is_quiz_start = False
        self.kw_save_answer(conversation=conversation, text=message)
        conversation.write({
            'survey_id': False,
            'survey_question_id': False,
            'user_input_id': False, })
        lang = conversation.sender_id.partner_id.lang
        text = self.with_context(
            lang=lang).message_end_survey
        conversation.send_message(
            text=text, )
        return True

    def question_transform(self, conversation, val):
        self.ensure_one()
        if val.get('question_type') in ['multiple_choice', 'matrix']:
            return False
        text = ''
        if val.get('title'):
            text = val.get('title')
            if text:
                conversation.send_message(text=text, )
        return text

    def start_quiz(self, conversation, bot, message, **kwargs):
        self.ensure_one()
        if not self.kw_validate_answer_data(conversation, message):
            return False
        if not self.prepare_data_quiz(conversation):
            return False
        if not conversation.question_and_page_ids \
                and conversation.is_quiz_start:
            self.end_quiz(
                conversation=conversation, bot=bot, message=message, **kwargs)
        if (conversation.question_and_page_ids and
                self.kw_validate_answer_data(conversation, message)):
            if conversation.survey_question_id:
                self.kw_save_answer(conversation=conversation, text=message)
            conversation.sudo().survey_question_id = \
                conversation.question_and_page_ids.ids[0]
            conversation.sudo().question_and_page_ids = \
                [(6, 0, conversation.question_and_page_ids.ids[1:])]
            self.send_next_question(conversation=conversation)
        return True

    def send_next_question(self, conversation):
        self.question_transform(
            conversation=conversation,
            val=conversation.survey_question_id.get_question_data())
        return True
