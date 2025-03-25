import logging

from odoo import models, fields, exceptions, _

from .checkbox import CheckBoxApi

_logger = logging.getLogger(__name__)


class XReports(models.Model):
    _name = 'kw.checkbox.x.reports'
    _description = 'XReport'

    name = fields.Char(string='Report ID', required=True)
    cash_register_id = fields.Many2one('kw.checkbox.cash.register')
    payments = fields.Many2many('kw.checkbox.x.reports.payments')
    taxes = fields.Many2many('kw.checkbox.tax')
    sell_receipts_count = fields.Integer()
    return_receipts_count = fields.Integer()
    transfers_count = fields.Integer()
    transfers_sum = fields.Float()
    balance = fields.Float()
    initial = fields.Float()
    created_at = fields.Datetime()
    updated_at = fields.Datetime()

    html_text = fields.Html(string='Html', compute='_compute_print_report')

    def _compute_print_report(self):
        self.ensure_one()
        cashier_token = (
            self.cash_register_id.cashier_id.get_cashier_token())
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token,
            license_key=self.cash_register_id.license_key,
            test_mode=self.cash_register_id.company_id
            .kw_checkbox_mode != 'prod'
        )
        res = checkbox.get_print_report(report_id=self.name)
        self.html_text = '<pre class="tab">' + res.replace('\n',
                                                           '<br>') + "</pre>"

    def open_report(self):
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': f'/checkbox/report/kw_checkbox.'
                   f'action_x_report_for_check/{self.id}',
        }


class XReportsPayment(models.Model):
    _name = 'kw.checkbox.x.reports.payments'
    _description = 'Checkbox payment report'

    x_report_id = fields.Many2one(
        comodel_name='kw.checkbox.x.reports'
    )

    rec_id = fields.Char()
    code = fields.Char()
    type = fields.Char()
    label = fields.Char()
    sell_sum = fields.Integer()
    return_sum = fields.Integer()
    service_in = fields.Integer()
    service_out = fields.Integer()
