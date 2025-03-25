import logging

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class WizardReceiptService(models.TransientModel):
    _name = 'kw.wizard.service.receipt'
    _description = 'Checkbox Service Receipt'

    payment_type = fields.Selection(
        [('cash', 'CASH'), ('cashless', 'CASHLESS')],
        default='cash', required=True
    )
    type_of_move = fields.Selection(
        required=True, default='enter', selection=[
            # ('basic', _('Basic')),
            ('enter', _('Enter')),
            ('take', _('Take'))
        ], )

    payment_value = fields.Float()

    def commit_receipt(self):
        self.ensure_one()
        cash_register = self.env['kw.checkbox.cash.register'].search([
            ('id', '=', self.env.context.get('cash_reg'))
        ])
        _coef = -1 if self.type_of_move == 'take' else 1
        data = {
            "payment": {
                "type": self.payment_type.upper(),
                "value": int(self.payment_value * 100) * _coef,
            },
        }
        res = cash_register.commit_receipt(data)
        try:
            trans = res['transaction']['id']
        except Exception:
            trans = ""
        self.env['kw.checkbox.receipt'].create({
            'status': res['status'],
            'cb_id': res['id'],
            'type': res['type'],
            'transaction_cb_id': trans,
            'shift_cb_id': res['shift']['id'],
            'cashier_id': self.env.user.kw_checkbox_cashier_ids[0].id,
            'cash_register_id': cash_register.id,
            'cashier_cb_id': self.env.user.kw_checkbox_cashier_ids[0].cb_id,
            'res_val': res,
            'cash_register_cb_id': cash_register.cb_id,
        })
