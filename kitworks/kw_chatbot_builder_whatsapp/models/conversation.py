import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    # pylint: disable=R0911,R0912
    def whatsapp_get_response(self, message):
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if not self.wired_conversation_id:
                self.send_message(
                    text='Press /start to go online or /end to go offline')
        if self.sender_id:
            if self.sender_id.user_id:
                self.env.context = dict(
                    self.env.context, lang=self.sender_id.user_id.lang)
                self.env.user = self.sender_id.user_id
        text = message
        step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
            ('name', '=', text), ])
        trig_step = self.env['kw.chatbot.step'].sudo().search([
            ('alias_ids', 'in', step_alias.ids),
            ('dialog_id', '=', self.dialog_id.id)])
        if not trig_step and not self.wired_conversation_id:
            if not self.dialog_id.wait_start_message and text != '/end':
                text = '/start'
                step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
                    ('name', '=', text), ])
                trig_step = self.env['kw.chatbot.step'].sudo().search([
                    ('alias_ids', 'in', step_alias.ids),
                    ('dialog_id', '=', self.dialog_id.id)])
        if trig_step:
            if trig_step.whatsapp_get_response(
                    conversation=self, message=message):
                if self.input_step_id:
                    return None
            if trig_step.step_type in ["forward_operator", "create_lead"]:
                return None
            self.whatsapp_next_step(trig_step, message)
            return True

        if self.input_step_id:
            if self.input_step_id.step_type == 'update_contact_field':
                lang = self.sender_id.partner_id.lang
                text_resp = self.input_step_id.with_context(
                    lang=lang).msg_after_update_contact_field
                field = self.input_step_id.update_contact_field.name
                record = self.sender_id.partner_id
                value = text
                if record.write({field: value}):
                    self.send_message(text=text_resp)
                for add_tag in self.input_step_id.add_contact_tag_ids:
                    self.sender_id.partner_id.category_id = [
                        (4, add_tag.id)]
                for del_tag in self.input_step_id.remove_contact_tag_ids:
                    self.sender_id.partner_id.category_id = [
                        (3, del_tag.id)]
            self.env['kw.chatbot.input.question'].create({
                'question': self.input_step_id.text,
                'answer': text,
                'conversation_id': self.id, })
            self.write({
                'input_step_id': False,
                'last_step_id': self.input_step_id, })

            self.whatsapp_next_step(self.last_step_id, message)
            return True

        if text == '/end' and self.last_step_id:
            self.whatsapp_next_step(self.last_step_id, message)
            return True

        answer = self.env['chatbot.dialog.answer'].sudo().search(
            [('name', '=', text),
             ('dialog_step_id', '=', self.last_step_id.id), ])
        if answer and answer.refund_step_id:
            step = answer.refund_step_id
            if self.input_step_id:
                return None
            self.write({'last_step_id': step.id})
            step.whatsapp_get_response(conversation=self, message=message)
            if step.step_type not in ['update_contact_field']:
                self.whatsapp_next_step(step, message)
            return True

        return super().whatsapp_get_response(message)

    def whatsapp_next_step(self, step, message):
        next_step = step.go_to_step_id
        for obj in next_step:
            if obj.whatsapp_get_response(
                    conversation=self, message=message):
                if self.input_step_id or obj.step_type == 'forward_operator':
                    break
                else:
                    self.whatsapp_next_step(obj, message)

    def whatsapp_does_not_found(self):
        if not self.wired_conversation_id and \
                not self.chat_id.is_consultant_chat and \
                not self.operator_live_id:
            self.ensure_one()
            lang = self.sender_id.partner_id.lang
            alternative = _('There is no answer for your request')
            text = self.dialog_id.with_context(
                lang=lang).not_found_msg.strip() or alternative
            f_step = self.dialog_id.chatbot_step_ids.sorted(
                key=lambda r: r.sequence)[0]
            button = []
            for alias in f_step.alias_ids:
                button.append({
                    'id': alias.name,
                    'title': alias.name})
            self.send_message(text=text, button=button)
        return False

    def whatsapp_out_message(self, text=False):
        if not self.wired_conversation_id and not self.operator_live_id:
            res = super(Conversation, self).telegram_out_message(text=text)
            return res
        return False
