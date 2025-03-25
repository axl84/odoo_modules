import json
import logging
import base64
import requests
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    is_umnico_send = fields.Boolean()
    umnico_leadId = fields.Char()
    umnico_realId = fields.Char()

    def get_or_create_partner(self, sender_id, company_id=False):
        if self.chat_id.messenger_id.provider != 'umnico':
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
        if self.sender_id.umnico_channel_id:
            channel_id = self.sender_id.umnico_channel_id
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
        if not partner_id.mobile:
            partner_id.write({'mobile': sender_id.login})
        return partner_id

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'umnico':
            return super().get_or_create(chat, **kwargs)
        sender = kwargs.get('sender')
        if not sender:
            raise ValueError('Cant process: "sender_id" not provided')
        conversation = self.sudo().search([
            ('sender_id', '=', sender.id),
            ('company_id', '=', chat.company_id.id),
            ('chat_id', '=', chat.id)], limit=1)
        if not conversation:
            # TODO create id umnico conversation
            if kwargs.get('message'):
                conversation = self.sudo().create({
                    'name': kwargs.get('message', False).get('leadId', False),
                    'dialog_id': chat.dialog_id.id,
                    'company_id': chat.company_id.id,
                    'sender_id': sender.id,
                    'chat_id': chat.id,
                    # flake8: noqa: E501
                    'umnico_leadId': kwargs.get('message', False).get('leadId', False),
                    # flake8: noqa: E501
                    'umnico_realId': kwargs.get('message', False).get('message', False).get('source', False).get(
                        'realId',
                        False),
                })
            else:
                conversation = self.sudo().create({
                    'name': sender.display_name,
                    'dialog_id': chat.dialog_id.id,
                    'company_id': chat.company_id.id,
                    'sender_id': sender.id,
                    'chat_id': chat.id,
                })
            if conversation.dialog_id.is_partner:
                conversation.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
                mail_channel = conversation.create_live_chat_channel(
                    conversation.sender_id.partner_id)
                umnico_channel_id = conversation.sender_id.umnico_channel_id
                mail_channel.write({'name': '{} ({})'.format(
                    mail_channel.name,
                    umnico_channel_id.name
                    if umnico_channel_id else '', )})
                subtype = self.env['mail.message.subtype'].search(
                    [('default', '=', True)], limit=1)
                mail_channel.message_post(
                    author_id=conversation.sender_id.partner_id.id,
                    body=_('%(name)s joined you (%(type)s, %(umnico_name)s)',
                           name=conversation.sender_id.name,
                           type=umnico_channel_id.type
                           if umnico_channel_id else '',
                           umnico_name=umnico_channel_id.name
                           if umnico_channel_id else ''),
                    message_type='comment',
                    subtype_id=subtype.id, )
                if isinstance(kwargs, dict):
                    if kwargs.get('message'):
                        mail_channel.message_post(
                            author_id=conversation.sender_id.partner_id.id,
                            body=_(kwargs.get('message', False).get('message', False).get('message', False).get('text',
                                                                                                                False)),
                            message_type='comment',
                            subtype_id=subtype.id, )

        return conversation

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'umnico':
            return super().send_message(text, **kwargs)
        try:
            if self.is_personal:
                body = {
                    "message": {
                        "text": text,
                    },
                    "destination": self.sender_id.login or self.sender_id.partner_id.mobile,
                    "saId": int(self.sender_id.umnico_saId if self.sender_id.umnico_saId else self.sender_id.umnico_id),
                }
                # pylint: disable=E8106
                response = requests.request(
                    method='post',
                    url='https://api.umnico.com/v1.3/messaging/post',
                    headers={'Authorization': 'Bearer {}'.format(
                        self.chat_id.messenger_id.umnico_api_token),
                        'Host': 'api.umnico.com'},
                    json=body, )
                self.umnico_create_log(name='OUT', body=body, url=response.url, headers=response.headers, )
            else:
                # TODO source change umnico channel
                body = {
                    "message": {
                        'text': text},
                    "source": self.umnico_realId,
                    "userId": int(
                        self.chat_id.messenger_id.umnico_operator_id.umnico_id
                    )}
                # pylint: disable=E8106
                response = requests.request(
                    method='post',
                    url='https://api.umnico.com/v1.3/messaging/{}/send'.format(
                        self.umnico_leadId),
                    headers={'Authorization': 'Bearer {}'.format(
                        self.chat_id.messenger_id.umnico_api_token),
                        'Host': 'api.umnico.com'},
                    json=body, )
            # if 200 <= response.status_code < 300:
            # self.umnico_out_message(text=text)
                self.umnico_create_log(name='OUT', body=body, url=response.url, headers=response.headers, )
        except Exception as e:
            _logger.debug(e)
        return None

    def umnico_out_message(self, text=False):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].search([
            ('umnico_realId', '=', self.sender_id.umnico_realId)], limit=1)
        if sender:
            self.env['kw.chatbot.message'].sudo().create({
                'conversation_id': self.id, 'is_bot_message': True,
                'sender_id': sender.id, 'text': text,
                'name': 'None', })
        else:
            self.env['kw.chatbot.message'].sudo().create({
                'conversation_id': self.id, 'is_bot_message': True,
                'sender_id': self.sender_id.id, 'text': text,
                'name': 'None', })

    def umnico_create_log(self, name=False, body=False, **kwargs):
        self.ensure_one()
        self.env['kw.chatbot.log'].create({
            'name': name,
            'messenger_id': self.chat_id.messenger_id.id,
            'body': body,
            'chat_id': self.chat_id.id,
            'dialog_id': self.dialog_id.id,
            'sender_id': self.sender_id.id,
            'conversation_id': self.id,
            'url': kwargs.get('url', False),
            'headers': kwargs.get('headers', False),

        })

    def upload_umnico_url_file(self, text):
        try:
            url = text
            # pylint: disable=E8106
            r = requests.get(url, allow_redirects=True)
            data = r.content
            mimetype = r.headers.get('content-type')
            data = base64.b64encode(data)
            data = data.decode('utf-8')
        except Exception as e:
            _logger.debug(e)
            return False
        filename = 'umnico_file'
        attachment = self.env['ir.attachment'].sudo().create({
            'name': filename, 'datas': data,
            'mimetype': mimetype, 'res_model': 'mail.compose.message'})
        if attachment:
            attachment.write(
                {'name': '{}-{}'.format(filename, attachment.id)})
            self.connect_live_chat(attachment=attachment)
            return True
        return False

    def umnico_get_response(self, jsonrequest):
        self.ensure_one()
        text = jsonrequest.get('text')
        umnico_object = jsonrequest.get('attachments')
        if umnico_object:
            for attach in umnico_object:
                self.upload_umnico_url_file(attach.get('url'))
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if text in ['/start', '/end']:
                return None
            live_chat_mess_id = self.connect_live_chat(text=text)
            if live_chat_mess_id:
                self.write({'is_umnico_send': True})
        else:
            self.umnico_out_message(text=text)
        return False

    def send_file(self, files, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'umnico':
            return super().send_file(files, **kwargs)
        for file in files:
            if file and file.datas:
                url = self.get_attachment_url(attachment=file)
                op = self.chat_id.messenger_id.umnico_operator_id.umnico_id
                try:
                    # send file to umnico
                    if self.is_personal:
                        payload = {
                            "saId": int(self.sender_id.umnico_saId)}
                    else:
                        payload = {'source': self.umnico_realId, }
                    url = "https://api.umnico.com/v1.3/messaging/upload"

                    files = [
                        ('media', (file.name, file.raw,)),
                    ]
                    headers = {
                        'Authorization': 'Bearer {}'.format(
                            self.chat_id.messenger_id.umnico_api_token),

                    }
                    response = requests.request("POST", url, headers=headers, data=payload,
                                                files=files, timeout=20)
                    self.umnico_create_log(name='OUT', body=payload, url=url, headers=headers, )
                    # pylint: disable=E8106
                    content = response.json()
                    if self.is_personal:
                        # continue
                        payload = json.dumps({
                            "message": {
                                "text": "",
                                "attachment": content,
                            }
                            ,
                            "destination": self.sender_id.login or self.sender_id.partner_id.mobile,
                            "saId": int(self.sender_id.umnico_saId)
                        })
                        url = 'https://api.umnico.com/v1.3/messaging/post'
                        headers = {
                            'Authorization': f'Bearer {self.chat_id.messenger_id.umnico_api_token}',
                            'Content-Type': 'application/json',
                            'Host': 'api.umnico.com'
                        }
                        response = requests.request("POST", url, headers=headers, data=payload)
                        self.umnico_create_log(name='OUT', body=payload, url=url, headers=headers, )
                    else:
                        url = f"https://api.umnico.com/v1.3/messaging/{self.sender_id.umnico_leadId}/send"

                        payload = json.dumps({
                            "message": {
                                "text": "",
                                "attachment": {
                                    "media": {
                                        "path": content.get('media').get('path'),
                                        "name": content.get('media').get('name'),
                                        "mime": content.get('media').get('mime')
                                    },
                                    "type": content.get('type')
                                }
                            },
                            "source": self.umnico_realId,
                            "userId": int(op)
                        })
                        headers = {
                            'Authorization': f'Bearer {self.chat_id.messenger_id.umnico_api_token}',
                            'Content-Type': 'application/json',
                            'Host': 'api.umnico.com'
                        }
                        response = requests.request("POST", url, headers=headers, data=payload)
                        self.umnico_create_log(name='OUT', body=payload, url=response.url, headers=response.headers, )
                    self.umnico_out_message(text={'media': url})
                    self.umnico_create_log(name='OUT', body=payload)
                except Exception as e:
                    _logger.debug(e)
        return None

    def get_attachment_url(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        token = attachment.generate_access_token()
        token = token[0] if token else ''
        url = '{}/web/content/ir.attachment/{}/datas?access_token={}'.format(
            burl, attachment.id, token)
        return url

    def umnico_does_not_found(self):
        self.ensure_one()
        self.send_message(text=(self.dialog_id.not_found_msg.strip() or
                                _('There is no answer for your request')))


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    umnico_id = fields.Integer()

    raw_json = fields.Text()
