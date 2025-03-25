import logging

from odoo import models

_logger = logging.getLogger(__name__)

INPUTS = ['free_input_single', 'question_name',
          'question_email', 'update_contact_field']


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    # pylint: disable=R0912
    # pylint: disable=R0915
    def wepster_get_response(self, conversation, message):
        self.ensure_one()
        if conversation.dialog_id:
            if self.step_type in INPUTS:
                conversation.send_message(text=self.text)
                conversation.input_step_id = self.id
                conversation.last_step_id = self.id
                return True
        if self.step_type == 'create_lead':
            self.create_lead(conversation)
            return True
        if self.step_type == 'forward_operator':
            operator = self.operator_forward(conversation, message)
            if conversation.wired_conversation_id:
                if not self.is_not_send_send_text:
                    conv_id = conversation.wired_conversation_id
                    subtype = self.env['mail.message.subtype'].search(
                        [('default', '=', True)], limit=1)
                    conversation.mail_channel_id.message_post(
                        author_id=conv_id.partner_id.id,
                        body=self.text,
                        message_type='comment',
                        subtype_id=subtype.id, )
                    if not conversation.chat_id.is_automatic_send_greet:
                        conversation.send_message(
                            text=self.text)
            if not operator and self.go_to_step_id:
                step = self.go_to_step_id
                conversation.wepster_next_step(
                    step=step, next_step=step, text='')
            return True
        conversation.wepster_out_message(self.text)
        conversation.send_message(
            text=self.text)
        if conversation.dialog_id:
            if self.step_type == 'text':
                return False
        return True
