import logging
import time

from odoo import models, fields, _, SUPERUSER_ID, exceptions

_logger = logging.getLogger(__name__)


class CheckboxPosSession(models.Model):
    _inherit = 'pos.session'

    kw_checkbox_shift_ids = fields.One2many(
        comodel_name='kw.checkbox.shift', inverse_name='pos_session_id', )

    def kw_checkbox_get_shift(self, organization):
        self.ensure_one()
        for s in self.kw_checkbox_shift_ids:
            if organization.id == s.cashier_id.organization_id.id:
                return s
        return False

    def reshipment_of_unsent_orders_checkbox(self):
        self.ensure_one()
        if not self.kw_checkbox_shift_ids:
            return
        unsent_orders = self.get_unsent_orders()
        if not unsent_orders:
            return
        receipts = self.get_receipts_info()
        self.process_receipts(receipts, unsent_orders)
        self.try_reship_unsent_orders(unsent_orders)

    def sent_offline_orders_checkbox(self):
        self.ensure_one()
        if not self.kw_checkbox_shift_ids:
            return
        offline_orders = self.get_offline_orders()
        if not offline_orders:
            return
        for offline_order in offline_orders:
            offline_order.checkbox_sell_offline()

    def get_offline_orders(self):
        offline_orders = self.env['pos.order'].sudo().search([
            ('session_id', '=', self.id), ('is_offline', '=', True),
            ('kw_checkbox_organization_id', '!=', False),
            ('kw_checkbox_receipt_id', '=', False)])
        return offline_orders

    def get_unsent_orders(self):
        unsent_orders = self.env['pos.order'].sudo().search([
            ('session_id', '=', self.id), ('is_offline', '=', False),
            ('kw_checkbox_organization_id', '!=', False),
            ('kw_checkbox_receipt_id', '=', False)])
        return unsent_orders.ids

    def get_receipts_info(self):
        shift = self.kw_checkbox_shift_ids[0]
        return self.env['kw.checkbox.receipt'].sudo().get_receipt(
            cashier_id=shift.cashier_id,
            cash_register_id=shift.cash_register_id,
            params={'shift_id': shift.cb_id})['results']

    def process_receipts(self, receipts, unsent_orders):
        po_sudo = self.env['pos.order'].sudo()
        for receipt in receipts:
            context_checkbox = receipt.get('context', {})
            if context_checkbox and 'order_id' in context_checkbox:
                order = int(receipt.get('context').get('order_id'))
                if order in unsent_orders:
                    order_record = po_sudo.browse([order])
                    order_record.kw_checkbox_receipt_id = (
                        self.search_or_create_receipt(receipt))
                    unsent_orders.remove(order)

    def search_or_create_receipt(self, vals):
        shift = self.kw_checkbox_shift_ids[0]
        kcr_sudo = self.env['kw.checkbox.receipt'].sudo()
        receipt_id = kcr_sudo.search(
            [('cb_id', '=', vals['id'])], limit=1)
        if not receipt_id:
            receipt_id = kcr_sudo.create({
                'name': vals['fiscal_code'],
                'fiscal_date': vals['fiscal_date'],
                'status': vals['status'], 'cb_id': vals['id'],
                'type': vals['type'],
                'transaction_cb_id': vals['transaction']['id'],
                'shift_cb_id': vals['shift']['id'],
                'cashier_id': shift.cashier_id.id,
                'cash_register_id': shift.cash_register_id.id,
                'cashier_cb_id': shift.cashier_id.cb_id,
                'res_val': kcr_sudo.get_res_val(vals),
                'cash_register_cb_id': shift.cash_register_id.cb_id,
                'company_id': shift.cashier_id.company_id.id
            })
        return receipt_id.id

    def try_reship_unsent_orders(self, unsent_orders):
        po_sudo = self.env['pos.order'].sudo()
        try:
            po_sudo.browse(unsent_orders).action_reshipping()
        except Exception as e:
            _logger.info(e)

    def close_session_checkbox(self):
        self.ensure_one()
        for shift in self.kw_checkbox_shift_ids:
            shift.update_info()
            if shift.status == 'OPENED':
                try:
                    shift.close_opened()
                    while shift.status != 'CLOSED':
                        time.sleep(1)
                        shift.update_info()
                except Exception as e:
                    raise exceptions.ValidationError(e)

    def action_pos_session_closing_control(
            self, balancing_account=False, amount_to_balance=0,
            bank_payment_method_diffs=None):
        for pos_session in self:
            pos_session.sent_offline_orders_checkbox()
            pos_session.reshipment_of_unsent_orders_checkbox()
            pos_session.close_session_checkbox()
        return super(
            CheckboxPosSession, self).action_pos_session_closing_control(
                balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
                bank_payment_method_diffs=bank_payment_method_diffs)

    def action_pos_session_close(
            self, balancing_account=False,
            amount_to_balance=0, bank_payment_method_diffs=None):
        for pos_session in self:
            pos_session.sent_offline_orders_checkbox()
            pos_session.reshipment_of_unsent_orders_checkbox()
            pos_session.close_session_checkbox()
        return super(
            CheckboxPosSession, self).action_pos_session_close(
                balancing_account=balancing_account,
                amount_to_balance=amount_to_balance,
                bank_payment_method_diffs=bank_payment_method_diffs)

    # pylint: disable=too-many-branches
    def action_pos_session_open(self):
        if self.env.uid == SUPERUSER_ID:
            return False
        for pos_session in self.filtered(lambda x: not x.rescue):
            _logger.info(pos_session.config_id.kw_checkbox_cash_register_ids)
            for register in \
                    pos_session.config_id.kw_checkbox_cash_register_ids:
                register.update_info()
                if register.current_shift_id:
                    if register.current_shift_id.cashier_id.id not in \
                            self.env.user.kw_checkbox_cashier_ids.ids:
                        raise exceptions.ValidationError(_(
                            'This cash register user by other user'))
                    register.current_shift_id.pos_session_id = pos_session.id
                    continue
                cashier = self.env['kw.checkbox.cashier'].search(
                    [('user_ids', 'in', self.env.user.ids),
                     ('organization_id', '=', register.organization_id.id)],
                    limit=1)
                if not cashier:
                    raise exceptions.ValidationError(_(
                        'There is no valid cashier for cash register'))
                cashier.update_info()
                cashier.update_open_shifts()
                is_checkbox_online = register.ping_tax_service()
                _logger.info('%s', 'X' * 100)
                _logger.info('is_checkbox_online %s', is_checkbox_online)
                if is_checkbox_online:
                    shift = self.env['kw.checkbox.shift'].create({
                        'cashier_id': cashier.id,
                        'cash_register_id': register.id,
                        'pos_session_id': pos_session.id, })
                    _logger.info('shift %s', shift)
                    while shift.status != 'OPENED':
                        time.sleep(1)
                        shift.update_info_by_token(
                            cashier.get_checkbox().access_token)
                    register.count_offline_codes = \
                        len(self.env['kw.checkbox.offline.code'].search(
                            [('cash_register_id', '=', register.id)]).ids)
                    if not register.count_offline_codes \
                            or register.count_offline_codes \
                            < register.min_count_codes:
                        if not register.is_offline:
                            register.ask_offline_codes()
                        register.get_offline_codes()
                    # pos_session.config_id.check_and_sell_offline_orders(
                    #     register)
                else:
                    raise exceptions.ValidationError(_(
                        'Unable to reach the tax office, try again later'))
            # if not pos_session.kw_checkbox_shift_ids.filtered(
            #         lambda x: x.status == 'OPENED'):
            #     return
            if pos_session.config_id.kw_checkbox_cash_register_ids:
                if len(pos_session.kw_checkbox_shift_ids.filtered(
                        lambda x: x.status == 'OPENED')) != len(
                        pos_session.config_id.kw_checkbox_cash_register_ids):
                    raise exceptions.ValidationError(_(
                        'Session require opened shifts to start'))

        return super().action_pos_session_open()

    def open_frontend_cb(self):
        if self.config_id.kw_checkbox_cash_register_ids:
            if len(self.kw_checkbox_shift_ids.filtered(
                    lambda x: x.status == 'OPENED')) != len(
                    self.config_id.kw_checkbox_cash_register_ids):
                return self.action_pos_session_open()
        if self.state == 'opening_control':
            self.action_pos_session_open()
        return super(CheckboxPosSession, self).open_frontend_cb()

    def try_cash_in_out(self, _type, amount, reason, extras):
        res = super(CheckboxPosSession, self).try_cash_in_out(
            _type, amount, reason, extras)
        sign = 1 if _type == 'in' else -1
        sessions = self.filtered('cash_journal_id')
        self.checkbox_cash_out(sessions, amount, sign)
        return res

    def checkbox_cash_out(self, records, amount, sign):
        for obj in records:
            if obj.kw_checkbox_shift_ids:
                if (obj.with_context(
                        **{}).cash_register_balance_end) < 0:
                    raise exceptions.ValidationError(
                        _("You cannot withdraw more than "
                          "what is available at the box office"))
                data = {
                    "payment": {
                        "type": 'CASH',
                        "value": int(amount * 100) * sign,
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

    def _loader_params_product_product(self):
        res = super(CheckboxPosSession, self)._loader_params_product_product()
        res['search_params']['fields'].append('is_excise_product')
        res['search_params']['fields'].append('kw_checkbox_uktzed')
        res['search_params']['fields'].append(
            'kw_checkbox_product_category_id')
        return res

    def _get_pos_ui_pos_payment_method(self, params):
        params['search_params']['fields'].append(
            'kw_checkbox_product_category_id')
        params['search_params']['fields'].append(
            'kw_checkbox_is_register_receipt')
        res = super(CheckboxPosSession,
                    self)._get_pos_ui_pos_payment_method(params)
        return res

    def check_refund_sum(self, session):
        session_id = self.browse(session)
        return session_id.with_context(**{}).cash_register_balance_end
