import logging

from odoo import models, exceptions, _
from .api import Privat24AutoclientApi

_logger = logging.getLogger(__name__)

# try:
#     from privat24_autoclient import Privat24AutoclientApi
# except (ImportError, IOError) as err:
#     _logger.debug(err)


class Privat24AutoClientMixin(models.AbstractModel):
    _name = 'kw.privat24.autoclient.mixin'
    _description = 'kw.privat24.autoclient.mixin'

    # pylint: disable=R1710
    def kw_privat24_get_autoclient(self):
        self.ensure_one()
        if not self.privat24_id:
            return
        bank_account_id = self.bank_account_id
        if not bank_account_id:
            raise exceptions.ValidationError(
                _('Wrong! Add an account number'))
        return Privat24AutoclientApi(
            bank_acc_number=bank_account_id.acc_number.replace(' ', ''),
            client_id=self.privat24_id,
            token=self.privat24_token, )
