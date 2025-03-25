import logging

from odoo import models, fields, exceptions, _

from .checkbox import CheckBoxApi

_logger = logging.getLogger(__name__)


class CheckboxCashRegister(models.Model):
    _name = 'kw.checkbox.cash.register'
    _inherit = ['kw.checkbox.mixin']
    _description = 'Checkbox cash register'
    _sql_constraints = [
        ('cb_id_uniq', 'unique (cb_id)', _('CheckBox ID must be unique'))]

    name = fields.Char(
        string='Title', )
    checkbox_name = fields.Char(readonly=True)
    active = fields.Boolean(
        default=True, )
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', change_default=True,
        default=lambda self: self.env.user.company_id.id, )
    address = fields.Char(
        readonly=True, )
    cb_id = fields.Char(
        string='CheckBox ID', readonly=True, )
    fiscal_number = fields.Char(
        readonly=True, )
    license_key = fields.Char(
        required=True, )
    is_offline = fields.Boolean(
        default=False, readonly=True, )
    organization_id = fields.Many2one(
        comodel_name='kw.checkbox.organization', )
    cashier_id = fields.Many2one(
        comodel_name='kw.checkbox.cashier', required=True)
    current_shift_id = fields.Many2one(
        comodel_name='kw.checkbox.shift', )
    max_count_codes = fields.Integer(
        default=150, string='Max offline codes', required=True, )
    is_log_enabled = fields.Boolean(
        default=False, )
    is_pass_barcode_to_checkbox = fields.Boolean(
        string='Pass barcode to Checkbox', default=True)

    def get_all_tax(self):
        self.ensure_one()
        _logger.info('get_all_tax')
        cashier_token = self.cashier_id.get_cashier_token()
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token, license_key=self.license_key,
            test_mode=self.company_id.kw_checkbox_mode != 'prod', )
        res = checkbox.get_all_tax()
        for tax in res:
            domain = [('cash_register_id', '=', self.id),
                      ('index', '=', tax.get('id'))]
            if not self.env['kw.checkbox.tax'].search(domain):
                self.env['kw.checkbox.tax'].sudo().create({
                    'cash_register_id': self.id,
                    'index': tax.get('id'),
                    'code': tax.get('code'),
                    'label': tax.get('label'),
                    'symbol': tax.get('symbol'),
                    'rate': tax.get('rate'),
                    'extra_rate': tax.get('extra_rate'),
                    'included': tax.get('included'),
                    'datetime_created_at': tax.get('created_at'),
                    'datetime_updated_at': tax.get('updated_at'), })
        self.update_info()
        _logger.info(res)
        return res

    def go_online(self):
        self.ensure_one()
        _logger.info('go_online')
        cashier_token = self.cashier_id.get_cashier_token()
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token, license_key=self.license_key,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        checkbox.go_online()
        self.update_info()

    def go_offline(self):
        _logger.info('go_offline')
        self.ensure_one()
        cashier_token = self.cashier_id.get_cashier_token()
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token, license_key=self.license_key,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        checkbox.go_offline()
        self.update_info()

    def ask_offline_codes(self):
        _logger.info('ask_offline_codes')
        self.ensure_one()
        cashier_token = self.cashier_id.get_cashier_token()
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token, license_key=self.license_key,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        checkbox.cash_registers_ask_offline_codes(
            params={'count': self.max_count_codes})
        self.update_info()

    def get_offline_codes(self):
        _logger.info('get_offline_codes')
        self.ensure_one()
        cashier_token = self.cashier_id.get_cashier_token()
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token, license_key=self.license_key,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        res = checkbox.cash_registers_get_offline_codes(
            params={'count': self.max_count_codes})
        for code in res:
            domain = [('cash_register_id', '=', self.id),
                      ('serial_id', '=', code.get('serial_id')),
                      ('fiscal_code', '=', code.get('fiscal_code'))]
            if not self.env['kw.checkbox.offline.code'].search(domain):
                self.env['kw.checkbox.offline.code'].sudo().create({
                    'cash_register_id': self.id,
                    'serial_id': code.get('serial_id'),
                    'fiscal_code': code.get('fiscal_code'),
                    'datetime_created_at':
                        code.get('created_at'), })

        self.update_info()

    def ping_tax_service(self):
        _logger.info('ping_tax_service')
        self.ensure_one()
        cashier_token = self.cashier_id.get_cashier_token()
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token, license_key=self.license_key,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        res = checkbox.cash_registers_ping_tax_service()
        _logger.info(res)
        self.update_info()
        if res.get('status') == 'DONE':
            return True
        return False

    def update_info(self):
        self.ensure_one()
        cashier_token = self.cashier_id.get_cashier_token()
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        self.update_info_by_token(cashier_token)

    def action_shifts(self):
        self.ensure_one()
        action = self.env.ref(
            'kw_checkbox.kw_checkbox_kw_checkbox_shift_action_window'
            '').read()[0]
        action['domain'] = [('cash_register_id', '=', self.id)]
        return action

    def update_info_by_token(self, token, ):
        checkbox = CheckBoxApi(
            access_token=token, license_key=self.license_key,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        res = checkbox.cash_registers_info()
        data = {'fiscal_number': res['fiscal_number'], 'cb_id': res['id'],
                'address': res['address'], 'is_offline': res['offline_mode'],
                'checkbox_name': res['title'] or res['fiscal_number'],
                'name': res['title'] or res['fiscal_number'], }
        res = checkbox.get_cash_registers(res['id'])
        if res.get('shift'):
            shift_data = res.get('shift')
            shift_data['cash_register'] = {'id': res['id']}
            current_shift_id = self.env[
                'kw.checkbox.shift'].get_or_create(shift_data)
            if current_shift_id and current_shift_id.status == 'OPENED':
                data['current_shift_id'] = current_shift_id.id
            else:
                data['current_shift_id'] = False
        else:
            data['current_shift_id'] = False
        self.write(data)

    def get_reports_x(self):
        self.ensure_one()
        self.update_info()
        if not self.current_shift_id or \
                self.current_shift_id.status != 'OPENED':
            raise exceptions.ValidationError(
                _('There is no OPENED shift'))
        checkbox = self.current_shift_id.cashier_id.get_checkbox()
        # if not cashier_token:
        #     raise exceptions.ValidationError(
        #         _('There is no acceptable username'))
        checkbox.license_key = self.license_key
        # checkbox = CheckBoxApi(
        #     access_token=cashier_token, license_key=self.license_key,
        #     test_mode=self.company_id.kw_checkbox_mode != 'prod')
        result = checkbox.x_report()
        _logger.info(result)
        return result

    def cb_to_wizard(self):
        form_view = self.env.ref(
            "kw_checkbox.kw_wizard_service_receipt_wizard_view")
        return {
            'name': 'Service Receipt',
            'views': [
                (form_view.id, 'form'),
            ],
            'res_model': 'kw.wizard.service.receipt',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {
                'cash_reg': self.id,
            },
        }

    def commit_receipt(self, data):
        cashier_token = self.cashier_id.get_cashier_token()
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token,
            license_key="" if not self.license_key else self.license_key,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        res = checkbox.post_service_receipt(data)
        return res
