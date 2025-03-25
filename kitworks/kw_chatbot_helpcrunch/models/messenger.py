import logging

import requests
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Messenger(models.Model):
    _inherit = 'kw.chatbot.messenger'

    webhook_chat_new = fields.Char(
        compute='_compute_webhook', readonly=True, )
    webhook_message_chat_customer = fields.Char(
        compute='_compute_webhook', readonly=True, )
    api_token = fields.Char()
    operator_id = fields.Many2one(
        comodel_name='kw.chatbot.helpcrunch.operators', )
    helpcrunch_channels_ids = fields.One2many(
        comodel_name='kw.chatbot.helpcrunch.channels',
        inverse_name='messenger_id', )
    helpcrunch_developer_url = fields.Char()
    is_helpcrunch_developer_mode = fields.Boolean()

    def operators_default(self):
        for obj in self:
            if not obj.operator_id and \
                    obj.env['kw.chatbot.helpcrunch.operators'].search(
                        [], limit=1):
                obj.write({
                    'operator_id':
                        obj.env['kw.chatbot.helpcrunch.operators'].search(
                            [], limit=1)})

    @api.onchange('helpcrunch_developer_url', 'is_helpcrunch_developer_mode')
    def onchange_helpcrunch_developer_url(self):
        for obj in self:
            obj._compute_webhook()

    def _compute_webhook(self):
        for obj in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url')
            if self.is_helpcrunch_developer_mode \
                    and self.helpcrunch_developer_url:
                base_url = self.helpcrunch_developer_url.strip()
            obj.webhook_chat_new = "{}/chat/new/{}".format(base_url, self.id)
            obj.webhook_message_chat_customer = \
                "{}/message/chat/customer/{}".format(base_url, self.id)

    def get_helpcrunch_channels(self):
        self.ensure_one()
        try:
            # pylint: disable=E8106
            response = requests.request(
                method='get', url='https://api.helpcrunch.com/v1/applications',
                headers={'Authorization': f'Bearer {self.api_token}'})
            if 200 <= response.status_code < 300:
                channels = response.json()
                for obj in channels.get('data'):
                    channel = self.env[
                        'kw.chatbot.helpcrunch.channels'].search(
                        [('helpcrunch_channel_id', '=', obj.get('id'))])
                    if not channel:
                        self.env['kw.chatbot.helpcrunch.channels'].create({
                            'helpcrunch_channel_id': obj['id'],
                            'name': obj['name'],
                            'display_name': obj['displayName'],
                            'type': obj['type'], 'messenger_id': self.id})
        except Exception as e:
            _logger.debug(e)

    def update_operators(self):
        for obj in self:
            obj.get_helpcrunch_channels()
            try:
                # pylint: disable=E8106
                response = requests.request(
                    method='get', url='https://api.helpcrunch.com/v1/agents',
                    headers={'Authorization': f'Bearer {obj.api_token}'})
                if 200 <= response.status_code < 300:
                    self.env['kw.chatbot.helpcrunch.operators'].search(
                        []).unlink()
                    operators = response.json()
                    obj.search_or_create_operators(operators)
                    obj.operators_default()
                    self.env['kw.chatbot.chat'].helpcrunch_create_chat()
            except Exception as e:
                _logger.debug(e)

    def search_or_create_operators(self, operators):
        for obj in operators['data']:
            operator = self.env['kw.chatbot.helpcrunch.operators'].search([
                ('helpcrunch_id', '=', obj['id'])])
            if not operator:
                self.env['kw.chatbot.helpcrunch.operators'].create({
                    'helpcrunch_id': obj['id'], 'name': obj['name'],
                    'email': obj['email'], 'role': obj['role']})


class Operators(models.Model):
    _name = 'kw.chatbot.helpcrunch.operators'
    _description = 'Helpcrunch Operators'

    helpcrunch_id = fields.Char()
    name = fields.Char()
    email = fields.Char()
    role = fields.Char()


class HelpcrunchChannels(models.Model):
    _name = 'kw.chatbot.helpcrunch.channels'
    _description = 'Helpcrunch Channels'

    name = fields.Char(
        readonly=True, )
    display_name = fields.Char(
        readonly=True, )
    helpcrunch_channel_id = fields.Char(
        readonly=True, )
    type = fields.Char(
        readonly=True, )
    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger',
        readonly=True, ondelete='cascade', )
