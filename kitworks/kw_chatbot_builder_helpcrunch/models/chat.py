import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    def search_dialog(self):
        if self.provider == 'help_crunch':
            dialog_ids = self.dialog_ids
            dialog_ids = dialog_ids.search([
                ('company_id', '=', self.env.company.id)])
            if dialog_ids:
                return dialog_ids.ids
            return dialog_ids
        return super().search_dialog()
