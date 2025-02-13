from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    type_person = fields.Selection(
        selection=[
            ("child", "Child"),
            ("parent", "Parent")
        ],
        tracking=True
    )

    @api.onchange("company_type")
    def _onchange_type_person(self):
        if self.is_company:
            self.type_person = False
