import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Notification(models.Model):
    _inherit = 'kw.chatbot.notification'

    def send_message(self, record, text, conversation_id, **kwargs):
        res = super().send_message(record, text, conversation_id, **kwargs)
        provider = conversation_id.chat_id.messenger_id.provider
        if self.is_file_send and self.file_fields_ids:
            for file_field in self.file_fields_ids:
                file = getattr(record, file_field.name)
                if file and provider == 'viber':
                    if file_field.ttype == 'binary':
                        _logger.info('Don\'t work')
                    else:
                        conversation_id.send_file(files=file)
        return res
