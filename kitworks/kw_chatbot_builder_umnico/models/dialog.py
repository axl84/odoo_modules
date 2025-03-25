import logging

from odoo import models

_logger = logging.getLogger(__name__)

INPUTS = ['free_input_single', 'question_name',
          'question_email', 'update_contact_field']


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    # pylint: disable=R0912
    # pylint: disable=R0915
    def umnico_get_response(self, conversation, message):
        self.ensure_one()
        if conversation.dialog_id:
            if self.step_type in INPUTS:
                conversation.send_message(text=self.text)
                conversation.input_step_id = self.id
                conversation.last_step_id = self.id
                return True
        if self.step_type == 'create_lead':
            self.create_lead(conversation)

        if self.step_type == 'forward_operator':
            if not self.is_not_send_send_text:
                conversation.send_message(text=self.text)
            self.operator_forward(conversation, message)
            return True
        conversation.umnico_out_message(self.text)
        conversation.send_message(
            text=self.text)
        if conversation.dialog_id:
            if self.step_type == 'text':
                return False
        return True
