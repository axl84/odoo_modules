import logging
from odoo import models, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def add_conversation(self):
        self.ensure_one()
        return {
            'name': _('Conversation'),
            'view_mode': 'form',
            'res_model': 'kw.conversation.wizard.umnico',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_partner_id': self.id, }}
