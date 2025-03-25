import logging

import requests
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Messenger(models.Model):
    _inherit = 'kw.chatbot.messenger'

    wepster_webhook_message_chat = fields.Char(
        compute='_compute_wepster_webhook', readonly=True, )
    wepster_api_token = fields.Char(
        strint='Token')
    wepster_businessId = fields.Char(
        string='BusinessId')
    wepster_channels_ids = fields.One2many(
        comodel_name='kw.chatbot.wepster.channels',
        inverse_name='messenger_id', )
    wepster_developer_url = fields.Char()
    is_wepster_developer_mode = fields.Boolean()

    @api.onchange('wepster_developer_url', 'is_wepster_developer_mode')
    def onchange_helpcrunch_developer_url(self):
        for obj in self:
            obj._compute_wepster_webhook()

    def _compute_wepster_webhook(self):
        for obj in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url')
            if self.is_wepster_developer_mode \
                    and self.wepster_developer_url:
                base_url = self.wepster_developer_url.strip()
            obj.wepster_webhook_message_chat = \
                "{}/message/chat/wepster/{}".format(base_url, self.id)

    def get_wepster_channels(self):
        self.ensure_one()
        try:
            # pylint: disable=E8106
            response = requests.request(
                method='get',
                url='https://my.wepster.com/api/v1/channels/{}'.format(
                    self.wepster_businessId),
                headers={'wepster': self.wepster_api_token})
            if 200 <= response.status_code < 300:
                channels = response.json().get('channels')
                if channels:
                    for obj in channels:
                        channel = self.env['kw.chatbot.wepster.channels'].sudo(
                            ).search(
                                [('wepster_channel_id', '=', obj.get('id'))])
                        if not channel:
                            self.env['kw.chatbot.wepster.channels'].create({
                                'wepster_channel_id': obj['id'],
                                'name': obj['name'], 'type': obj['type'],
                                'messenger_id': self.id, })
        except Exception as e:
            _logger.debug(e)

    def add_chat(self):
        self.get_wepster_channels()
        self.env['kw.chatbot.chat'].wepster_create_chat()


class WepsterChannels(models.Model):
    _name = 'kw.chatbot.wepster.channels'
    _description = 'Wepster Channels'
    _rec_name = 'display_name'

    name = fields.Char(
        readonly=True, )
    display_name = fields.Char(
        compute='_compute_display_name', index=True)
    wepster_channel_id = fields.Char(
        readonly=True, )
    type = fields.Char(
        readonly=True, )
    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger',
        readonly=True, ondelete='cascade', )

    def _compute_display_name(self):
        for obj in self:
            obj.display_name = '{} ({})'.format(
                obj.type.title(), obj.name)
