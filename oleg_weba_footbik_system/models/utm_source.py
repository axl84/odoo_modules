from odoo import models, fields


class UtmSource(models.Model):
    _inherit = "utm.source"

    medium_id = fields.Many2one(comodel_name="utm.medium", string="Channel")
