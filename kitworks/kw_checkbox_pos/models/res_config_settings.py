from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_kw_is_checkbox_rounding = fields.Boolean(
        related='pos_config_id.kw_is_checkbox_rounding', readonly=False)
    pos_kw_is_checkbox_check_in_pos = fields.Boolean(
        related='pos_config_id.kw_is_checkbox_check_in_pos', readonly=False)
