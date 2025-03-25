import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    def umnico_get_response(self, jsonrequest, ):
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if not self.wired_conversation_id:
                self.send_message(
                    text='Press /start to go online or /end to go offline')
        self.is_umnico_send = False
        text = jsonrequest.get('text')
        step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
            ('name', '=', text), ])
        trig_step = self.env['kw.chatbot.step'].sudo().search([
            ('alias_ids', 'in', step_alias.ids),
            ('dialog_id', '=', self.dialog_id.id)])
        if trig_step:
            if trig_step.umnico_get_response(conversation=self, message=text):
                self.write({
                    'is_umnico_send': True,
                    'last_step_id': trig_step.id, })
                if self.input_step_id:
                    return None
            self.umnico_next_step(trig_step, jsonrequest)
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
            self.umnico_next_step(self.last_step_id, text)
            return True

        if text == '/end' and self.last_step_id:
            self.umnico_next_step(self.last_step_id, text)
            return True
        if not step_alias:
            self.umnico_does_not_found()
            return True

        return super().umnico_get_response(jsonrequest)

    def umnico_next_step(self, step, jsonrequest):
        next_step = step.go_to_step_id
        for obj in next_step:
            # if obj.triggering_answer_ids and not step.triggering_answer_ids:
            #     break
            # if obj.triggering_answer_ids and step.triggering_answer_ids:
            #     continue
            if obj.umnico_get_response(conversation=self, message=jsonrequest):
                if self.input_step_id or obj.step_type == 'forward_operator':
                    break
                self.write({
                    'is_umnico_send': True,
                    'last_step_id': obj.id, })

    def umnico_does_not_found(self):
        if not self.wired_conversation_id and \
                not self.chat_id.is_consultant_chat and \
                not self.operator_live_id:
            return super(Conversation, self).umnico_does_not_found()
        return False

    def umnico_out_message(self, text=False):
        if not self.wired_conversation_id and not self.operator_live_id:
            return super(Conversation, self).umnico_out_message(text=text)
        return False
