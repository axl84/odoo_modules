from odoo import models, fields


class Skills(models.Model):
    _name = "skills"
    _description = "Skills"

    name = fields.Char(string="Skill")
