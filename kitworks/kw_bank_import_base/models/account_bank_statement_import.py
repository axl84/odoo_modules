import base64

from odoo import models, fields, _
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.exceptions import UserError


class AccountBankStatementImport(models.TransientModel):
    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'

    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string='Files',
        required=True,
        help='Get you bank statements in electronic'
             ' format from your bank and select them here.')

    def import_file(self):
        self.ensure_one()
        statement_line_ids_all = []
        notifications_all = []
        for data_file in self.attachment_ids:
            currency_code, account_number, stmts_vals = self.with_context(
                active_id=self.ids[0])._parse_file(
                    base64.b64decode(data_file.datas))
            self._check_parsed_data(stmts_vals, account_number)
            currency, journal = self._find_additional_data(
                currency_code, account_number)
            if not journal:
                return self.with_context(
                    active_id=self.ids[0])._journal_creation_wizard(
                        currency, account_number)
            if not journal.default_debit_account_id \
                    or not journal.default_credit_account_id:
                raise UserError(_(
                    'You have to set a '
                    'Default Debit Account and a Default Credit '
                    'Account for the journal: %s') % (journal.name,))
            stmts_vals = self._complete_stmts_vals(
                stmts_vals, journal, account_number)
            statement_line_ids, notifications = self._create_bank_statements(
                stmts_vals)
            statement_line_ids_all.extend(statement_line_ids)
            notifications_all.extend(notifications)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.bank.statement.line',
                'view_mode': 'list',
                'target': 'new',
                'name': 'Import',
                'domain': [('id', 'in', statement_line_ids)],
            }

    def _journal_creation_wizard(self, currency, account_number):
        return {
            'name': _('Journal Creation'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.import.journal.creation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'statement_import_transient_id': self.env.context['active_id'],
                'default_bank_acc_number': account_number,
                'default_name': _('Bank') + ' ' + account_number,
                'default_currency_id': currency and currency.id or False,
                'default_type': 'bank',
            }
        }

    def _parse_file(self, data_file):
        raise UserError(_(
            'Could not make sense of the given file.'
            '\nDid you install the module to support this type of file ?'))

    def _check_parsed_data(self, stmts_vals, account_number):
        extra_msg = _('If it contains transactions for more than one account,'
                      ' it must be imported on each of them.')
        if len(stmts_vals) == 0:
            raise UserError(
                _('This file doesn\'t contain any statement '
                  'for account %s.') % (account_number,) + '\n' + extra_msg)
        no_st_line = True
        for vals in stmts_vals:
            if vals['transactions'] and len(vals['transactions']) > 0:
                no_st_line = False
                break
        if no_st_line:
            raise UserError(
                _('This file doesn\'t contain any transaction for '
                  'account %s.') % (account_number,) + '\n' + extra_msg
            )

    def _check_journal_bank_account(self, journal, account_number):
        # Needed for CH to accommodate for non-unique account numbers
        sanitized_acc_number = journal.bank_account_id.sanitized_acc_number
        if " " in sanitized_acc_number:
            sanitized_acc_number = sanitized_acc_number.split(" ")[0]
        return sanitized_acc_number == account_number

    def _find_additional_data(self, currency_code, account_number):
        company_currency = self.env.company.currency_id
        journal_obj = self.env['account.journal']
        currency = None
        sanitized_account_number = sanitize_account_number(account_number)
        if currency_code:
            currency = self.env['res.currency'].search(
                [('name', '=ilike', currency_code)], limit=1)
            if not currency:
                raise UserError(_(
                    "No currency found matching '%s'.") % currency_code)
            if currency == company_currency:
                currency = False
        journal = journal_obj.browse(self.env.context.get('journal_id', []))
        if account_number:
            if journal and not journal.bank_account_id:
                journal.set_bank_account(account_number)
            elif not journal:
                journal = journal_obj.search(
                    [('bank_account_id.sanitized_acc_number', '=',
                      sanitized_account_number)])
            else:
                if not self._check_journal_bank_account(
                        journal, sanitized_account_number):
                    # pylint: disable=W8120
                    raise UserError(_(
                        'The account of this statement (%s) is not the same '
                        'as the journal (%s).') % (
                            account_number,
                            journal.bank_account_id.acc_number))
        if journal:
            journal_currency = journal.currency_id
            if currency is None:
                currency = journal_currency
            if currency and currency != journal_currency:
                # pylint: disable=R1706
                statement_cur_code = not currency \
                    and company_currency.name or currency.name
                journal_cur_code = not journal_currency \
                    and company_currency.name or journal_currency.name
                # pylint: disable=W8120
                raise UserError(_(
                    'The currency of the bank statement (%s) is not the same '
                    'as the currency of the journal (%s).') % (
                        statement_cur_code, journal_cur_code))

        # If we couldn't find / can't create a journal, everything is lost
        if not journal and not account_number:
            raise UserError(_('Cannot find in which journal import this '
                              'statement. Please manually select a journal.'))
        return currency, journal

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal.id
            if not st_vals.get('reference'):
                st_vals['reference'] = " ".join(
                    self.attachment_ids.mapped('name'))
            if st_vals.get('number'):
                st_vals['name'] = journal.sequence_id.with_context(
                    ir_sequence_date=st_vals.get('date')).get_next_char(
                        st_vals['number'])

                # pylint: disable=C0325
                del (st_vals['number'])
            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id')
                if unique_import_id:
                    sanitized_account_number = sanitize_account_number(
                        account_number)
                    line_vals['unique_import_id'] = (
                        sanitized_account_number and sanitized_account_number
                        + '-' or '') + str(
                            journal.id) + '-' + unique_import_id

                if not line_vals.get('bank_account_id'):
                    identifying_string = line_vals.get('account_number')
                    if identifying_string:
                        partner_bank = self.env['res.partner.bank'].search(
                            [('acc_number', '=', identifying_string)], limit=1)
                        if partner_bank:
                            line_vals['bank_account_id'] = partner_bank.id
                            line_vals[
                                'partner_id'] = partner_bank.partner_id.id
        return stmts_vals

    def _create_bank_statements(self, stmts_vals):
        BankStatement = self.env['account.bank.statement']
        BankStatementLine = self.env['account.bank.statement.line']
        statement_line_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in stmts_vals:
            filtered_st_lines = []
            for line_vals in st_vals['transactions']:
                d = [('unique_import_id', '=',
                      line_vals['unique_import_id'])]
                if 'unique_import_id' not in line_vals \
                        or not line_vals['unique_import_id'] \
                        or not BankStatementLine.sudo().search(d, limit=1):
                    filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.append(
                        line_vals['unique_import_id'])
                    if 'balance_start' in st_vals:
                        st_vals['balance_start'] += float(line_vals['amount'])

            if len(filtered_st_lines) > 0:
                st_vals.pop('transactions', None)
                st_vals['line_ids'] = [[0, False, line] for line in
                                       filtered_st_lines]
                BankStatement = BankStatement.create(st_vals)
                statement_line_ids.extend(
                    BankStatement.line_ids.ids)

        if len(statement_line_ids) == 0:
            raise UserError(_('You already have imported that file.'))
        # BankStatement.update({'state': 'posted'})
        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_statement_lines_import_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message': _(
                    "%d transactions had already been imported and "
                    "were ignored."
                    "") % num_ignored if num_ignored > 1 else _(
                        "1 transaction had already been imported "
                        "and was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': BankStatementLine.search(
                        [('unique_import_id', 'in',
                          ignored_statement_lines_import_ids)]).ids
                }
            }]
        return statement_line_ids, notifications

    def checking_start_and_end_balance(self, statement, journal):
        sorted_keys = sorted(statement.keys())
        if len(sorted_keys) == 0:
            return statement
        last_statement = self.env['account.bank.statement'].search(
            [('journal_id', '=', journal.id),
                ('date', '<=', sorted_keys[0])], order='date desc', limit=1)
        if last_statement:
            balance_end_real = last_statement.balance_end_real
        else:
            balance_end_real = 0
        bank_statement = self.env['account.bank.statement'].search(
            [('journal_id', '=', journal.id), ('date', '=', sorted_keys[0])])
        if bank_statement:
            balance_end_real = bank_statement.balance_start

        for date in sorted_keys:
            if statement.get(date):
                amount_statement = sum(
                    x['amount'] for x in statement[date]['transactions'])
                statement[date]['balance_start'] = balance_end_real
                balance_end_real += amount_statement
                statement[date]['balance_end_real'] = balance_end_real
        return statement
