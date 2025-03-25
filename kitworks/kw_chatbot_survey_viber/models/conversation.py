import logging
import ast

from odoo import models

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    def viber_send_search_answer(self, question_id, message=None):
        if not message:
            message = question_id.kw_search_message
        buttons, rich_media = [], ''
        buttons.append(self.last_step_id.viber_button_keyboard_values(
            name=question_id.kw_button_search_message,
            action_body=f'/search_quiz_{question_id.id}'))
        buttons.append(self.last_step_id.viber_button_keyboard_values(
            name=question_id.kw_button_action_message,
            action_body=f'/action_quiz_{question_id.id}'))
        if buttons:
            rich_media = self.last_step_id.get_viber_rich_media(
                text=False, buttons=buttons)
            self.send_message(
                text=message)
            self.send_message(
                text=message, keyboard=rich_media, )
        return True

    def viber_next_step(self, step, bot, message, next_step=None):
        if not self.is_quiz_start:
            return super().viber_next_step(step, bot, message, next_step)
        return False

    def viber_get_response(self, bot, message):
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
        if text and text == '/end_quiz':
            self.close_quiz()
            self.viber_next_step(
                step=self.last_step_id, bot=bot, message=message)
            return False
        if self.is_quiz_start:
            try:
                self.viber_pre_response(bot, message)
            except Exception as e:
                _logger.info("++++++++++++++++++++++++++++++++++++++++++++")
                _logger.info(e)
                _logger.info("++++++++++++++++++++++++++++++++++++++++++++")
                self.send_message(text=self.survey_id.kw_message_error)
                buttons = self.last_step_id.viber_button_keyboard_values(
                    name=self.survey_id.kw_close_quiz_button_name,
                    action_body='/end_quiz')
                if buttons:
                    rich_media = self.last_step_id.get_viber_rich_media(
                        text=False, buttons=[buttons])
                    self.send_message(
                        text=self.survey_id.kw_close_quiz_button_name,
                        rich_media=rich_media, )
                self.close_quiz()
            return False
        return super().viber_get_response(bot, message)

    def viber_pre_response(self, bot, message):
        self.ensure_one()
        if message and '/start' in message:
            self.close_quiz()
        result = super().viber_pre_response(bot, message)
        if '/start_quiz' in message or self.is_quiz_start:
            if self.last_step_id.start_quiz(
                    conversation=self, bot=bot, message=message,
                    action_body=self.get_action_body(message)):
                return True
        return result

    def viber_does_not_found(self):
        if not self.survey_id and not self.is_quiz_start:
            return super(Conversation, self).viber_does_not_found()
        return None

    def get_action_body(self, message):
        try:
            if hasattr(message, 'get'):
                if message.get('action_body'):
                    message = message.get('action_body')
                else:
                    message = message.get('text')
                    message = self.viber_str_to_dict(message)
                    message = message.get('action_body')
        except Exception as e:
            _logger.debug(e)
            message = False
        return message
