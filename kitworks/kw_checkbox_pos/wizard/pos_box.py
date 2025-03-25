from odoo.addons.account.wizard.pos_box import CashBox
from odoo import exceptions, _


class PosBox(CashBox):
    _register = False

    def run(self):
        active_model = self.env.context.get('active_model', False)
        active_ids = self.env.context.get('active_ids', [])

        if active_model == 'pos.session':
            records = self.env[active_model].browse(active_ids)
            self.checkbox_cash_out(records)
        return super(PosBox, self).run()


class PosBoxOut(PosBox):
    _inherit = 'cash.box.out'

    def checkbox_cash_out(self, records):
        for obj in records:
            if obj.kw_checkbox_shift_ids:
                amount = self.amount
                if (obj.with_context(
                        **{}).cash_register_balance_end + amount) < 0:
                    raise exceptions.ValidationError(
                        _("You cannot withdraw more than "
                          "what is available at the box office"))
                data = {
                    "payment": {
                        "type": 'CASH',
                        "value": int(self.amount * 100),
                    },
                }
                res = \
                    obj.kw_checkbox_shift_ids[0].\
                    cash_register_id.commit_receipt(data)
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
                    'cashier_id': obj.kw_checkbox_shift_ids[0].cashier_id.id,
                    'cash_register_id':
                        obj.kw_checkbox_shift_ids[0].cash_register_id.id,
                    'cashier_cb_id':
                        obj.kw_checkbox_shift_ids[0].cashier_id.cb_id,
                    'res_val': res,
                    'cash_register_cb_id':
                        obj.kw_checkbox_shift_ids[0].cash_register_id.cb_id,
                })
