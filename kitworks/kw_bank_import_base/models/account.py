import logging
from datetime import datetime

from odoo import models, fields, _
# from odoo.osv.expression import OR, AND

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = 'account.journal'

    kw_bank_import_module_type = fields.Selection(
        string='Import type', selection=[], )
    kw_bank_import_partner_auto_create = fields.Boolean(
        string='Create partner automatically', default=False, )
    kw_bank_import_initial_date = fields.Date(
        string='Initial date', )
    default_credit_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Credit Account',
        domain=[('deprecated', '=', False)],
        help="It acts as a default account for credit amount",
        ondelete='restrict')
    default_debit_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Debit Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        help="It acts as a default account for debit amount",
        ondelete='restrict')

    def import_statement(self):
        action_name = 'kw_action_account_bank_statement_import'
        [action] = self.env.ref(
            'kw_bank_import_base.{}'.format(action_name)).read()
        action.update({'context': (u"{'journal_id': " + str(self.id) + u"}")})
        return action

    def _get_bank_statements_available_import_formats(self):
        return ['File']

    def __get_bank_statements_available_sources(self):
        rslt = super(AccountJournal, self)
        rslt = rslt.__get_bank_statements_available_sources()
        formats_list = self._get_bank_statements_available_import_formats()
        _logger.info(formats_list)
        if formats_list:
            import_formats_str = ', '.join(formats_list)
            rslt.append((
                "file_import", _("Import {}").format(import_formats_str)))
        return rslt

    def kw_bank_import_prepare_statement(self, statements):
        self.ensure_one()
        return statements

    def statement_state_posted(self):
        statement_ids = self.env['account.bank.statement'].search(
            [('journal_id', '=', self.id), ('state', '=', 'open')])
        for statement in statement_ids:
            if statement.date < datetime.now().date() \
                    and datetime.now().time().hour > 1:
                statement.update({'state': 'posted'})

    def kw_bank_import_commit_statement(self, statements):
        self.ensure_one()
        statements = self.kw_bank_import_prepare_statement(statements)

        for st in statements.values():
            date = datetime.strptime(st['date'], '%d.%m.%Y')
            statement = self.env['account.bank.statement'].search(
                [('journal_id', '=', self.id), ('name', '=', st['name']), ],
                limit=1)
            if not statement:
                statement = self.env['account.bank.statement'].create({
                    'name': st['name'],
                    'date': date,
                    'balance_start': st.get('balance_start') or 0,
                    'balance_end_real': st.get('balance_end_real') or 0,
                    'journal_id': self.id, })
            else:
                statement.update({
                    'balance_start': st['balance_start'] or 0,
                    'balance_end_real': st['balance_end_real'] or 0, })
            for line in st['transactions']:
                domain = []
                if 'unique_import_id' in line:
                    domain = [
                        ('unique_import_id', '=', line['unique_import_id'])]
                elif 'ref' in line:
                    domain = [
                        ('journal_id', '=', self.id),
                        ('ref', '=', line['ref'],)]

                narration_fields = [
                    'kw_bank_import_raw_description',
                    'kw_bank_import_raw_partner_name',
                    'kw_bank_import_raw_enterprise_code', ]
                line['narration'] = ' | '.join(
                    [line.get(x) or '' for x in narration_fields])

                st_line = None
                if domain:
                    st_line = self.env['account.bank.statement.line'].search(
                        domain, limit=1)
                    if st_line:
                        try:
                            st_line.update(line)
                        except Exception as e:
                            _logger.info(e)
                            _logger.info(st_line)
                if not st_line:
                    line['statement_id'] = statement.id
                    try:
                        self.env['account.bank.statement.line'].create(line)
                    except Exception as e:
                        _logger.info(e)
                        _logger.info(line)
