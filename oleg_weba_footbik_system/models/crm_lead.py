from odoo import models, fields, api, _
from ..models.res_partner import TYPE_PARENT, GENDER


class CrmLead(models.Model):
    _inherit = "crm.lead"

    birthday = fields.Date(string="Birthday", tracking=True)
    age = fields.Integer(compute="_compute_age", store=False)
    age_store = fields.Integer(string="Age", tracking=True)

    @api.depends("birthday")
    def _compute_age(self):
        for rec in self:
            age = self.env["res.partner"].get_age(rec.birthday)
            rec.age = age
            rec.age_store = age

    gender = fields.Selection(selection=GENDER, string="Gender", tracking=True)

    full_name_parent = fields.Char(string="Full name parent", tracking=True)
    type_parent = fields.Selection(
        selection=TYPE_PARENT, string="Type parent", tracking=True)
    gender_parent = fields.Selection(
        selection=GENDER, string="Gender parent", tracking=True)
    telephone_parent = fields.Char(string="Telephone parent", tracking=True)
    email_parent = fields.Char(string="Email parent", tracking=True)

    domain_source_id = fields.Binary(compute="_compute_domain_source_id")

    @api.depends("medium_id")
    def _compute_domain_source_id(self):
        for rec in self:
            if rec.medium_id:
                rec.domain_source_id = [("medium_id", "=", rec.medium_id.id)]
            else:
                rec.domain_source_id = []

    manager_promouter_id = fields.Many2one(
        comodel_name="hr.employee", string="Manager promouter", tracking=True)

    """Конвертація у нагоду"""
    def _handle_partner_assignment(self, force_partner_id=False, create_missing=True):
        for lead in self:
            if force_partner_id:
                lead.partner_id = force_partner_id
            if not lead.partner_id and create_missing:
                child = lead._create_customer()
                lead.partner_id = child.id

                # Custom
                child.write({
                    "company_type": "person",

                    "type_person": "child",
                    "birthday": lead.birthday,
                    "gender": lead.gender,

                    "medium_id": lead.medium_id.id,
                    "source_id": lead.source_id.id,
                    "manager_promouter_id": lead.manager_promouter_id.id,
                })

                # Custom
                self.env["res.partner"].create({
                    "company_type": "person",

                    "type_person": "parent",
                    "name": lead.full_name_parent,
                    "type_parent": lead.type_parent,
                    "gender": lead.gender_parent,
                    "phone": lead.telephone_parent,
                    "email": lead.email_parent,

                    "parent_id": child.id,
                })



