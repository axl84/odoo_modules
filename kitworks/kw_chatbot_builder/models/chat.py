import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    def search_dialog(self):
        if self.provider == 'odoo_livechat':
            dialog_ids = self.dialog_ids
            dialog_ids = dialog_ids.search([
                ('company_id', '=', self.env.company.id)])
            if dialog_ids:
                return dialog_ids.ids
            return dialog_ids
        return super().search_dialog()

    @api.depends('messenger_id', 'dialog_id')
    def _compute_messengers(self):
        for obj in self:
            if not obj.dialog_id:
                dialog_id = self.env['kw.chatbot.dialog'].sudo().search([
                    ('bots_type', '=', 'is_communication_bot'),
                    ('company_id', '=', self.env.company.id)], limit=1)
                obj.write({
                    'dialog_id': dialog_id.id})
        return super()._compute_messengers()
