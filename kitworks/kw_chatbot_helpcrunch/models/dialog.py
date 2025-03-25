import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Dialog(models.Model):
    _inherit = 'kw.chatbot.dialog'

    def unlink(self):
        messenger_id = self.env['kw.chatbot.messenger'].sudo().search([
            ('provider', '=', 'help_crunch')], limit=1)
        if messenger_id:
            for obj in self:
                help_crunch_chat = obj.chatbot_chat_ids.filtered(
                    lambda x: x.messenger_id == messenger_id.id)
                if help_crunch_chat:
                    help_crunch_chat.unlink()
        return super(Dialog, self).unlink()
