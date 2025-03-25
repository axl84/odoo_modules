import logging

from telebot import types
from odoo import models, api

_logger = logging.getLogger(__name__)


class ChatbotSurveyMixin(models.AbstractModel):
    _inherit = 'kw.chatbot.survey.mixin'

    # pylint: disable=R1702,R0911,R0912
    def start_quiz(self, conversation, bot, message, **kwargs):
        if self.get_provider(conversation) != 'telegram':
            return super().start_quiz(conversation, bot, message, **kwargs)
        _logger.info('___________TELEGRAM Start Quiz___________')
        if conversation.survey_question_id:
            question_id = conversation.survey_question_id
            if not kwargs.get('message_data'):
                message_data = conversation.telegram_get_message_data(message)
            else:
                message_data = kwargs.get('message_data')
            _logger.info(message_data)
            if question_id.suggested_answer_ids and question_id.is_search:
                if isinstance(message, types.CallbackQuery) \
                        and not kwargs.get('is_search'):
                    check_message_data = message_data
                    _logger.info(f'/action_quiz_{question_id.id}')
                    _logger.info(f'/search_quiz_{question_id.id}')
                    if check_message_data == f'/search_quiz_{question_id.id}':
                        return self.send_next_question(conversation)
                    if check_message_data == f'/action_quiz_{question_id.id}':
                        message_data = ''
                        if question_id.code:
                            message_data = self.get_action_code(
                                conversation=conversation,
                                question_id=question_id)

                            # It doesn't work for some reason
                            if isinstance(message_data, dict) \
                                    or isinstance(message_data, bool):
                                return False

                        if not message_data:
                            return super().start_quiz(
                                conversation, bot, message_data, **kwargs)
                    else:
                        return super().start_quiz(
                            conversation, bot, message, **kwargs)
                conversation.survey_search_value = message_data
                model = question_id.kw_search_model_id.model
                field = question_id.kw_search_field_id.name
                try:
                    if isinstance(message_data, str):
                        message_data = int(message_data)
                    else:
                        _logger.info('Message_data is not a string')
                except ValueError:
                    _logger.info('Message_data is not int')
                search_domain = [(field, '=', message_data)]
                search_record = self.env[model].search(search_domain)
                if question_id.is_update_suggested_answer:
                    if len(question_id.suggested_answer_ids) > 2000:
                        conversation.send_message(
                            text=question_id.kw_field_waiting_message)
                    question_id.update_value_suggested()
                suggested_value = question_id.suggested_answer_ids.search([
                    ('question_id', '=', question_id.id),
                    ('value', 'in', search_record.mapped('name'))])
                if suggested_value:
                    self.question_transform(
                        conversation=conversation,
                        suggested_value=suggested_value,
                        val=question_id.get_question_data())
                    return True
                conversation.telegram_send_search_answer(
                    question_id=question_id)
                return False
        return super().start_quiz(conversation, bot, message, **kwargs)

    def send_search_message(self, question_id, conversation):
        search_field = question_id.kw_search_field_id
        search_message = question_id.kw_field_search_message
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        if search_field.ttype == 'selection':
            s_model = self.env[search_field.model]
            s_data = s_model.fields_get(allfields=[search_field.name])
            for but in s_data[search_field.name]['selection']:
                call_back = {
                    'search_message_step': self.id,
                    'message_data': but[0]}
                button = types.InlineKeyboardButton(
                    text=but[1], callback_data=str(call_back))
                buttons.append(button)
        if search_field.ttype in ['many2one', 'many2many', 'one2many']:
            records = self.env[search_field.relation].search([])
            for but in records:
                call_back = {
                    'search_message_step': self.id,
                    'message_data': but.id}
                text = but.with_context(
                    lang=conversation.sender_id.partner_id.lang).name
                button = types.InlineKeyboardButton(
                    text=text, callback_data=str(call_back))
                buttons.append(button)
        markup.add(*buttons)
        return conversation.send_message(
            text=search_message, reply_markup=markup, buttons=buttons)

    def send_next_question(self, conversation):
        if self.get_provider(conversation) != 'telegram':
            return super().send_next_question(conversation)
        if conversation.survey_question_id:
            question_id = conversation.survey_question_id
            if question_id.is_update_suggested_answer:
                if len(question_id.suggested_answer_ids) > 2000:
                    conversation.send_message(
                        text=question_id.kw_field_waiting_message)
                question_id.update_value_suggested()
            if question_id.suggested_answer_ids and question_id.is_search:
                self.send_search_message(
                    question_id=question_id, conversation=conversation)
                return False
        return super().send_next_question(conversation)

    @api.onchange('return_step_type')
    def _onchange_return_step_type(self):
        if self.return_step_type == 'notification':
            self.send_end_survey_button = False

    def kw_validate_answer_data(self, conversation, text):
        if self.get_provider(conversation) == 'telegram':
            if text:
                text = conversation.telegram_get_message_data(text)
        return super().kw_validate_answer_data(conversation, text)

    def kw_save_answer(self, conversation, text):
        self.ensure_one()
        if self.get_provider(conversation) == 'telegram':
            if text:
                text = conversation.telegram_get_message_data(text)
        user_input_id = conversation.sudo().user_input_id
        try:
            user_input_id.kw_chatbot_partner_id = \
                conversation.sender_id.partner_id.id
        except ValueError:
            _logger.info('Error in partner_id')
        try:
            user_input_id.kw_conversation_id = conversation.id
        except ValueError:
            _logger.info('Error in conversation_id')
        res = super().kw_save_answer(conversation, text)
        return res

    def question_transform(self, conversation, val, suggested_value=False):
        self.ensure_one()
        if self.get_provider(conversation) != 'telegram':
            return super().question_transform(
                conversation, val, suggested_value)
        if val.get('question_type') in ['multiple_choice', 'matrix']:
            return True
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        if val.get('title'):
            text = val.get('title')
            suggested_answer_ids = suggested_value
            if not suggested_answer_ids:
                suggested_answer_ids = val.get('suggested_answer_ids')
            for k in suggested_answer_ids:
                btn = types.InlineKeyboardButton(
                    text=k['value'], callback_data=k['id'])
                markup.add(btn)
            markup.add(*buttons)
            conversation.send_message(
                text=text, reply_markup=markup, buttons=buttons, )
        return True

    # pylint: disable=R0914
    def end_quiz(self, conversation, bot, message, **kwargs):
        step_id = kwargs.get('step_id')
        notification_id = kwargs.get('notification_id')
        if self.get_provider(conversation) != 'telegram' or not any(
                [step_id, notification_id]):
            return super().end_quiz(conversation, bot, message, **kwargs)
        conversation.sudo().is_quiz_start = False
        self.kw_save_answer(conversation, message)
        conversation.write({
            'survey_id': False,
            'survey_question_id': False,
            'tg_button_for_survey': False,
            'user_input_id': False, })
        lang = conversation.sender_id.partner_id.lang
        markup, buttons = None, []
        # Send a message after completing the survey
        message_end_survey = self.with_context(
            lang=lang).message_end_survey
        if self.return_step_type == 'step' and step_id:
            if self.send_end_survey_button:
                last_message = step_id.id if step_id else False
                markup = types.InlineKeyboardMarkup()
                text = self.with_context(
                    lang=lang).name_button_after_end_survey
                btn = types.InlineKeyboardButton(
                    text=text,
                    callback_data=f'/end, {last_message}', )
                markup.add(btn)
                markup.add(*buttons)
                conversation.send_message(
                    text=message_end_survey, reply_markup=markup,
                    buttons=buttons, )
            else:
                if message_end_survey:
                    conversation.send_message(
                        text=message_end_survey, )
                conversation.telegram_next_step(
                    step=step_id, bot=bot, message=message,
                    **{'redirect': step_id})
            return True
        if self.return_step_type == 'notification' and notification_id:
            record = kwargs.get('record_id')
            if record._name != notification_id.model_id.model:
                model = notification_id.model_id.model
                r_activity = conversation.model_activity_ids.filtered(
                    lambda x: x.res_model == model)
                if r_activity:
                    record = r_activity.get_record()
            if record:
                if message_end_survey:
                    conversation.send_message(
                        text=message_end_survey, )
                if record:
                    text = notification_id.prepare_notification_text(
                        record=record)
                    notification_id.send_message(
                        record=record, text=text,
                        conversation_id=conversation, )
                return True
        return super().end_quiz(conversation, bot, message, **kwargs)
