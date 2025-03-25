# pylint: disable=R0914
import logging

from werkzeug.urls import url_join
from odoo import api, fields, models, tools
from .sms_api import KwSmsApi

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    IAP_TO_SMS_STATE_SUCCESS = {
        'queued': 'queued',
        'processing': 'process',
        'success': 'pending',
        # These below are not returned in responses from IAP API in _send
        # but are received via webhook events.
        'sent': 'pending',
        'delivered': 'sent',
    }

    kw_sms_sender_name = fields.Char(string='Sender', )
    kw_sms_provider_id = fields.Many2one('kw.sms.provider',
                                         required=True, string='Provider', )
    state = fields.Selection(selection_add=[('queued', 'Queued')],
                             ondelete={'queued': 'cascade'})

    def _send(self, unlink_failed=False, unlink_sent=True,
              raise_exception=False):
        """Modifications made compare to original _send() function:
                add res_id to 'messages' to avoid KeyError while accessing it,
                redirect source of SmsApi class to custom
        """
        messages = [{'content': body,
                     'numbers': [{'number': sms.number, 'uuid': sms.uuid}
                                 for sms in body_sms_records],
                     'res_id': body_sms_records.id, }
                    for body, body_sms_records in self.grouped('body').items()]
        delivery_reports_url = url_join(self[0].get_base_url(), '/sms/status')
        try:
            results = KwSmsApi(self.env)._send_sms_batch(
                messages, delivery_reports_url=delivery_reports_url)
        except Exception as e:
            results = [{'uuid': sms.uuid, 'state': 'server_error'}
                       for sms in self]
            _logger.info('Sent batch %s SMS: %s: failed with exception %s',
                         len(self.ids), self.ids, e)
            if raise_exception:
                raise
        else:
            _logger.info('Send batch %s SMS: ids%s: gave %s',
                         len(self.ids), self.ids, results)
        # Use logic from deprecated in v17.0 _postprocess_iap_sent_sms()
        # NOTE: method is still in use.
        results = self._postprocess_iap_sent_sms(iap_results=results)
        results_uuids = [result['uuid'] for result in results]
        all_sms_sudo = self.env['sms.sms'].sudo().search(
            [('uuid', 'in', results_uuids)]
        ).with_context(sms_skip_msg_notification=True)
        for iap_state, results_group in tools.groupby(
                results, key=lambda result: result['state']):
            sms_sudo = all_sms_sudo.filtered(
                lambda s:
                s.uuid in {result['uuid'] for result in results_group})
            if success_state := self.IAP_TO_SMS_STATE_SUCCESS.get(iap_state):
                sms_sudo.sms_tracker_id._action_update_from_sms_state(
                    success_state)
                to_delete = {'to_delete': True} if unlink_sent else {}
                sms_sudo.write({'state': success_state,
                                'failure_type': False, **to_delete})
            else:
                failure_type = self.IAP_TO_SMS_FAILURE_TYPE.get(iap_state,
                                                                'unknown')
                if failure_type != 'unknown':
                    sms_sudo.sms_tracker_id._action_update_from_sms_state(
                        'error', failure_type=failure_type)
                else:
                    sms_sudo.sms_tracker_id.\
                        _action_update_from_provider_error(iap_state)
                to_delete = {'to_delete': True} if unlink_failed else {}
                sms_sudo.write({'state': 'error',
                                'failure_type': failure_type, **to_delete})
        all_sms_sudo.mail_message_id._notify_message_notification_update()

    def _postprocess_iap_sent_sms(self, iap_results):
        results = []
        for r in iap_results:
            if r['state'] == 'queued':
                self.env['sms.sms'].sudo().browse(r['res_id']).write({
                    'state': 'queued', })
            else:
                results.append(r)
        return results

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        vals = []
        for val in vals_list:
            provider_id = self.env['kw.sms.provider']
            if 'kw_sms_provider_id' not in val or \
                    not val['kw_sms_provider_id']:
                provider_id = self.env['kw.sms.provider'].search(
                    [('state', '=', 'enabled')], limit=1)
                val['kw_sms_provider_id'] = provider_id.id
            if not provider_id:
                provider_id = self.env['kw.sms.provider'].browse(
                    val['kw_sms_provider_id'])
            val['kw_sms_sender_name'] = provider_id.sms_sender(
                val.get('kw_sms_sender_name', ''))
            # remove [1] url added by html2plaintext
            val['body'] = val['body'].split('\n\n\n[1]')[0]
            for i in range(10):
                val['body'] = val['body'].replace(f' [{i}] ', '')
            vals.append(val)
        return super().create(vals)

    def kw_sms_status(self):
        for obj in self:
            if not obj.kw_sms_provider_id:
                continue
            obj.kw_sms_provider_id.sms_status(obj.id)
