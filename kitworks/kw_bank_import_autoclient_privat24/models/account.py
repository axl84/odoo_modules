import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = 'account.journal'

    kw_privat24_downloading_date = fields.Date(
        readonly=True, string='Privat24 progress date',
        default=fields.Date.context_today)

    def kw_privat24_init_sync(self):
        self.ensure_one()
        self.kw_privat24_downloading_date = self.kw_bank_import_initial_date

    def kw_privat24_self_sync(self):
        self.ensure_one()
        obj = self

        last_statement = self.env['account.bank.statement'].search(
            [('journal_id', '=', obj.id)], order='date desc', limit=1)
        before_last_statement = self.env['account.bank.statement'].search(
            [('journal_id', '=', obj.id)], order='date desc', limit=1,
            offset=1)
        if not self.kw_privat24_downloading_date:
            raise UserError(
                _("You don't have 'Privat24 progress date'. Please select "
                  "'Initial date' and press button: 'INIT SYNC'. "
                  "And continue"))
        if last_statement:
            downloading_date = self.kw_privat24_downloading_date
            if before_last_statement:
                balance_end_real = before_last_statement.balance_end_real
            else:
                balance_end_real = 0
        else:
            downloading_date = obj.kw_privat24_downloading_date
            balance_end_real = 0
        autoclient = obj.kw_privat24_get_autoclient()
        while downloading_date < datetime.now().date():
            _logger.info(downloading_date)
            data = obj.privat24_sync_statements(autoclient.get_statement(
                downloading_date, downloading_date), balance_end_real)
            if data:
                statement_date = datetime.strftime(
                    downloading_date, '%d.%m.%Y')
                balance_end_real = data[statement_date]['balance_end_real']
            if downloading_date < datetime.now().date():
                downloading_date = downloading_date + relativedelta(days=1)
                obj.kw_privat24_downloading_date = downloading_date
        data = obj.privat24_sync_statements(
            autoclient.get_statement(
                datetime.now().date(),
                datetime.now().date()), balance_end_real)
        if data:
            statement_date = datetime.strftime(
                datetime.now().date(), '%d.%m.%Y')
            balance_end_real = data[statement_date]['balance_end_real']
        _logger.info(downloading_date)

    def _kw_privat24_cron_sync(self):
        for obj in self.env['account.journal'].search(
                [('bank_statements_source', '=', 'privat24_autoclient')]):
            last_statement = self.env['account.bank.statement'].search(
                [('journal_id', '=', obj.id)], order='date desc', limit=1)
            before_last_statement = self.env['account.bank.statement'].search(
                [('journal_id', '=', obj.id)], order='date desc', limit=1,
                offset=1)
            if last_statement:
                downloading_date = last_statement.date
                obj.kw_privat24_downloading_date = last_statement.date
                if before_last_statement:
                    balance_end_real = before_last_statement.balance_end_real
                else:
                    balance_end_real = 0
            else:
                downloading_date = obj.kw_privat24_downloading_date
                balance_end_real = 0
            autoclient = obj.kw_privat24_get_autoclient()
            while downloading_date < datetime.now().date():
                data = obj.privat24_sync_statements(autoclient.get_statement(
                    downloading_date, downloading_date), balance_end_real)
                if data:
                    statement_date = datetime.strftime(
                        downloading_date, '%d.%m.%Y')
                    balance_end_real = data[statement_date]['balance_end_real']
                if downloading_date < datetime.now().date():
                    downloading_date = downloading_date + relativedelta(days=1)
                    obj.kw_privat24_downloading_date = downloading_date
            data = obj.privat24_sync_statements(
                autoclient.get_statement(
                    datetime.now().date(),
                    datetime.now().date()), balance_end_real)
            if data:
                statement_date = datetime.strftime(
                    datetime.now().date(), '%d.%m.%Y')
                balance_end_real = data[statement_date]['balance_end_real']

    def kw_privat24_today_sync(self):
        self.ensure_one()
        autoclient = self.kw_privat24_get_autoclient()
        self.privat24_sync_statements(autoclient.get_statement_today())

    def privat24_sync_statements(self, statement_records, balance_start):
        _logger.info(statement_records)
        self.ensure_one()
        acc_number = self.bank_account_id.acc_number.replace(' ', '')
        statements = {}
        if not statement_records:
            return statements
        for record in statement_records:
            record = list(record.values())[0]
            if record['BPL_FL_REAL'] != 'r':
                # skip not real statement lines
                continue
            if record['AUT_MY_ACC'] not in (acc_number, acc_number[-14:]):
                # skip statement lines for different account number
                continue

            statement_date = record['BPL_DAT_OD']
            direction = -1 if record['TRANTYPE'] != 'C' else 1

            if not statements.get(statement_date):
                statements[statement_date] = {
                    'name': '{} {}'.format(acc_number, statement_date),
                    'date': statement_date,
                    'balance_start': balance_start,
                    'balance_end_real': balance_start + direction * float(
                        record['BPL_SUM']),
                    'transactions': [],
                }
            else:
                ber = statements[statement_date]['balance_end_real']
                statements[statement_date]['balance_end_real'] =\
                    ber + direction * float(record['BPL_SUM'])

            partner_id = False
            partner = self.get_partner(
                enterprise_code=record['AUT_CNTR_CRF'],
                partner_name=record['AUT_CNTR_NAM'],
                acc_number=record['AUT_CNTR_ACC'],
                bic=record['AUT_CNTR_MFO'],
                bank_name=record['AUT_CNTR_MFO_NAME'],
                create=self.kw_bank_import_partner_auto_create,
                use_name_search=True, )
            if partner:
                partner_id = partner.id

            if record['ID'] == 'null':
                record['ID'] = record['BPL_REF']
            statements[statement_date]['transactions'].append({
                'name': 'Privat24 {}-{}'.format(acc_number, record['ID']),
                'date': datetime.strptime(statement_date, '%d.%m.%Y'),
                'amount': direction * float(record['BPL_SUM']),
                'unique_import_id': '%s-%s' % (acc_number, record['ID']),
                # 'account_number': record['AUT_CNTR_ACC'],
                'note': record['BPL_OSND'],
                'partner_name': record['AUT_CNTR_NAM'],
                'partner_id': partner_id,
                'ref': record['BPL_REF'],
                'payment_ref': '{} (REF-{})'.format(
                    record['BPL_OSND'],
                    record['BPL_REF'] or record['BPL_OSND']),
                'kw_bank_import_raw_acc': record['AUT_CNTR_ACC'],
                'kw_bank_import_raw_bic': record['AUT_CNTR_MFO'],
                'kw_bank_import_raw_bank_name': record[
                    'AUT_CNTR_MFO_NAME'],
                'kw_bank_import_raw_enterprise_code': record[
                    'AUT_CNTR_CRF'],
                'kw_bank_import_raw_partner_name': record['AUT_CNTR_NAM'],
                'kw_bank_import_raw_description': record['BPL_OSND'],
                'journal_id': self.id,
            })
        self.kw_bank_import_commit_statement(statements)
        return statements
