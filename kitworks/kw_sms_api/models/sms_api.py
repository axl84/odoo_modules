import logging

from odoo.addons.sms.tools.sms_api import SmsApi

_logger = logging.getLogger(__name__)


class KwSmsApi(SmsApi):

    def _contact_iap(self, local_endpoint, params):
        _logger.info({'local_endpoint': local_endpoint, 'params': params, })
        return []

    def _send_sms(self, numbers, message, provider):
        _logger.info(
            {'numbers': numbers, 'message': message, 'provider': provider, })
        return []

    def _send_sms_batch(self, messages, delivery_reports_url=False):
        """ Send SMS using IAP in batch mode

        :param messages: list of SMS to send, structured as dict [{
            'res_id':  integer: ID of sms.sms,
            'number':  string: E164 formatted phone number,
            'content': string: content to send
        }]

        :return: a list of dict [{
            'res_id': integer: ID of sms.sms,
            'state':  string: 'insufficient_credit' or 'wrong_number_format'
            or 'success' or 'queued' ,
            'credit': integer: number of credits spent to send this SMS,
            'uuid': string: current sms uuid
        }]

        :raises: normally none
        """
        for message in messages:
            sms = self.env['sms.sms']
            res_id = sms.browse(message['res_id'])
            if res_id:
                res_id.kw_sms_provider_id.sms_send(message['res_id'])
        return [{'res_id': x['res_id'], 'state': 'queued',
                 'credit': '1', 'uuid': sms.browse(x['res_id']).uuid}
                for x in messages]
