import logging

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class CheckboxOrganization(models.Model):
    _name = 'kw.checkbox.organization'
    _description = 'Checkbox organization'
    _sql_constraints = [
        ('cb_id_uniq', 'unique (cb_id)', _('CheckBox ID must be unique'))]

    name = fields.Char(
        string='Title', )
    active = fields.Boolean(
        default=True, )
    cb_id = fields.Char(
        string='CheckBox ID', readonly=True, )
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', change_default=True,
        default=lambda self: self.env.user.company_id.id, )
    edrpou = fields.Char(
        string='EDRPOU', )
    tax_number = fields.Char()

    is_log_enabled = fields.Boolean(
        default=False, )
