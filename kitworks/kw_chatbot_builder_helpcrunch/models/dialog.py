import logging

from odoo.tools.safe_eval import safe_eval

from odoo import models

_logger = logging.getLogger(__name__)


INPUTS = ['free_input_single', 'question_name',
          'question_email', 'update_contact_field']


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    def helpcrunch_get_response(self, conversation, message):
        _logger.info('helpcrunch_get_response')
        self.ensure_one()

        if conversation.sender_id.partner_id:
            domain = safe_eval(self.triggering_answer_domain) \
                if self.triggering_answer_domain else []
            check_partner = self.env['res.partner'].sudo().search(domain)
            if conversation.sender_id.partner_id not in check_partner:
                step = self.triggering_answer_redirect_step_id
                step.helpcrunch_get_response(conversation, message)
                if not conversation.input_step_id:
                    conversation.helpcrunch_next_step(step=step, text=message)
                return False

        if self.step_type == 'request_notification':
            _logger.info('request_notification step')
            return True

        if conversation.dialog_id:
            if self.step_type == 'update_contact_field' \
                    and self.step_type in INPUTS:
                conversation.send_message(text=self.text)
                conversation.input_step_id = self.id
                conversation.last_step_id = self.id
                return True

        if self.step_type == 'create_lead':
            _logger.info('create_lead step')
            lead = self.create_lead(conversation)
            hc_channel = conversation.sender_id.help_crunch_channel_id
            hc_channel_name = 'HelpCrunch/{} ({})'.format(
                hc_channel.type, hc_channel.display_name)
            source_id = self.env['utm.source'].search([
                ('name', '=', hc_channel_name)])
            if not source_id:
                source_id = self.env['utm.source'].create({
                    'name': hc_channel_name})
            lead.sudo().write({'source_id': source_id.id})
            return True
        if self.step_type == 'forward_operator':
            _logger.info('forward_operator step')
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
                    # if conversation.chat_id.is_automatic_send_greet:
                    #     conversation.send_message(
                    #         text=self.text)

            # go to step redirect_to step_id if the operator is not available
            if not operator and self.redirect_step_id:
                conversation.is_no_reply = True
                step = self.redirect_step_id
                conversation.helpcrunch_next_step(
                    step=step, next_step=step, text='')
            return True

        conversation.send_message(text=self.text)
        return True
