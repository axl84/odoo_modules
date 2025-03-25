import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Dialog(models.Model):
    _inherit = 'kw.chatbot.dialog'


# pylint: disable=lost-exception
class Step(models.Model):
    _name = 'kw.chatbot.step'
    _inherit = ['kw.chatbot.step', 'kw.chatbot.survey.mixin']

    # pylint: disable=R1705
    def viber_get_response(self, conversation, bot, message):
        self.ensure_one()
        message_text = message
        if isinstance(message, dict):
            message = conversation.viber_get_message(message)
            message_text = message.get('text')
        if self.select_flow == 'survey':
            if '/start_quiz' not in message.get('action_body'):
                conversation.close_quiz()
                lang = conversation.sender_id.partner_id.lang
                text_start = self.with_context(
                    lang=lang).name_button_start_survey
                text_end = self.with_context(
                    lang=lang).kw_close_quiz_button_name
                buttons = [
                    self.viber_button_keyboard_values(
                        name=text_start,
                        action_body=f'/start_quiz_{self.id}'),
                    self.viber_button_keyboard_values(
                        name=text_end,
                        action_body='/end_quiz')]
                rich_media = self.get_viber_rich_media(
                    text=False, buttons=buttons)
                text = self.with_context(
                    lang=lang).message_start_survey
                conversation.send_message(
                    text=text)
                conversation.send_message(
                    text=self.text, rich_media=rich_media, )
            else:
                conversation.write({'last_step_id': self.id})
                if self.is_survey_send_text:
                    conversation.send_message(text=self.text)
                self.start_quiz(
                    conversation=conversation, bot=bot, message=message,
                    action_body=conversation.get_action_body(message))
            return False
        else:
            return super().viber_get_response(
                conversation=conversation, bot=bot, message=message_text)
