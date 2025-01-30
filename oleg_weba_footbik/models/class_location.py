from odoo import models, fields


class ClassLocation(models.Model):
    _name = "class.location"
    _description = "Class Location"

    name = fields.Char(string="Name")
    company_id = fields.Many2one(comodel_name="res.company", string="Club")
