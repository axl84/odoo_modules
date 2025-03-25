import logging
import base64

import requests
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    is_helpcrunch_send = fields.Boolean()

    def get_or_create_partner(self, sender_id, company_id=False):
        if self.chat_id.messenger_id.provider != 'help_crunch':
            return super().get_or_create_partner(sender_id, company_id)
        partner_id = sender_id.partner_id
        if not sender_id.partner_id:
            partner_id = self.env['res.partner'].sudo().create({
                'name': sender_id.name, })
            if company_id:
                partner_id.write({'company_id': company_id.id, })
            sender_id.write({'partner_id': partner_id.id})
        tag_channel = self.env['res.partner.category'].search([
            ('name', '=', sender_id.help_crunch_channel_id.display_name), ],
            limit=1)
        if not tag_channel:
            tag_channel = self.env['res.partner.category'].create({
                'name': sender_id.help_crunch_channel_id.display_name, })
        tag_channel.write({'partner_ids': [(4, partner_id.id)]})

        tag = self.env['res.partner.category'].search([
            ('name', '=', self.chat_id.name), ])
        if not tag:
            tag = self.env['res.partner.category'].create({
                'name': self.chat_id.name,
                'partner_ids': partner_id.ids})
        tag.write({'partner_ids': [(4, partner_id.id)]})
        if self.sender_id.help_crunch_channel_id:
            channel_id = self.sender_id.help_crunch_channel_id
            parent_tag_id = self.env['res.partner.category'].search([
                ('parent_id', '=', tag.id),
                ('name', '=', '{}-{}'.format(
                    channel_id.type, channel_id.display_name)), ])
            if not parent_tag_id:
                self.env['res.partner.category'].create({
                    'name': '{}-{}'.format(
                        channel_id.type, channel_id.display_name),
                    'parent_id': tag.id,
                    'partner_ids': partner_id.ids, })
            parent_tag_id.write({'partner_ids': [(4, partner_id.id)]})
            return partner_id
        return None

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'help_crunch':
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
                'name': sender.help_crunch_id,
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
                hp_channel_id = conversation.sender_id.help_crunch_channel_id
                lc_name = '{} ({})'.format(
                    mail_channel.name, hp_channel_id.display_name)
                for lang in self.env['res.lang'].search(
                        [('active', '=', True)]):
                    mail_channel.with_context(
                        lang=lang.code).write({'name': lc_name})
                subtype = self.env['mail.message.subtype'].search(
                    [('default', '=', True)], limit=1)
                mail_channel.message_post(
                    author_id=conversation.sender_id.partner_id.id,
                    body=_('%(name)s joined you (%(type)s, %(hc_name)s)',
                           name=conversation.sender_id.name,
                           type=hp_channel_id.type,
                           hc_name=hp_channel_id.display_name, ),
                    message_type='comment',
                    subtype_id=subtype.id, )
        return conversation

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'help_crunch':
            return super().send_message(text, **kwargs)
        try:
            body = {"chat": int(self.name),
                    "text": text,
                    "markdownText": text,
                    "agent": int(
                        self.chat_id.messenger_id.operator_id.helpcrunch_id),
                    "type": "message"}
            # pylint: disable=E8106
            token = self.chat_id.messenger_id.api_token
            response = requests.request(
                method='post', url='https://api.helpcrunch.com/v1/messages',
                json=body,
                headers={'Authorization': f'Bearer {token}'})
            if 200 <= response.status_code < 300:
                self.helpcrunch_out_message(text=text)
                self.helpcrunch_create_log(name='OUT', body=body)
        except Exception as e:
            _logger.debug(e)
        return None

    def send_file(self, files, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'help_crunch':
            return super().send_file(files, **kwargs)
        for file in files:
            if file and file.datas:
                url = self.get_help_attachment_url(attachment=file)
                try:
                    self.send_message(text=url)
                except Exception as e:
                    _logger.debug(e)
        return None

    def get_help_attachment_url(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        messenger_id = self.chat_id.messenger_id
        if messenger_id.is_helpcrunch_developer_mode \
                and messenger_id.helpcrunch_developer_url:
            burl = messenger_id.helpcrunch_developer_url.strip()
        token = attachment.generate_access_token()
        token = token[0] if token else ''
        url = '{}/web/content/ir.attachment/{}/datas?access_token={}'.format(
            burl, attachment.id, token)
        return url

    def helpcrunch_out_message(self, text=False):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].search([
            ('name', '=', 'HelpCrunch')], limit=1)
        self.env['kw.chatbot.message'].sudo().create({
            'conversation_id': self.id, 'is_bot_message': True,
            'sender_id': sender[0].id, 'text': text,
            'name': 'None', })

    def helpcrunch_create_log(self, name=False, body=False):
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

    # pylint: disable=R1710
    def helpcrunch_create_conversation(self, jsonrequest, chat_id, sender_id):
        if jsonrequest.get('eventData')['chat_id']:
            conversation_id = self.sudo().create(
                {'name': jsonrequest.get('eventData')['chat_id'],
                 'dialog_id': chat_id.dialog_id.id,
                 'sender_id': sender_id.id,
                 'chat_id': chat_id.id,
                 'last_activity_datetime': fields.Datetime.now()})
            return conversation_id

    def helpcrunch_message_conversation(self, jsonrequest):
        if jsonrequest.get('eventData')['chat_id']:
            conversation_id = self.sudo().search([
                ('name', '=', jsonrequest.get('eventData')['chat_id'])],
                limit=1)
            return conversation_id

    def upload_url_image(self, text):
        try:
            url = text.strip()
            if url and url.startswith("[") and url.endswith("]"):
                url = url.strip("[]").strip()
            # pylint: disable=E8106
            r = requests.get(url, allow_redirects=True)
            data = r.content
            mimetype = r.headers.get('content-type')
            data = base64.b64encode(data)
            data = data.decode('utf-8')
        except Exception as e:
            _logger.debug(e)
            return False
        if mimetype.split('/')[0] == 'image':
            filename = 'helpcrunch_image'
            attachment = self.env['ir.attachment'].sudo().create({
                'name': filename, 'datas': data,
                'mimetype': mimetype, 'res_model': 'mail.compose.message'})
            if attachment:
                attachment.write(
                    {'name': '{}-{}'.format(filename, attachment.id)})
                self.connect_live_chat(attachment=attachment)
                return attachment
        return False

    def helpcrunch_get_response(self, jsonrequest):
        text = jsonrequest['message']['text']
        self.ensure_one()
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if text in ['/start', '/end']:
                return None
            live_chat_mess_id = self.connect_live_chat(text=text)
            if live_chat_mess_id:
                self.write({'is_helpcrunch_send': True})
        if self.is_helpcrunch_send:
            return None
        return False

    def get_link_bot(self, jsonrequest):
        self.ensure_one()
        if jsonrequest.get('eventData')['telegramBotUsername']:
            self.write({
                'link_bot':
                    jsonrequest.get('eventData')['telegramBotUsername']})
        if jsonrequest.get('eventData')['instagramPageName']:
            self.write({
                'link_bot': jsonrequest.get('eventData')['instagramPageName']})
        if jsonrequest.get('eventData')['facebookPageLink']:
            self.write({
                'link_bot': jsonrequest.get('eventData')['facebookPageLink']})


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    helpcrunch_id = fields.Integer()

    raw_json = fields.Text()
