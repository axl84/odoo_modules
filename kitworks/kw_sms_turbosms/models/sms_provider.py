import json
import logging

import requests
from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class TurboSmsSender(models.Model):
    _name = 'kw.turbosms.sender'
    _description = 'Sender'
    _sql_constraints = [
        ('provider_id_sender_uniq', 'unique(provider_id, name)',
         _('This sender already assign to this provider')), ]

    provider_id = fields.Many2one(
        comodel_name='kw.sms.provider', required=True, )
    name = fields.Char(
        required=True, string="Sender")


class SmsProvider(models.Model):
    _inherit = 'kw.sms.provider'

    turbosms_token = fields.Char(
        string='HTTP auth token', )
    turbosms_sender_id = fields.Many2one(
        comodel_name='kw.turbosms.sender', string='Default sender', )
    turbosms_balance = fields.Float(
        string='Balance', readonly=True, )
    turbosms_sender_ids = fields.One2many(
        comodel_name='kw.turbosms.sender', inverse_name='provider_id', )

    def turbosms_sms_sender(self, sender_name):
        self.ensure_one()
        sender = self.env['kw.turbosms.sender'].search([
            ('provider_id', '=', self.id), ('name', '=', sender_name)
        ], limit=1)
        if sender:
            return sender_name
        return self.turbosms_sender_id.name

    def turbosms_request_url(self, url, r=False):
        self.ensure_one()
        r = json.dumps(r or {})
        headers = {'Authorization': 'Basic {}'.format(self.turbosms_token),
                   'Content-Type': 'application/json'}
        url = 'https://api.turbosms.ua{}'.format(url)
        if self.is_log_enabled:
            log = self.env['kw.sms.log'].create({
                'request': r, 'request_url': url, 'provider_id': self.id, })
        r = requests.post(url=url, data=r, headers=headers, timeout=10)
        if r.status_code != 200:
            if self.is_log_enabled:
                log.write({'response': r.status_code})
            return False
        if self.is_log_enabled:
            log.write({'response': r.text})
        try:
            r = r.json()
        except Exception as e:
            _logger.info(e)
        else:
            return r
        return False

    def turbosms_get_balance(self):
        for obj in self:
            r = obj.turbosms_request_url('/user/balance.json')
            if r and r['response_code'] == 0:
                obj.turbosms_balance = r['response_result']['balance']

    def turbosms_sms_request(self, sms_id):
        # _logger.info('turbosms_sms_request')
        sms_id = self.env['sms.sms'].browse(sms_id)
        return {'recipients': [sms_id.number], 'sms': {
            'sender': sms_id.kw_sms_sender_name, 'text': sms_id.body, }}

    def turbosms_sms_send(self, sms_id):
        # _logger.info('turbosms_sms_send')
        self.ensure_one()
        sms = self.env['sms.sms'].browse(sms_id)
        r = self.turbosms_sms_request(sms_id)
        if self.state != 'enabled':
            _logger.info(r)
            sms.write({'kw_turbosms_response_status': 'test'})
            return
        r = self.turbosms_request_url('/message/send.json', r)
        if r and r['response_code']:
            param = {}
            if r['response_code'] in [0, 800, 801, 802, 803, ]:
                param['state'] = 'sent'
                if 'response_result' in r:
                    param['kw_turbosms_message_id'] = \
                        r['response_result'][0]['message_id']
            else:
                param['state'] = 'error'
            param['kw_turbosms_response_code'] = r['response_code']
            param['kw_turbosms_response_status'] = r['response_status']
            sms.write(param)

    def turbosms_sms_status(self, sms_id):
        self.ensure_one()
        sms = self.env['sms.sms'].browse(sms_id)
        r = {'messages': [sms.kw_turbosms_message_id], }
        r = self.turbosms_request_url('/message/status.json', r)
        if r and r['response_code'] in [0]:
            param = {
                'kw_turbosms_message_id':
                    r['response_result'][0]['message_id'],
                'kw_turbosms_response_code':
                    r['response_result'][0]['response_code'],
                'kw_turbosms_response_status':
                    r['response_result'][0]['response_status'], }
            if r['response_result'][0]['response_code'] == 0:
                param['state'] = 'sent'
            else:
                param['state'] = 'error'
            sms.write(param)
        else:
            sms_id.write({'state': 'error'})
