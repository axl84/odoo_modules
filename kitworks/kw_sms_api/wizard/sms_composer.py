import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SendSMS(models.TransientModel):
    _inherit = 'sms.composer'

    kw_sms_provider_id = fields.Many2one(
        comodel_name='kw.sms.provider', string='SMS provider',
        domain=[('state', 'in', ['enabled', 'test'])])

    def _prepare_mass_sms_values(self, records):
        rs = {}
        # _logger.info(records)
        records = super()._prepare_mass_sms_values(records)
        # _logger.info(records)
        for r in records:
            k = records[r]
            k['kw_sms_provider_id'] = self.kw_sms_provider_id.id
            rs[r] = k
        return rs

    @api.model
    def default_get(self, vals):
        result = super().default_get(vals)

        provider_id = self.env['kw.sms.provider'].search(
            [('state', '=', 'enabled')])
        if len(provider_id) == 1:
            result['kw_sms_provider_id'] = provider_id.id

        return result
