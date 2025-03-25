import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    kw_sms_partner_phone = fields.Char(compute='_compute_get_phone_number')

    def _compute_get_phone_number(self):
        for obj in self:
            obj.kw_sms_partner_phone = obj.mobile or obj.phone
