import logging
import base64
from urllib import request as urllib_request
import magic

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    umnico_crm_user_id = fields.Many2one(
        comodel_name='res.users', string='Salesperson')
    umnico_crm_team_id = fields.Many2one(
        comodel_name='crm.team', string='Sales Team')
    umnico_crm_type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')],
        default='opportunity', string='Type')

    def load_image_from_url(self, url, headers=False, mime_type=False):
        headers = headers or {}
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'Wget/1.11.4'
            # headers['User-Agent'] = \
            #     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) ' \
            #     'AppleWebKit/537.36 (KHTML, like Gecko) ' \
            #     'Chrome/50.0.2661.102 Safari/537.36'
        req = urllib_request.Request(url.strip(), None, headers)
        # pylint: disable=E8106
        try:
            res = urllib_request.urlopen(req)
        except urllib_request.HTTPError as e:
            _logger.error('HTTPError: %s', e)
            return False
        if mime_type:
            return magic.from_buffer(res.read(), mime=True)
        return res.read()

    # pylint: disable=R1710
    def umnico_create_chat(self, dialog_id=None):
        messenger_id = self.env['kw.chatbot.messenger'].sudo().search(
            [('name', '=', 'Umnico')], limit=1)
        chat_id = self.search([
            ('name', '=', 'Umnico'),
            ('messenger_id', '=', messenger_id.id)], limit=1)
        if not chat_id:
            if not dialog_id:
                dialog_id = self.env['kw.chatbot.dialog'].sudo().search([
                    ('bots_type', '=', 'is_consultant_bot')], limit=1)
            chat_id = self.create({
                'name': 'Umnico',
                'dialog_id': dialog_id.id,
                'messenger_id': messenger_id.id})
        return chat_id

    def umnico_process_message(self, message, log):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id, sender=message)
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        if sender.is_person:
            conversation.is_personal = True
        log.sudo().write({
            'sender_id': sender.id, 'conversation_id': conversation.id, })
        umnico_message = message.get('message')
        if umnico_message:
            text = umnico_message['message'].get('text')

            # decode id
            if isinstance(umnico_message.get('messageId'), str):
                umnico_id = 0
                for i in range(4, len(umnico_message.get('messageId')), 4):
                    a = int(umnico_message.get('messageId')[i - 4:i], 16)
                    umnico_id += a
            else:
                umnico_id = umnico_message.get('messageId')
            if text:
                self.env['kw.chatbot.message'].sudo().create({
                    'umnico_id': umnico_id,
                    'conversation_id': conversation.id,
                    'sender_id': sender.id,
                    'text': text if text else 'Attachments',
                    'name': text if text else 'Attachments', })
                conversation.last_activity_datetime = fields.Datetime.now()
                conversation.umnico_get_response(umnico_message['message'])
            if umnico_message['message'].get('attachments'):
                for attachment in umnico_message['message'].get('attachments'):
                    url = attachment['url'].replace(' ', '%20')
                    data = self.load_image_from_url(url)
                    if not data:
                        continue
                    mime_type = self.load_image_from_url(url, mime_type=True)
                    message_data = {
                        'umnico_id': umnico_id,
                        'conversation_id': conversation.id,
                        'sender_id': sender.id, }
                    data = base64.b64encode(data)
                    data = data.decode('utf-8')

                    if attachment['type'] == 'photo':
                        attachment = self.env['ir.attachment'].sudo().create({
                            # flake8: noqa: E501
                            'name': attachment['text'] if attachment.get('text') else 'Photo',
                            'datas': data,
                            # flake8: noqa: E501
                            'mimetype': mime_type if mime_type else 'image/jpeg', })

                        message_data.update(
                            {'attachment_ids': [(4, attachment.id)]})

                    if attachment['type'] == 'doc':
                        attachment = self.env['ir.attachment'].sudo().create(
                            {
                                'name': attachment['text'],
                                'datas': data,
                                # flake8: noqa: E501
                                'mimetype': mime_type if mime_type else 'application/pdf',
                            })
                        message_data.update(
                            {'attachment_ids': [(4, attachment.id)]})
                    message_data['name'] = 'Attachments'
                    self.env['kw.chatbot.message'].sudo().create(message_data)
                    conversation.last_activity_datetime = fields.Datetime.now()

    def umnico_process_call(self, jsonrequest, log):
        self.ensure_one()
        # _logger.info('facebook_process_call')
        if jsonrequest.get('type') == 'message.incoming':
            self.umnico_process_message(
                message=jsonrequest, log=log)
