import logging

import requests
from odoo import models, fields

_logger = logging.getLogger(__name__)


class Messenger(models.Model):
    _inherit = 'kw.chatbot.messenger'

    umnico_webhook_message_chat = fields.Char(
        compute='_compute_umnico_webhook', readonly=True, )
    umnico_api_token = fields.Char(
        string='Token')
    umnico_channels_ids = fields.One2many(
        comodel_name='kw.chatbot.umnico.channels',
        inverse_name='messenger_id', )
    umnico_operator_id = fields.Many2one(
        comodel_name='kw.chatbot.umnico.operators', )
    is_umnico_webhook = fields.Boolean(
        default=False)
    dialog_id = fields.Many2one('kw.chatbot.dialog', string='Dialog')

    def _compute_umnico_webhook(self):
        for obj in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url')
            obj.umnico_webhook_message_chat = \
                "{}/message/chat/umnico/{}".format(base_url, self.id)

    def get_umnico_channels(self):
        self.ensure_one()
        try:
            # pylint: disable=E8106
            response = requests.request(
                method='get',
                url='https://api.umnico.com/v1.3/integrations',
                headers={'Authorization': 'Bearer {}'.format(
                    self.umnico_api_token),
                    'Host': 'api.umnico.com'})
            if 200 <= response.status_code < 300:
                channels = response.json()
                if channels:
                    for obj in channels:
                        channel = self.env['kw.chatbot.umnico.channels'].sudo(
                        ).search(
                            [('umnico_channel_id', '=', obj.get('id'))])
                        if not channel:
                            self.env['kw.chatbot.umnico.channels'].create({
                                'umnico_channel_id': obj['id'],
                                'name': obj['login'], 'type': obj['type'],
                                'externalId': obj['externalId'],
                                'url': obj['url'], 'messenger_id': self.id, })
        except Exception as e:
            _logger.debug(e)

    def update_umnico_webhook(self):
        self.delete_umnico_webhook()
        try:
            body = {'url': self.umnico_webhook_message_chat}
            # pylint: disable=E8106
            response = requests.request(
                method='post',
                url='https://api.umnico.com/v1.3/webhooks',
                json=body,
                headers={'Authorization': 'Bearer {}'.format(
                    self.umnico_api_token),
                    'Host': 'api.umnico.com'})
            data = response.json()
            if 200 <= response.status_code < 300 \
                    or data.get('error') == 'This server already exists':
                self.write({'is_umnico_webhook': True})
        except Exception as e:
            _logger.debug(e)

    def add_umnico_chat(self):
        self.get_umnico_channels()
        self.umnico_update_operators()
        self.env['kw.chatbot.chat'].umnico_create_chat(
            dialog_id=self.dialog_id)

    def get_umnico_webhook(self):
        try:
            # pylint: disable=E8106
            response = requests.request(
                method='get',
                url='https://api.umnico.com/v1.3/webhooks',
                headers={'Authorization': 'Bearer {}'.format(
                    self.umnico_api_token),
                    'Host': 'api.umnico.com'})
            if 200 <= response.status_code < 300:
                return response.json()
        except Exception as e:
            _logger.debug(e)
        return False

    def delete_umnico_webhook(self):
        webhooks = self.get_umnico_webhook()
        if webhooks:
            for w in webhooks:
                try:
                    # pylint: disable=E8106
                    requests.request(
                        method='delete',
                        url='https://api.umnico.com/v1.3/webhooks/{}'.format(
                            w.get('id')),
                        headers={'Authorization': 'Bearer {}'.format(
                            self.umnico_api_token),
                            'Host': 'api.umnico.com'})
                except Exception as e:
                    _logger.debug(e)

    def umnico_update_operators(self):
        try:
            # pylint: disable=E8106
            response = requests.request(
                method='get',
                url='https://api.umnico.com/v1.3/managers',
                headers={'Authorization': 'Bearer {}'.format(
                    self.umnico_api_token),
                    'Host': 'api.umnico.com'})
            if 200 <= response.status_code < 300:
                for obj in response.json():
                    operator = self.env['kw.chatbot.umnico.operators'].search([
                        ('umnico_id', '=', obj['id'])])
                    if not operator:
                        op = self.env['kw.chatbot.umnico.operators'].create({
                            'umnico_id': obj['id'], 'name': obj['name'],
                            'email': obj['login'], 'role': obj['role']})
                        if op:
                            self.write({'umnico_operator_id': op.id})
        except Exception as e:
            _logger.debug(e)


class UmnicoOperators(models.Model):
    _name = 'kw.chatbot.umnico.operators'
    _description = 'Umnico Operators'

    umnico_id = fields.Char()
    name = fields.Char()
    email = fields.Char()
    role = fields.Char()


class UmnicoChannels(models.Model):
    _name = 'kw.chatbot.umnico.channels'
    _description = 'Umnico Channels'
    _rec_name = 'display_name'

    name = fields.Char(
        readonly=True, )
    umnico_channel_id = fields.Char(
        readonly=True, )
    display_name = fields.Char(
        compute='_compute_display_name', index=True)
    type = fields.Char(
        readonly=True, )
    externalId = fields.Char(
        readonly=True, )
    url = fields.Char(
        readonly=True, )
    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger',
        readonly=True, ondelete='cascade', )

    def _compute_display_name(self):
        for obj in self:
            obj.display_name = '{} ({})'.format(
                obj.type.title(), obj.name)
