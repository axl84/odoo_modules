from odoo import models, fields


class ClassProgram(models.Model):
    _name = "class.program"
    _description = "Class Program"

    name = fields.Char(string="Name")
