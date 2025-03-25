import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    def instagram_get_response(self, bot, message):

        if self.dialog_id.bots_type == 'is_consultant_bot':
            return super().instagram_get_response(bot, message)

        self.is_instagram_send = False
        text = self.instagram_get_message_data(message)
        step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
            ('name', '=', text), ])
        trig_step = self.env['kw.chatbot.step'].sudo().search([
            ('alias_ids', 'in', step_alias.ids),
            ('dialog_id', '=', self.dialog_id.id)])

        if trig_step:
            if trig_step.instagram_get_response(
                    conversation=self, bot=bot, message=message):
                self.write({
                    'is_instagram_send': True,
                    'last_step_id': trig_step.id, })
                if self.input_step_id:
                    return None
            self.instagram_next_step(trig_step, bot, message)
            return True

        if self.input_step_id:
            self.env['kw.chatbot.input.question'].create({
                'question': self.input_step_id.text,
                'answer': text,
                'conversation_id': self.id, })
            self.write({
                'input_step_id': False,
                'last_step_id': self.input_step_id, })
            self.instagram_next_step(self.last_step_id, bot, message)
            return True

        if text == '/end' and self.last_step_id:
            self.instagram_next_step(self.last_step_id, bot, message)
            return True

        return super().instagram_get_response(bot, message)

    def instagram_next_step(self, step, bot, message):
        next_step = step.go_to_step_id
        for obj in next_step:
            if obj.triggering_answer_ids and not step.triggering_answer_ids:
                break
            if obj.triggering_answer_ids and step.triggering_answer_ids:
                continue
            if obj.instagram_get_response(
                    conversation=self, bot=bot, message=message):
                if self.input_step_id or obj.step_type == 'forward_operator':
                    break
                self.write({
                    'is_instagram_send': True,
                    'last_step_id': obj.id, })

    def instagram_does_not_found(self):
        if not self.wired_conversation_id and \
                not self.chat_id.is_consultant_chat and \
                not self.operator_live_id:
            return super(Conversation, self).instagram_does_not_found()
        return False
