import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ExciseBarcode(models.Model):
    _name = 'kw.excise.barcode'
    _description = 'Excise Barcode'

    name = fields.Char(
        string="Marks serial", )
