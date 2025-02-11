import datetime

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

GENDER = [
    ("male", "Male"),
    ("female", "Female"),
]

TYPE_PARENT = [
    ("mother", "Mother"),
    ("father", "Father"),
    ("brother", "Brother"),
    ("sister", "Sister"),
    ("grandmother", "Grandmother"),
    ("grandfather", "Grandfather"),
    ("nanny", "Nanny"),
    ("guardian", "Guardian")
]


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

    birthday = fields.Date(string="Birthday", tracking=True)
    age = fields.Integer(compute="_compute_age", store=False)
    age_store = fields.Integer(string="Age", tracking=True)

    @api.depends("birthday")
    def _compute_age(self):
        for rec in self:
            age = rec.get_age(rec.birthday)
            rec.age = age
            rec.age_store = age

    @staticmethod
    def get_age(birthday):
        today = datetime.date.today()
        return relativedelta(today, birthday).years if birthday else 0

    gender = fields.Selection(selection=GENDER, string="Gender", tracking=True)
    type_parent = fields.Selection(
        selection=TYPE_PARENT, string="Type parent", tracking=True)

    medium_id = fields.Many2one(
        comodel_name="utm.medium", ondelete="set null", string="Channel")
    source_id = fields.Many2one(
        comodel_name="utm.source", ondelete="set null", string="Source")

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
