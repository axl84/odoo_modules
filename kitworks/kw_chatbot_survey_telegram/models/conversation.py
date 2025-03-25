import logging
import ast
from telebot import types
from odoo import models, fields, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    tg_button_for_survey = fields.Many2one(
        comodel_name='kw.chatbot.step.telegram.button', )

    def telegram_send_search_answer(self, question_id, message=None):
        if not message:
            message = question_id.kw_search_message
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton(
            text=question_id.kw_button_search_message,
            callback_data=f'/search_quiz_{question_id.id}', )
        markup.add(btn)
        btn = types.InlineKeyboardButton(
            text=question_id.kw_button_action_message,
            callback_data=f'/action_quiz_{question_id.id}', )
        markup.add(btn)
        markup.add(*buttons)
        self.send_message(
            text=message,
            reply_markup=markup, buttons=buttons, )

    def telegram_next_step(self, step, bot, message, **kwargs):
        if step.select_flow != 'survey' or kwargs.get('do_step'):
            return super().telegram_next_step(step, bot, message, **kwargs)
        return False

    def telegram_get_response(self, bot, message):
        text = self.telegram_get_message_data(message)
        if not text:
            text = ''
        if text and text == '/end_quiz':
            self.close_quiz()
            self.telegram_next_step(
                step=self.last_step_id, bot=bot,
                message=message, **{'do_step': True})
            return False
        if text not in [f'/action_quiz_{self.survey_question_id.id}',
                        f'/search_quiz_{self.survey_question_id.id}'] and all(
                ['/' in text, self.is_quiz_start, self.tg_button_for_survey]):
            self.sudo().close_quiz()
        return super().telegram_get_response(bot, message)

    def telegram_pre_response(self, bot, message):
        self.ensure_one()
        self_usr = self
        if not self.env.user:
            self_usr = self.with_user(SUPERUSER_ID)
        text = self_usr.telegram_get_message_data(message) or ''
        if text and '/start' in text:
            self_usr.sudo().write({
                'is_quiz_start': False,
                'survey_question_id': False,
                'question_and_page_ids': [(6, 0, [])],
                'user_input_id': False,
                'tg_button_for_survey': False,
                'survey_id': False, })

        result = super().telegram_pre_response(bot, message)

        if '/start_quiz' in text and not self_usr.sender_id.partner_id \
                and self_usr.survey_id.users_login_required:
            if self_usr.last_step_id.telegram_add_partner(
                    self_usr, bot, message):
                return True
        if '/start_quiz' in text or self_usr.is_quiz_start:
            if self_usr.tg_button_for_survey:
                button = self_usr.tg_button_for_survey
                bt_record = self_usr.env[self_usr.button_model].search([
                    ('id', '=', self_usr.button_res_id)])
                self_usr.tg_button_for_survey.start_quiz(
                    conversation=self_usr, bot=bot, message=message,
                    record_id=bt_record,
                    notification_id=button.survey_next_notification_id,
                    step_id=button.survey_next_step_id)
                return True
            if self_usr.last_step_id.start_quiz(
                    conversation=self_usr, bot=bot, message=message,
                    step_id=self_usr.last_step_id.go_to_step_id):
                return True
        return result

    # pylint: disable=R0911
    def do_action_on_button_click(self, json_data, bot=None, message=None):
        if json_data in [f'/action_quiz_{self.survey_question_id.id}',
                         f'/search_quiz_{self.survey_question_id.id}'] \
                and self.tg_button_for_survey:
            self.tg_button_for_survey.start_quiz(
                conversation=self, bot=bot, message=message)
            return True
        try:
            res = ast.literal_eval(json_data)
        except SyntaxError:
            _logger.info('json_data is not dict')
            return False
        _logger.info(f'res: {res}')
        if isinstance(res, int):
            return False
        if res.get('t'):
            return self.update_contact_field(res, bot, message)
        if res.get('message_data') and res.get('search_message_step'):
            step = self.env['kw.chatbot.step'].sudo().browse(
                res.get('search_message_step'))
            return step.start_quiz(
                conversation=self, bot=bot,
                message=message,
                is_search=True,
                message_data=res.get('message_data'))
        button_data = res.get('id_button')
        button = self.env['kw.chatbot.step.telegram.button'].sudo().browse(
            button_data)
        if button.state == 'survey':
            button_data = {
                'write_field':
                    button.related_fields_id.name
                    if button.related_fields_id else '',
                'tg_button_for_survey': button.id}
            if button.model_id:
                record_data = res.get('id_record')
                record = self.env[button.model_id.model].sudo().browse(
                    record_data)
                button_data.update({
                    'button_res_id': record.id, 'button_model': record._name})
            self.write(button_data)
            if button.notification_id.is_save_button_activity:
                if button.notification_id.model_id and record_data:
                    self._save_telegram_model_activity(
                        notification_id=button.notification_id,
                        res_model=button.notification_id.model_id.model,
                        res_id=record_data)
            button.start_quiz(conversation=self, bot=bot, message=message)
            return True
        if button.state == 'forward_step' \
                and self.last_step_id.select_flow == 'survey':
            return self.telegram_next_step(
                self.last_step_id, bot, message,
                **{'redirect': button.forward_step_id, 'do_step': True})
        return super().do_action_on_button_click(json_data, bot, message)
