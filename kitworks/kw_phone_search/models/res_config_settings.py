from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def format_all_kw_phone_number_name(self):
        for obj in self.env['res.partner'].search([]):
            obj.format_kw_phone_number_name()
