import logging

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class SendSMS(models.TransientModel):
    _inherit = 'sms.composer'

    kw_turbosms_sms_or_viber = fields.Selection(
        copy=False, default='sms', required=True, string='Sms or Viber',
        selection=[('sms', _('SMS')), ('viber', _('VIBER')),
                   ('sms_viber', _('SMS and Viber')), ], )
    kw_turbosms_is_transactional = fields.Boolean(
        string='Is transactional', )
    kw_turbosms_ttl = fields.Integer(
        string='Time-to-live', )
    kw_turbosms_image_url = fields.Char(
        string='Image url', )
    kw_turbosms_caption = fields.Char(
        string='Caption', )
    kw_turbosms_action = fields.Char(
        string='Action', )
    kw_turbosms_file_id = fields.Integer(
        string='File', )
    kw_turbosms_is_count_clicks = fields.Boolean(
        string='Count clicks', )

    def _action_send_sms(self):
        records = self._get_records()
        return self._action_send_sms_mass(records)

    def _prepare_mass_sms_values(self, records):
        rs = {}
        records = super()._prepare_mass_sms_values(records)
        for r in records:
            k = records[r]
            k['kw_turbosms_sms_or_viber'] = self.kw_turbosms_sms_or_viber
            k['kw_body_viber_sms'] = self.body
            k['kw_turbosms_is_transactional'] = \
                self.kw_turbosms_is_transactional
            k['kw_turbosms_ttl'] = self.kw_turbosms_ttl
            k['kw_turbosms_image_url'] = self.kw_turbosms_image_url
            k['kw_turbosms_caption'] = self.kw_turbosms_caption
            k['kw_turbosms_action'] = self.kw_turbosms_action
            k['kw_turbosms_file_id'] = self.kw_turbosms_file_id
            k['kw_turbosms_is_count_clicks'] = self.kw_turbosms_is_count_clicks
            rs[r] = k
        return rs
