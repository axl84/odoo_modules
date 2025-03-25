import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class Transaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def create(self, vals_list):
        vals_list['partner_country_id'] = self.env.company.country_id.id
        if vals_list.get('partner_id'):
            partner = self.env['res.partner'].sudo().browse(
                vals_list.get('partner_id'))
            if partner.country_id:
                vals_list['partner_country_id'] = partner.country_id.id
        return super().create(vals_list)
