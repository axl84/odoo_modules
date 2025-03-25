import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CheckboxShift(models.Model):
    _inherit = 'kw.checkbox.shift'

    pos_session_id = fields.Many2one(
        comodel_name='pos.session', readonly=True, )
