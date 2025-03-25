from odoo import models


class SetupBarBankConfigWizard(models.TransientModel):
    _inherit = 'account.setup.bank.manual.config'

    def validate(self):
        super(SetupBarBankConfigWizard, self).validate()
        acc = self.env['account.journal']
        if (self.num_journals_without_account == 0 or
                self.linked_journal_id.bank_statements_source == 'undefined') \
                and acc._get_bank_statements_available_import_formats():
            self.linked_journal_id.bank_statements_source = 'file_import'
        return True
