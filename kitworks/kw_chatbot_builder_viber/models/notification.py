# flake8: noqa: E501
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)

INPUTS = ['free_input_single', 'question_name',
          'question_email']


class Notification(models.Model):
    _inherit = 'kw.chatbot.notification'

    viber_button_ids = fields.One2many(
        comodel_name='kw.chatbot.step.viber.keyboard',
        inverse_name='notification_id', )
    viber_message_not_found = fields.Text(
       default='Sorry, I don\'t understand you', translate=True)
    send_only_button = fields.Boolean(
        default=False)
    viber_button_count = fields.Integer(
        compute='_compute_viber_button_count', )

    def _compute_viber_button_count(self):
        for obj in self:
            obj.viber_button_count = \
                len(obj.viber_button_ids.filtered(
                    lambda x: not x.send_last).ids)

    def send_message(self, record, text, conversation_id, **kwargs):
        result = super().send_message(record, text, conversation_id, **kwargs)
        if conversation_id.chat_id.messenger_id.provider == 'viber' \
                and self.viber_button_ids \
                and self.trigger != 'on_external_event':
            buttons = []
            step_id = conversation_id.last_step_id
            for button in self.viber_button_ids.filtered(
                    lambda x: not x.send_last):
                if record and step_id:
                    call_back = {
                        'type': 'notification',
                        'id_record': record[0].id,
                        'id_button': button.id,
                        'id_conversation': conversation_id.id}
                    buttons.append(
                        step_id.viber_button_keyboard_values(
                            name=button.name,
                            action_body=str(call_back)))
            _logger.info(buttons)
            if buttons:
                conversation_id.send_rich_media_buttons_in_batches(buttons)
        return result
