import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    def facebook_get_response(self, bot, message):

        def check_context(context):
            try:
                index = int(context)
            except Exception as e:
                _logger.debug(e)
                index = False
            return index
        for step in self.dialog_id.chatbot_step_ids:

            text = self.facebook_get_message_data(message)
            if text and '/start' in text and len(text.split(' ')) > 1 \
                    and check_context(text.split(' ')[1]):
                link_tracker = self.env['link.tracker'].search([
                    ('id', '=', int(text.split(' ')[1]))])
                if link_tracker:
                    self.sudo().lint_tracker_id = link_tracker
                message['text'] = '/start'

            is_me = step.name == text
            if not is_me:
                is_me = self.env['kw.chatbot.step.alias'].sudo().search_count([
                    ('name', '=ilike', text), ('step_id', '=', step.id)])
            if not is_me:
                continue
            if step.facebook_get_response(
                    conversation=self, bot=bot, message=message):
                self.write({
                    'is_facebook_send': True,
                    'last_step_id': step.id, })
                break
            else:
                next_message = step.search([
                    ('sequence', '>', step.sequence),
                    ('dialog_id', '=', self.dialog_id.id)])
                for obj in next_message:
                    if obj.facebook_get_response(
                            conversation=self, bot=bot, message=message):
                        self.write({
                            'is_facebook_send': True,
                            'last_step_id': step.id, })
                        break
        return super().facebook_get_response(bot, message)
