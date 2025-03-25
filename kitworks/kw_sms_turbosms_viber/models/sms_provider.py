import logging

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class TurboSmsSender(models.Model):
    _inherit = 'kw.turbosms.sender'

    sms_or_viber = fields.Selection(
        default='sms', required=True, string='Sms or Viber',
        selection=[('sms', _('SMS')), ('viber', _('VIBER')),
                   ('sms_viber', _('SMS and Viber')), ], )


class SmsProvider(models.Model):
    _inherit = 'kw.sms.provider'

    turbosms_sender_id = fields.Many2one(
        string='Default SMS sender',
        domain=[('sms_or_viber', 'in', ['sms', 'sms_viber'])], )
    turbosms_viber_sender_id = fields.Many2one(
        comodel_name='kw.turbosms.sender', string='Default Viber sender',
        domain=[('sms_or_viber', 'in', ['viber', 'sms_viber'])], )

    def turbosms_sms_sender(self, sender_name):
        self.ensure_one()
        sender = self.env['kw.turbosms.sender'].search([
            ('provider_id', '=', self.id), ('name', '=', sender_name),
            ('sms_or_viber', 'in', ['sms', 'sms_viber']), ], limit=1)
        if sender:
            return sender_name
        return self.turbosms_sender_id.name

    def turbosms_viber_sender(self, sender_name):
        self.ensure_one()
        sender = self.env['kw.turbosms.sender'].search([
            ('provider_id', '=', self.id), ('name', '=', sender_name),
            ('sms_or_viber', 'in', ['viber', 'sms_viber']), ], limit=1)
        if sender:
            return sender_name
        return self.turbosms_viber_sender_id.name

    def turbosms_sms_request(self, sms_id):
        # _logger.info('turbosms_sms_request viber')
        sms = self.env['sms.sms'].browse(sms_id)
        # _logger.info(sms)
        result = {'recipients': [sms.number], }
        if sms.kw_turbosms_sms_or_viber in ['sms', 'sms_viber']:
            result['sms'] = {
                'sender': self.turbosms_sms_sender(sms.kw_sms_sender_name),
                'text': sms.body, }
        if sms.kw_turbosms_sms_or_viber in ['viber', 'sms_viber']:
            result['viber'] = {
                'sender': self.turbosms_viber_sender(sms.kw_sms_sender_name),
                'text': sms.kw_body_viber_sms, }
            if sms.kw_turbosms_is_transactional:
                result['viber']['is_transactional'] = \
                    1 if sms.kw_turbosms_is_transactional else 0
            if sms.kw_turbosms_ttl:
                result['viber']['ttl'] = sms.kw_turbosms_ttl
            if sms.kw_turbosms_image_url:
                result['viber']['image_url'] = sms.kw_turbosms_image_url
            if sms.kw_turbosms_action:
                result['viber']['action'] = sms.kw_turbosms_action
            if sms.kw_turbosms_caption:
                result['viber']['caption'] = sms.kw_turbosms_caption
            if sms.kw_turbosms_file_id:
                result['viber']['file_id'] = sms.kw_turbosms_file_id
            if sms.kw_turbosms_is_count_clicks:
                result['viber']['is_count_clicks'] = \
                    1 if sms.kw_turbosms_is_count_clicks else 0
        # _logger.info(result)
        return result
