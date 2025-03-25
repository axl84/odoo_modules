import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CheckboxMixin(models.AbstractModel):
    _name = 'kw.checkbox.mixin'
    _description = 'Checkbox mixin'

    cb_id = fields.Char(
        string='CheckBox ID', )

    @api.model
    def get_by_cb_id(self, cb_id):
        return self.search([('cb_id', '=', cb_id)], limit=1)
