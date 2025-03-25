from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = ['account.journal', 'kw.privat24.autoclient.mixin',
                'kw.finance.statement.import.mixin', ]

    privat24_id = fields.Char(
        string='Privat24 Autoclient ID', )
    privat24_token = fields.Char(
        string='Privat24 Autoclient Token', )
    privat24_auto_sync = fields.Boolean(
        default=False, )

    @api.constrains('privat24_id')
    def constraint_privat24_id(self):
        for obj in self:
            if obj.bank_statements_source == 'privat24_autoclient' \
                    and not obj.privat24_id:
                raise ValidationError(_(
                    'Privat24 Autoclient is selected for Bank Feeds, '
                    'therefore the field "Privat24 Autoclient ID"'
                    ' canot be empty!'))

    def __get_bank_statements_available_sources(self):
        res = super().__get_bank_statements_available_sources()
        res.append(('privat24_autoclient', _('Privat24 Autoclient')))
        return res

    def test_privat24_autoclient_connection(self):
        self.ensure_one()
        client = self.kw_privat24_get_autoclient()
        try:
            client.get_rest_today()
            notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'type': 'success',
                    'message': _('Connection with Privat24 '
                                 'AutoClient were successful.'),
                    'sticky': False,
                }
            }
            return notification
        except Exception as e:
            raise ValidationError(e)
