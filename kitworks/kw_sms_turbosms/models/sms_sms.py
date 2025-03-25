import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    IAP_TO_SMS_STATE = {
        'success': 'sent',
        'queued': 'queued',
        'insufficient_credit': 'sms_credit',
        'wrong_number_format': 'sms_number_format',
        'server_error': 'sms_server'
    }

    kw_turbosms_message_id = fields.Char(
        string='TurboSMS message ID', copy=False, )
    kw_turbosms_response_code = fields.Char(
        string='TurboSMS response code', copy=False, )
    kw_turbosms_response_status = fields.Char(
        string='TurboSMS response status', copy=False, )
