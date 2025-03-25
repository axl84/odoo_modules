import logging

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    kw_checkbox_is_register_receipt = fields.Boolean(
        default=False, string='Register CheckBox receipt')
    kw_checkbox_is_journal_register_receipt = fields.Boolean(
        related='journal_id.kw_checkbox_is_register_receipt')
    kw_checkbox_receipt_id = fields.Many2one(
        comodel_name='kw.checkbox.receipt', string='Receipt', )
    kw_checkbox_invoice_id = fields.Many2one(
        comodel_name='account.move', string='Invoice', )
    kw_checkbox_cashier_id = fields.Many2one(
        comodel_name='kw.checkbox.cashier', string='Cashier', )
    kw_checkbox_cashier_ids = fields.Many2many(
        comodel_name='kw.checkbox.cashier',
        compute='_compute_kw_checkbox_cashier_ids', )
    kw_checkbox_cash_register_id = fields.Many2one(
        comodel_name='kw.checkbox.cash.register', string='Cash register', )
    kw_checkbox_cash_register_ids = fields.Many2many(
        comodel_name='kw.checkbox.cash.register',
        compute='_compute_kw_checkbox_cash_register_ids', )
    kw_checkbox_is_mixed_payment = fields.Boolean(
        default=False, string='CheckBox mixed payment')
    kw_checkbox_mixed_amount = fields.Monetary(
        currency_field='currency_id', string='CheckBox mixed amount')
    kw_checkbox_mixed_journal_id = fields.Many2one(
        'account.journal', string='CheckBox mixed journal',
        domain="[('company_id', '=', company_id), "
               "('type', 'in', ('bank', 'cash')), "
               "('kw_checkbox_is_register_receipt', '=', True)]")
    kw_payment_method_line_id = fields.Many2one(
        'account.payment.method.line', string='CheckBox mixed Payment Method',
        readonly=False, store=True, copy=False,
        compute='_compute_kw_payment_method_line_id',
        domain="[('id', 'in', kw_available_payment_method_line_ids)]")
    kw_available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_kw_payment_method_line_fields')

    @api.onchange('amount')
    def _onchange_amount(self):
        for obj in self:
            all_amount = obj.get_all_amount()
            obj.kw_checkbox_mixed_amount = all_amount - obj.amount

    @api.onchange('kw_checkbox_mixed_amount')
    def _onchange_mixed_amount(self):
        for obj in self:
            all_amount = obj.get_all_amount()
            obj.amount = all_amount - obj.kw_checkbox_mixed_amount

    def get_all_amount(self):
        for wizard in self:
            if wizard.source_currency_id == wizard.currency_id:
                return wizard.source_amount_currency
            if wizard.currency_id == wizard.company_id.currency_id:
                return wizard.source_amount
            return wizard.company_id.currency_id._convert(
                wizard.source_amount, wizard.currency_id, wizard.company_id,
                wizard.payment_date or fields.Date.today())

    def action_create_mixed_payments(self):
        for obj in self:
            new_obj = obj.copy(
                {'amount': obj.kw_checkbox_mixed_amount,
                 'payment_method_line_id': obj.kw_payment_method_line_id.id,
                 'journal_id': obj.kw_checkbox_mixed_journal_id.id})
            new_payment_ids = new_obj.with_context(
                **{'mixed_payment': True, 'return_payments_ids': True}
            ).action_create_payments()
            payment_ids = obj.with_context(
                **{'mixed_payment': True, 'return_payments_ids': True}
            ).action_create_payments()
            payment_ids = payment_ids | new_payment_ids
            payment_ids.mixed_action_post()
        return False

    @api.onchange('journal_id', 'kw_checkbox_cash_register_id')
    def _onchange_fields(self):
        for obj in self:
            curr_journal_id = self.env['account.journal'].search([
                ('id', '=', obj.journal_id.id)
            ])
            obj.kw_checkbox_is_register_receipt = \
                curr_journal_id.kw_checkbox_is_register_receipt
            curr_reg = obj.kw_checkbox_cash_register_id
            if curr_reg:
                cb_id = curr_reg.current_shift_id.cashier_id
                if cb_id:
                    obj.kw_checkbox_cashier_id = cb_id

    @api.model
    def default_get(self, vals):
        res = super().default_get(vals)
        active_id = self.env.context.get('active_id')
        res['kw_checkbox_invoice_id'] = active_id
        return res

    @api.depends('journal_id')
    def _compute_kw_checkbox_cashier_ids(self):
        for obj in self:
            ids = self.env.user.kw_checkbox_cashier_ids
            obj.kw_checkbox_cashier_ids = [(6, 0, ids.ids)]
            if len(ids) == 1:
                obj.kw_checkbox_cashier_id = ids[0].id

    @api.depends('journal_id')
    def _compute_kw_checkbox_cash_register_ids(self):
        for obj in self:
            ids = self.env['kw.checkbox.cash.register'].search([])
            obj.kw_checkbox_cash_register_ids = [(6, 0, ids.ids)]
            if len(ids) == 1:
                obj.kw_checkbox_cash_register_id = ids[0].id

    @api.constrains(
        'kw_checkbox_is_register_receipt', 'kw_checkbox_cashier_id',
        'kw_checkbox_cash_register_id', )
    def constrains_checkbox_fields(self):
        for obj in self:
            if obj.kw_checkbox_is_register_receipt and not \
                    obj.journal_id.kw_checkbox_is_register_receipt:
                raise exceptions.ValidationError(
                    _('This journal payment cant be registered as checkbox '
                      'receipt'))

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals.update({
            'kw_checkbox_is_register_receipt':
                self.kw_checkbox_is_register_receipt,
            'kw_checkbox_cashier_id': self.kw_checkbox_cashier_id.id,
            'kw_checkbox_invoice_id': self.kw_checkbox_invoice_id.id,
            'kw_checkbox_cash_register_id':
                self.kw_checkbox_cash_register_id.id, })
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        if not self.kw_checkbox_is_register_receipt:
            return super()._create_payment_vals_from_batch(batch_result)
        batch_values = self._get_wizard_values_from_batch(batch_result)
        return {
            'date': self.payment_date,
            'amount': batch_values['source_amount_currency'],
            'payment_type': batch_values['payment_type'],
            'partner_type': batch_values['partner_type'],
            'ref': self._get_batch_communication(batch_result),
            'journal_id': self.journal_id.id,
            'currency_id': batch_values['source_currency_id'],
            'partner_id': batch_values['partner_id'],
            'partner_bank_id': batch_result['key_values']['partner_bank_id'],
            'payment_method_id': self.payment_method_line_id.id,
            'destination_account_id': batch_result['lines'][0].account_id.id,
            'kw_checkbox_is_register_receipt':
                self.kw_checkbox_is_register_receipt,
            'kw_checkbox_cashier_id': self.kw_checkbox_cashier_id.id,
            'kw_checkbox_invoice_id': self.kw_checkbox_invoice_id.id,
            'kw_checkbox_cash_register_id':
                self.kw_checkbox_cash_register_id.id
        }

    def action_create_payments(self):
        payments = self._create_payments()
        if self._context.get('return_payments_ids'):
            return payments
        if self._context.get('dont_redirect_to_payments'):
            return True
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action

    @api.depends('kw_checkbox_mixed_journal_id')
    def _compute_kw_payment_method_line_id(self):
        for wizard in self:
            if wizard.kw_checkbox_mixed_journal_id:
                kw_cb_journal = wizard.kw_checkbox_mixed_journal_id
                available_payment_method_lines = (
                    kw_cb_journal._get_available_payment_method_lines(
                        wizard.payment_type))
            else:
                available_payment_method_lines = False

            if available_payment_method_lines:
                wizard.kw_payment_method_line_id = (
                    available_payment_method_lines[0]._origin)
            else:
                wizard.kw_payment_method_line_id = False

    @api.depends('kw_checkbox_mixed_journal_id')
    def _compute_kw_payment_method_line_fields(self):
        for wizard in self:
            if wizard.kw_checkbox_mixed_journal_id:
                kw_cb_journal = wizard.kw_checkbox_mixed_journal_id
                wizard.kw_available_payment_method_line_ids = (
                    kw_cb_journal._get_available_payment_method_lines(
                        wizard.payment_type))
            else:
                wizard.kw_available_payment_method_line_ids = False
