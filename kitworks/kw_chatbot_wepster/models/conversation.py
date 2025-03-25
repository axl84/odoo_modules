import logging
import base64

import requests
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    is_wepster_send = fields.Boolean()

    def get_or_create_partner(self, sender_id, company_id=False):
        if self.chat_id.messenger_id.provider != 'wepster':
            return super().get_or_create_partner(sender_id, company_id)
        partner_id = sender_id.partner_id
        if not sender_id.partner_id:
            partner_id = self.env['res.partner'].sudo().create({
                'name': sender_id.name, })
            if company_id:
                partner_id.write({'company_id': company_id.id, })
            sender_id.write({'partner_id': partner_id.id})

        tag = self.env['res.partner.category'].search([
            ('name', '=', self.chat_id.name), ])
        if not tag:
            tag = self.env['res.partner.category'].create({
                'name': self.chat_id.name,
                'partner_ids': partner_id.ids})
        tag.write({'partner_ids': [(4, partner_id.id)]})
        if self.sender_id.wepster_channel_id:
            channel_id = self.sender_id.wepster_channel_id
            parent_tag_id = self.env['res.partner.category'].search([
                ('parent_id', '=', tag.id),
                ('name', '=', '{}-{}'.format(
                    channel_id.type, channel_id.name)), ])
            if not parent_tag_id:
                self.env['res.partner.category'].create({
                    'name': '{}-{}'.format(
                        channel_id.type, channel_id.name),
                    'parent_id': tag.id,
                    'partner_ids': partner_id.ids, })
            parent_tag_id.write({'partner_ids': [(4, partner_id.id)]})
        return partner_id

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'wepster':
            return super().get_or_create(chat, **kwargs)
        sender = kwargs.get('sender')
        if not sender:
            raise ValueError('Cant process: "sender_id" not provided')
        conversation = self.sudo().search([
            ('sender_id', '=', sender.id),
            ('company_id', '=', chat.company_id.id),
            ('chat_id', '=', chat.id)], limit=1)
        if not conversation:
            conversation = self.sudo().create({
                'name': sender.wepster_id,
                'dialog_id': chat.dialog_id.id,
                'company_id': chat.company_id.id,
                'sender_id': sender.id,
                'chat_id': chat.id, })
            if conversation.dialog_id.is_partner:
                conversation.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
                mail_channel = conversation.create_live_chat_channel(
                    conversation.sender_id.partner_id)
                wepster_channel_id = conversation.sender_id.wepster_channel_id
                mail_channel.write({'name': '{} ({})'.format(
                    mail_channel.name,
                    wepster_channel_id.name
                    if wepster_channel_id else '', )})
                subtype = self.env['mail.message.subtype'].search(
                    [('default', '=', True)], limit=1)
                mail_channel.message_post(
                    author_id=conversation.sender_id.partner_id.id,
                    body=_('%(name)s joined you (%(type)s, %(wepster_name)s)',
                           name=conversation.sender_id.name,
                           type=wepster_channel_id.type
                           if wepster_channel_id else '',
                           wepster_name=wepster_channel_id.name
                           if wepster_channel_id else ''),
                    message_type='comment',
                    subtype_id=subtype.id, )
        return conversation

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'wepster':
            return super().send_message(text, **kwargs)
        try:
            body = {"messenger_id": self.sender_id.wepster_id,
                    "message": text, }
            # pylint: disable=E8106
            requests.request(
                method='post',
                url='https://my.wepster.com/api/v1/bots/{}/send_'
                    'message'.format(
                        self.chat_id.messenger_id.wepster_api_token),
                json=body, )
            # if 200 <= response.status_code < 300:
            self.wepster_out_message(text=text)
            self.wepster_create_log(name='OUT', body=body)
        except Exception as e:
            _logger.debug(e)
        return None

    def wepster_out_message(self, text=False):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].search([
            ('name', '=', 'Wepster')], limit=1)
        self.env['kw.chatbot.message'].sudo().create({
            'conversation_id': self.id, 'is_bot_message': True,
            'sender_id': sender.id if sender else False, 'text': text,
            'name': 'None', })

    def wepster_create_log(self, name=False, body=False):
        self.ensure_one()
        self.env['kw.chatbot.log'].create({
            'name': name,
            'messenger_id': self.chat_id.messenger_id.id,
            'body': body,
            'chat_id': self.chat_id.id,
            'dialog_id': self.dialog_id.id,
            'sender_id': self.sender_id.id,
            'conversation_id': self.id,
        })

    def upload_webster_url_file(self, text):
        try:
            url = 'https://my.wepster.com/{}'.format(text)
            # pylint: disable=E8106
            r = requests.get(url, allow_redirects=True)
            data = r.content
            mimetype = r.headers.get('content-type')
            data = base64.b64encode(data)
            data = data.decode('utf-8')
        except Exception as e:
            _logger.debug(e)
            return False
        filename = 'wepster_file'
        attachment = self.env['ir.attachment'].sudo().create({
            'name': filename, 'datas': data,
            'mimetype': mimetype, 'res_model': 'mail.compose.message'})
        if attachment:
            attachment.write(
                {'name': '{}-{}'.format(filename, attachment.id)})
            self.connect_live_chat(attachment=attachment)
            return attachment
        return False

    def wepster_get_response(self, jsonrequest):
        self.ensure_one()
        text = jsonrequest['message']['text']
        wepster_object = jsonrequest['message'].get('object')
        if wepster_object and wepster_object.get('wepster_photo'):
            if self.upload_webster_url_file(
                    wepster_object.get('wepster_photo')):
                return None
        if wepster_object and wepster_object.get('wepster_document'):
            if self.upload_webster_url_file(
                    wepster_object.get('wepster_document')):
                return None
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if text in ['/start', '/end']:
                return None
            live_chat_mess_id = self.connect_live_chat(text=text)
            if live_chat_mess_id:
                self.write({'is_wepster_send': True})
        return False

    def send_file(self, files, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'wepster':
            return super().send_file(files, **kwargs)
        for file in files:
            if file and file.datas:
                url = self.wepster_get_attachment_url(attachment=file)
                try:
                    body = {
                        "messenger_id": self.sender_id.wepster_userId,
                        "file_href": url}
                    # pylint: disable=E8106
                    requests.request(
                        method='post',
                        url='https://my.wepster.com/api/v1/bots/{}/'
                            'send_message'.format(
                                self.chat_id.messenger_id.wepster_api_token),
                        json=body, )
                    self.wepster_out_message(text={'media': url})
                    self.wepster_create_log(name='OUT', body=body)
                except Exception as e:
                    _logger.debug(e)
        return None

    def wepster_get_attachment_url(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        messenger_id = self.chat_id.messenger_id
        if messenger_id.is_wepster_developer_mode \
                and messenger_id.wepster_developer_url:
            burl = messenger_id.wepster_developer_url.strip()
        token = attachment.generate_access_token()
        token = token[0] if token else ''
        url = '{}/web/content/ir.attachment/{}/datas?access_token={}'.format(
            burl, attachment.id, token)
        return url


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    wepster_id = fields.Integer()

    raw_json = fields.Text()
