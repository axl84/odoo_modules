

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = 'res.users'

    kw_checkbox_cashier_ids = fields.Many2many(
        comodel_name='kw.checkbox.cashier', string='Cashiers',
        relation='kw_checkbox_cashier_res_users_rel',
        column1='user_id', column2='cashier_id', )
