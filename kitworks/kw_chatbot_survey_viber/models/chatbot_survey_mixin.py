import logging
import ast

from odoo import models

_logger = logging.getLogger(__name__)


class ChatbotSurveyMixin(models.AbstractModel):
    _inherit = 'kw.chatbot.survey.mixin'

    # pylint: disable=R0914,R0912
    def start_quiz(self, conversation, bot, message, **kwargs):
        if self.get_provider(conversation) != 'viber':
            return super().start_quiz(conversation, bot, message, **kwargs)
        question_id = conversation.survey_question_id
        action_body = kwargs.get('action_body')
        if isinstance(action_body, dict) or action_body in [
                f'/action_quiz_{question_id.id}',
                f'/search_quiz_{question_id.id}']:
            if action_body == f'/search_quiz_{question_id.id}':
                return self.send_next_question(conversation)
            if action_body == f'/action_quiz_{question_id.id}':
                message_data = ''
                if question_id.code:
                    message_data = self.get_action_code(
                        conversation=conversation,
                        question_id=question_id)
                if not message_data:
                    return super().start_quiz(
                        conversation, bot, message_data, **kwargs)
            message_data = action_body.get('message_data')
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
            suggested_value = question_id.suggested_answer_ids.filtered(
                lambda x: x.value in search_record.mapped('name'))
            if suggested_value:
                self.question_transform(
                    conversation=conversation,
                    suggested_value=suggested_value,
                    val=question_id.get_question_data())
                return True
            conversation.viber_send_search_answer(
                question_id=question_id)
            return False
        text = message.get('text')
        try:
            text = ast.literal_eval(text)
            if hasattr(text, 'get'):
                if text.get('action_body'):
                    text = text.get('action_body')
                else:
                    text = text.get('text')
        except Exception as e:
            _logger.debug(e)
        try:
            action_body_dict = conversation.viber_str_to_dict(text)
        except Exception as e:
            _logger.debug(e)
        if isinstance(action_body_dict, dict):
            text = action_body_dict.get('message_data')
        return super().start_quiz(conversation, bot, text, **kwargs)

    def send_next_question(self, conversation):
        if self.get_provider(conversation) != 'viber':
            return super().send_next_question(conversation)
        if conversation.survey_question_id:
            question_id = conversation.survey_question_id
            if question_id.is_update_suggested_answer:
                if len(question_id.suggested_answer_ids) > 2000:
                    conversation.send_message(
                        text=question_id.kw_field_waiting_message)
                question_id.update_value_suggested()
            if question_id.suggested_answer_ids and question_id.is_search:
                self.send_viber_search_message(
                    question_id=question_id, conversation=conversation)
                return False
        return super().send_next_question(conversation)

    def question_transform(self, conversation, val, suggested_value=False):
        self.ensure_one()
        if self.get_provider(conversation) != 'viber':
            return super().question_transform(
                conversation, val, suggested_value)
        if val.get('question_type') in ['multiple_choice', 'matrix']:
            return True
        buttons = []
        if val.get('title'):
            text = val.get('title')
            suggested_answer_ids = suggested_value
            if not suggested_answer_ids:
                suggested_answer_ids = val.get('suggested_answer_ids')
            for k in suggested_answer_ids:
                suggested_id = k['id']
                buttons.append(self.viber_button_keyboard_values(
                    name=k['value'],
                    action_body=suggested_id))
            conversation.send_message(
                text=text)
            if buttons:
                conversation.send_rich_media_buttons_in_batches(buttons)
        return True

    def end_quiz(self, conversation, bot, message, **kwargs):
        result = super().end_quiz(conversation, bot, message, **kwargs)
        if self.get_provider(conversation) == 'viber':
            if self.send_end_survey_button:
                buttons = []
                lang = conversation.sender_id.partner_id.lang
                buttons.append(self.viber_button_keyboard_values(
                    name=self.with_context(
                        lang=lang).name_button_after_end_survey,
                    action_body='/end_quiz'))
                if buttons:
                    conversation.send_rich_media_buttons_in_batches(buttons)
            else:
                conversation.viber_next_step(
                    step=conversation.last_step_id, bot=bot, message=message)
        return result

    def send_viber_search_message(self, question_id, conversation):
        search_field = question_id.kw_search_field_id
        search_message = question_id.kw_field_search_message
        buttons = []
        if search_field.ttype == 'selection':
            s_model = self.env[search_field.model]
            s_data = s_model.fields_get(allfields=[search_field.name])
            for but in s_data[search_field.name]['selection']:
                call_back = {
                    'search_message_step': self.id,
                    'message_data': but[0]}
                buttons.append(self.viber_button_keyboard_values(
                    name=but[1],
                    action_body=call_back))
        if search_field.ttype in ['many2one', 'many2many', 'one2many']:
            records = self.env[search_field.relation].search([])
            for but in records:
                call_back = {
                    'search_message_step': self.id,
                    'message_data': but.id}
                text = but.with_context(
                    lang=conversation.sender_id.partner_id.lang).name
                buttons.append(self.viber_button_keyboard_values(
                    name=text,
                    action_body=call_back))
        res = conversation.send_message(text=search_message)
        if buttons:
            conversation.send_rich_media_buttons_in_batches(buttons)
        return res
