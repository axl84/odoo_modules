from odoo import models, fields


class AccountBankStatementLine(models.Model):
    _name = 'account.bank.statement.line'
    _inherit = 'account.bank.statement.line'

    kw_bank_import_raw_acc = fields.Char(string='Raw acc')
    kw_bank_import_raw_bic = fields.Char(string='Raw bic')
    kw_bank_import_raw_bank_name = fields.Char(string='Raw bank')
    kw_bank_import_raw_enterprise_code = fields.Char(string='Raw code')
    kw_bank_import_raw_partner_name = fields.Char(string='Raw partner')
    kw_bank_import_raw_description = fields.Char(string='Raw description')
    journal_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='statement_id.currency_id',
        readonly=True)
    bank_account_id = fields.Many2one(
        comodel_name='res.partner.bank', string='Bank Account')
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Counterpart Account',
        domain=[('deprecated', '=', False)])
    note = fields.Text(string='Notes')
    unique_import_id = fields.Char(
        string='Import ID',
        readonly=True,
        copy=False)

    _sql_constraints = [
        ('unique_import_id', 'unique (unique_import_id)',
         'A bank account transactions can be imported only once !')
    ]
