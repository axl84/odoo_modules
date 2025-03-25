import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    def wepster_get_response(self, jsonrequest, ):
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if not self.wired_conversation_id:
                self.send_message(
                    text='Press /start to go online or /end to go offline')
        self.is_wepster_send = False
        text = jsonrequest['message']['text']
        _logger.info('text: %s', text)
        step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
            ('name', '=', text), ])
        trig_step = self.env['kw.chatbot.step'].sudo().search([
            ('alias_ids', 'in', step_alias.ids),
            ('dialog_id', '=', self.dialog_id.id)])
        if not trig_step and not self.wired_conversation_id:
            if not self.dialog_id.wait_start_message and text != '/end':
                trig_step = self.env['kw.chatbot.step'].sudo().search([
                    ('dialog_id', '=', self.dialog_id.id)]).sorted(
                    key=lambda r: r.sequence)[0]
        if trig_step:
            if trig_step.wepster_get_response(conversation=self, message=text):
                self.write({
                    'is_wepster_send': True,
                    'last_step_id': trig_step.id, })
                if self.input_step_id:
                    return None
            self.wepster_next_step(trig_step, jsonrequest)
            return True

        if self.input_step_id:
            answer = text
            self.env['kw.chatbot.input.question'].create({
                'question': self.input_step_id.text,
                'answer': answer,
                'conversation_id': self.id, })
            self.write({
                'input_step_id': False,
                'last_step_id': self.input_step_id, })
            self.wepster_next_step(self.last_step_id, text)
            return True

        if text == '/end' and self.last_step_id:
            self.wepster_next_step(self.last_step_id, text)
            return True
        res = super().wepster_get_response(jsonrequest)
        if not step_alias:
            self.wepster_does_not_found()
            return True
        return res

    def wepster_next_step(self, step, jsonrequest, next_step=None):
        if not next_step:
            next_step = step.go_to_step_id
        for obj in next_step:
            if obj.wepster_get_response(
                    conversation=self, message=jsonrequest):
                if self.input_step_id or obj.step_type == 'forward_operator':
                    self.write({
                        'is_wepster_send': True,
                        'last_step_id': obj.id, })
                    break
                else:
                    self.wepster_next_step(obj, jsonrequest)

    def wepster_does_not_found(self):
        if not self.wired_conversation_id and \
                not self.chat_id.is_consultant_chat and \
                not self.operator_live_id:
            return self.send_message(
                text='Sorry, I don\'t understand you. Please try again')
        return False

    def wepster_out_message(self, text=False):
        if not self.wired_conversation_id and not self.operator_live_id:
            return super(Conversation, self).wepster_out_message(text=text)
        return False


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    @api.model
    def create(self, vals_list):
        if vals_list.get('text') == '/end' \
                and vals_list.get('conversation_id'):
            conversation_id = self.env['kw.chatbot.conversation'].search(
                [('id', '=', vals_list.get('conversation_id'))])
            if conversation_id.wired_conversation_id:
                conv_id = conversation_id.wired_conversation_id
                obj = super().create(vals_list)
                if conv_id.chat_id.provider == 'wepster' \
                        and conv_id.last_step_id \
                        and conv_id.last_step_id.redirect_step_id:
                    conv_id.wepster_next_step(
                        step=conv_id.last_step_id,
                        next_step=conv_id.last_step_id.redirect_step_id,
                        text='')
                return obj
        return super().create(vals_list)
