import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    enterprise_code = fields.Char(size=13, )
