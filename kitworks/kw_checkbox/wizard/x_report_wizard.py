import logging

from odoo import models, fields, exceptions, _

_logger = logging.getLogger(__name__)


class WizardPaymentLine(models.TransientModel):
    _name = 'kw.wizard.payment.line'
    _description = 'Checkbox payment report'
    _rec_name = 'rec_id'

    rec_id = fields.Char()

    code = fields.Char()

    type = fields.Char()

    provider_type = fields.Char()

    label = fields.Char()

    sell_sum = fields.Integer()

    return_sum = fields.Integer()

    service_in = fields.Integer()

    service_out = fields.Integer()

    cash_withdrawal = fields.Integer()

    cash_withdrawal_commission = fields.Integer()


class WizardTaxLine(models.TransientModel):
    _name = 'kw.wizard.tax.line'
    _description = 'Checkbox Tax report'
    _rec_name = 'rec_id'

    rec_id = fields.Char(
        string='Rec ID', )

    code = fields.Char()

    label = fields.Char()

    symbol = fields.Char()

    rate = fields.Float()

    extra_rate = fields.Integer()

    sell_sum = fields.Integer()
    rate_sell_sum = fields.Integer()
    extra_rate_sell_sum = fields.Integer()
    rate_return_sum = fields.Integer()
    extra_rate_return_sum = fields.Integer()

    return_sum = fields.Integer()

    decimal_sell_sum = fields.Integer()
    decimal_return_sum = fields.Integer()

    sales_turnover = fields.Integer()

    returns_turnover = fields.Integer()

    created_at = fields.Datetime()

    setup_date = fields.Datetime()

    no_vat = fields.Boolean()

    advanced_code = fields.Char()


class WizardXReport(models.TransientModel):
    _name = 'kw.wizard.x_report'
    _description = 'Checkbox X report'
    _rec_name = 'balance'

    rec_id = fields.Char(
        string='Rec ID', )

    sell_receipts_count = fields.Integer()

    return_receipts_count = fields.Integer()

    transfers_count = fields.Integer()

    transfers_sum = fields.Integer()

    balance = fields.Integer()

    initial = fields.Integer()

    created_at = fields.Datetime()

    updated_at = fields.Datetime()

    cash_register_id = fields.Many2one(
        comodel_name='kw.checkbox.cash.register',
        required=True, )
    tax_line_ids = fields.Many2many(
        comodel_name='kw.wizard.tax.line', )
    payment_line_ids = fields.Many2many(
        comodel_name='kw.wizard.payment.line', )

    def get_checkbox_payment(self, result):
        self.ensure_one()
        if result:
            list_payments = []
            for obj in result.get('payments'):
                obj['rec_id'] = obj.pop('id')
                for x in ['sell_sum', 'return_sum', 'service_in',
                          'service_out']:
                    obj[x] = obj[x] / 100
                list_payments.append((0, 0, obj))
            return list_payments
        return False

    def get_checkbox_tax(self, result):
        self.ensure_one()
        if result:
            list_payments = []
            for obj in result.get('taxes'):
                obj['rec_id'] = obj.pop('id')
                list_payments.append((0, 0, obj))
            return list_payments
        return False

    def get_reports_x(self):
        self.ensure_one()
        result = self.cash_register_id.get_reports_x()

        if result.get('id'):
            self.rec_id = result.get('id')

        for name in list(self._fields):
            if result.get(name) and name != 'id':
                if name in ['transfers_sum', 'balance', 'initial']:
                    setattr(self, name, result.get(name) / 100)
                else:
                    setattr(self, name, result.get(name))
        self.tax_line_ids = self.get_checkbox_tax(result)
        self.payment_line_ids = self.get_checkbox_payment(result)
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kw.wizard.x_report',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def save_report(self):
        for obj in self:
            if not obj.rec_id:
                raise exceptions.ValidationError(
                    _('No ID in report, Try again!'))
            report = self.env['kw.checkbox.x.reports'].sudo().create({
                'name': obj.rec_id,
                'cash_register_id': obj.cash_register_id.id,
                'sell_receipts_count': obj.sell_receipts_count,
                'return_receipts_count': obj.return_receipts_count,
                'transfers_count': obj.transfers_count,
                'transfers_sum': obj.transfers_sum,
                'balance': obj.balance,
                'initial': obj.initial,
                'created_at': obj.created_at,
                'updated_at': obj.updated_at,
                'taxes': self.env['kw.checkbox.tax'].search(
                    [('code', 'in', obj.tax_line_ids.mapped('code'))]
                ).mapped('id'),
            })
            get_payment_list = []
            for payment in obj.payment_line_ids:
                get_payment_list.append(
                    self.env['kw.checkbox.x.reports.payments'].create({
                        'rec_id': payment.rec_id,
                        'code': payment.code,
                        'type': payment.type,
                        'label': payment.label,
                        'sell_sum': payment.sell_sum,
                        'return_sum': payment.return_sum,
                        'service_in': payment.service_in,
                        'service_out': payment.service_out,
                    }).id
                )
            report.write({
                'payments': get_payment_list
            })
