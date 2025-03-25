import hashlib
import logging
import os

from odoo.addons.kw_graph_api.models.graph_api import FacebookGraphApi
from odoo import models, fields, exceptions, api, _

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    whatsapp_access_token = fields.Char(
        string='WhatsApp Access Token')
    whatsapp_business_account = fields.Char(
        string='WhatsApp Business Account ID')

    whatsapp_phone_number = fields.Char(
        readonly=True, string='WhatsApp Phone Number')
    whatsapp_phone_number_id = fields.Char(
        readonly=True, string='WhatsApp Phone Number ID')

    whatsapp_facebook_app_id = fields.Many2one(
        comodel_name='kw.facebook.app',
        string='Facebook App', ondelete='cascade', )
    whatsapp_connect_status = fields.Selection(
        string='Connect Status', readonly=True, default='disabled', selection=[
            ('disabled', 'Disabled'), ('enabled', 'Enabled')], )

    whatsapp_error_msg = fields.Text(
        readonly=True, string='Error')

    whatsapp_verify_token = fields.Char()
    whatsapp_callback_url = fields.Char(
        compute='_compute_whatsapp_callback_url', )
    whatsapp_webhook_status = fields.Selection(
        string='Webhook Status', readonly=True, default='disabled', selection=[
            ('disabled', 'Disabled'), ('enabled', 'Enabled')], )

    whatsapp_timestamp = fields.Float()

    def whatsapp_webhook_action(self):
        self.ensure_one()
        context = {
            'default_facebook_app_id': self.whatsapp_facebook_app_id.id,
            'default_facebook_object': 'whatsapp_business_account',
            'default_facebook_fields': 'messages',
            'default_callback_url':
                self.whatsapp_callback_url,
            'default_verify_token':
                self.whatsapp_verify_token, }
        webhook = self.env['facebook.webhook.wizard'].sudo().with_context(
            **context).create({})
        return webhook.facebook_update_webhook()

    def whatsapp_update_verify_token(self):
        for obj in self:
            obj.write({
                'whatsapp_verify_token': obj.whatsapp_generate_verify_token(),
                'whatsapp_webhook_status': 'disabled'})

    def whatsapp_update_webhook(self):
        for obj in self:
            return obj.whatsapp_webhook_action()

    @api.model
    def whatsapp_generate_verify_token(self):
        r_bytes = os.urandom(16)
        return str(hashlib.sha256(r_bytes).hexdigest())

    def _compute_whatsapp_callback_url(self):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for obj in self:
            obj.whatsapp_callback_url = \
                '{url}/kw_chatbot/whatsapp/bot/{id}'.format(
                    url=burl, id=obj.id if obj.id else '')

    def whatsapp_connect_phone_number(self):
        self.ensure_one()
        self.write({
            'whatsapp_error_msg': '',
            'whatsapp_webhook_status': 'disabled',
            'whatsapp_connect_status': 'disabled'})
        params = {'access_token': self.whatsapp_access_token}
        apps = FacebookGraphApi().get_facebook_graph(
            url='/{}/subscribed_apps'.format(self.whatsapp_business_account),
            params=params)
        apps = self.whatsapp_error_handling(apps)
        for app in apps.get('data'):
            whatsapp_bad = app.get('whatsapp_business_api_data')
            f_app_id = self.whatsapp_facebook_app_id.app_id
            if whatsapp_bad:
                if whatsapp_bad.get('id') != f_app_id:
                    self.write({
                        'whatsapp_connect_status': 'disabled',
                        'whatsapp_webhook_status': 'disabled',
                        'whatsapp_error_msg':
                            'This WhatsApp business account does'
                            ' not correspond to this Facebook App ({})'.format(
                                self.whatsapp_facebook_app_id.name)})
            else:
                self.write({
                    'whatsapp_connect_status': 'disabled',
                    'whatsapp_webhook_status': 'disabled',
                    'whatsapp_error_msg':
                        'This WhatsApp business account was not found'})
        if not self.whatsapp_error_msg:
            params = {'access_token': self.whatsapp_access_token,
                      'fields': 'id,name,phone_numbers'}
            whatsapp_b = FacebookGraphApi().get_facebook_graph(
                url='/{}'.format(self.whatsapp_business_account),
                params=params)
            whatsapp_b = self.whatsapp_error_handling(whatsapp_b)
            if whatsapp_b.get('phone_numbers'):
                phone_numbers = whatsapp_b.get('phone_numbers').get('data')[0]
                self.get_whatsapp_long_lived_token()
                self.write({
                    'name': whatsapp_b.get('name'),
                    'whatsapp_phone_number':
                        phone_numbers.get('display_phone_number'),
                    'whatsapp_connect_status': 'enabled',
                    'whatsapp_phone_number_id': phone_numbers.get('id')})

    # pylint: disable=E8105
    # pylint: disable=W8115
    @staticmethod
    def whatsapp_error_handling(data):
        if data.get('error'):
            raise exceptions.ValidationError(_(f"{data.get('error')}"))
        return data.get('data')

    def _get_whatsapp_long_lived_token(self):
        w_chat = self.env['kw.chatbot.chat'].sudo().search([
            ('provider', '=', 'whatsapp'),
            ('active', '=', True), ])
        for w in w_chat:
            w.get_whatsapp_long_lived_token()

    def get_whatsapp_long_lived_token(self):
        self.ensure_one()
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.whatsapp_facebook_app_id.app_id,
            'client_secret': self.whatsapp_facebook_app_id.facebook_app_secret,
            'fb_exchange_token': self.whatsapp_access_token}
        res = FacebookGraphApi().get_facebook_graph(
            url='/oauth/access_token', params=params)
        if res.get('data'):
            token = res['data'].get('access_token')
            if token:
                self.write({'whatsapp_access_token': token})
        else:
            self.write({
                'whatsapp_connect_status': 'disabled',
                'whatsapp_webhook_status': 'disabled',
                'whatsapp_error_msg':
                    'Failed to get long-term token!{}'.format(
                        res.get('error'))})

    def whatsapp_process_message(self, message, log):
        self.ensure_one()
        for contact in message.get('contacts'):
            sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=self.messenger_id, sender=contact)
            conversation = self.env['kw.chatbot.conversation'].sudo(
            ).get_or_create(
                chat=self, message=message, contact=contact, sender=sender)
            log.sudo().write({
                'sender_id': sender.id,
                'conversation_id': conversation.id})
            for m_message in message.get('messages'):
                if m_message.get('text'):
                    m_text = m_message['text']
                if m_message.get('interactive'):
                    m_text = {
                        'body': m_message['interactive'].get(
                            'button_reply').get('title')}
                if m_text:
                    if m_message.get('from') == contact.get('wa_id'):
                        text = m_text.get('body')
                        conversation.chatbot_message_id = \
                            self.env['kw.chatbot.message'].sudo().create({
                                'whatsapp_id': sender.whatsapp_id,
                                'conversation_id': conversation.id,
                                'sender_id': sender.id, 'text': text,
                                'name': text, })
                        conversation.last_activity_datetime = \
                            fields.Datetime.now()
                        conversation.whatsapp_get_response(text)

    def whatsapp_process_call(self, jsonrequest, log):
        self.ensure_one()
        for entry in jsonrequest.get('entry'):
            for event in entry.get('changes'):
                messaging = event['value'].get('messages')
                if messaging:
                    for message in messaging:
                        if self.whatsapp_timestamp == float(
                                message.get('timestamp')):
                            return "success"
                        self.whatsapp_timestamp = message.get('timestamp')
                        self.whatsapp_process_message(
                            message=event['value'], log=log)
        return None

    def get_all_whatsapp_template(self):
        params = {'access_token': self.whatsapp_access_token}
        res = FacebookGraphApi().get_facebook_graph(
            params=params,
            url='/{}/message_templates'.format(self.whatsapp_business_account))
        if res.get('data'):
            for template in res['data']['data']:
                template_id = self.env['kw.chatbot.whatsapp.template'].search([
                    ('template_id', '=', template.get('id'))])
                if not template_id:
                    data = {
                        'name': template.get('name'),
                        'template_name': template.get('name'),
                        'template_id': template.get('id'),
                        'status': template.get('status').lower(),
                        'lang': template.get('language'),
                        'chat_id': self.id,
                        'template_category': template.get('category').lower(),
                        'model_id': self.env['ir.model']._get_id(
                            'res.partner')}
                    for component in template.get('components'):
                        component_type = component['type']
                        if component_type == 'HEADER':
                            data.update({'header_text': component.get('text')})
                        if component_type == 'BODY':
                            data.update({'body_text': component.get('text')})
                        if component_type == 'FOOTER':
                            data.update({'footer_text': component.get('text')})
                    self.env['kw.chatbot.whatsapp.template'].sudo().create(
                        data)
        return res
