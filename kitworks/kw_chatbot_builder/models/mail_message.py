import logging
import re

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Channel(models.Model):
    _inherit = 'mail.message'

    kw_livechat_bot_button_ids = fields.Many2many(
        comodel_name='kw.chatbot.step.livechat.button')
    kw_livechat_bot_button_html = fields.Char()
    kw_audio_url = fields.Char(compute='_compute_kw_audio_url')

    def get_attachment_url(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        token = attachment.generate_access_token()
        token = token[0] if token else ''
        url = '{}/web/content/ir.attachment/{}/datas?access_token={}'.format(
            burl, attachment.id, token)
        return url

    def _compute_kw_audio_url(self):
        for record in self:
            record.kw_audio_url = record.attachment_ids.filtered(
                lambda a: a.mimetype == 'audio/ogg').url

    def message_format(self, format_reply=True, msg_vals=None):
        res = super(Channel, self).message_format(
            format_reply=format_reply, msg_vals=msg_vals)
        # _logger.info('message_format')
        for msg in res:
            msg['button'] = str(self.get_html_button(msg['id']))
        # if we have a audio attachment, we need to add the player
        for msg in res:
            if msg.get('attachment_ids'):
                for attachment in msg['attachment_ids']:
                    if attachment['mimetype'] in \
                            ['audio/ogg', 'audio/mpeg', 'audio/wav']:
                        attachment['kw_audio_url'] = self.get_audio_player(
                            attachment)
                        msg['body'] = '%s%s' % (
                            msg['body'],
                            msg['attachment_ids'][0].get('kw_audio_url'))
                        msg['attachment_ids'] = []
                    elif attachment['mimetype'] in \
                            ['video/mp4', 'video/ogg', 'video/webm']:
                        attachment['kw_audio_url'] = self.get_video_player(
                            attachment)
                        msg['body'] = '%s%s' % (
                            msg['body'],
                            msg['attachment_ids'][0].get('kw_audio_url'))
                        msg['attachment_ids'] = []
        return res

    def get_video_player(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # get attachment by id
        attachment = self.env['ir.attachment'].browse(attachment['id'])
        token = attachment.generate_access_token()
        token = token[0] if token else ''
        url = '{}/web/content/ir.attachment/{}/datas?access_token={}'.format(
            burl, attachment['id'], token)
        return f"""<video width="320" height="240" controls>
            <source src="{url}" type="video/mp4">
            Your browser does not support the video tag.
        </video>"""

    def get_audio_player(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # get attachment by id
        attachment = self.env['ir.attachment'].browse(attachment['id'])
        token = attachment.generate_access_token()
        token = token[0] if token else ''
        url = '{}/web/content/ir.attachment/{}/datas?access_token={}'.format(
            burl, attachment['id'], token)
        return f"""<audio controls>
            <source src="{url}" type="audio/ogg">
            Your browser does not support the audio element.
        </audio>"""

    def get_html_button(self, index):
        # _logger.info('get_html_button')
        message_id = self.env['mail.message'].search([('id', '=', index)])
        return message_id.kw_livechat_bot_button_html \
            if message_id.kw_livechat_bot_button_html else '<div/>'

    @api.model
    def create(self, vals_list):
        obj = super().create(vals_list)
        text = re.compile('<.*?>')
        message = re.sub(text, '', obj.body)
        if obj.model == 'discuss.channel':
            mail_channel = self.env[obj.model].browse(obj.res_id)
            conversation_id = mail_channel.conversation_id
            conversation_id.is_closed = False
            conversation_id = conversation_id.wired_conversation_id
            conversation_id.is_closed = False
            if conversation_id and conversation_id.chat_id \
                    and conversation_id.chat_id.provider == 'odoo_livechat':
                sender_id = conversation_id.sender_id
                if conversation_id.sender_id.partner_id.id != obj.author_id.id:
                    sender_id = conversation_id.wired_conversation_id.sender_id
                conversation_id.chatbot_message_id = \
                    self.env['kw.chatbot.message'].sudo().create({
                        'odoo_livechat_id': conversation_id.sender_id.id,
                        'is_call_back_message': True,
                        'conversation_id': conversation_id.id,
                        'sender_id': sender_id.id,
                        'text': message,
                        'attachment_ids': obj.attachment_ids
                        if obj.attachment_ids else False,
                        'name': message,
                        'kw_parent_id': obj.kw_message_id[0].id
                        if obj.kw_message_id else False, })
                obj.kw_message_id |= conversation_id.chatbot_message_id
                if conversation_id.sender_id.partner_id.id == obj.author_id.id:
                    self.env['kw.chatbot.message'].sudo().create({
                        'odoo_livechat_id':
                            conversation_id.sender_id.id,
                        'is_double_message': True,
                        'conversation_id':
                            conversation_id.wired_conversation_id.id,
                        'sender_id':
                            conversation_id.sender_id.id,
                        'text': message,
                        'attachment_ids': obj.attachment_ids
                        if obj.attachment_ids else False,
                        'name': conversation_id.chatbot_message_id.name
                        if conversation_id.chatbot_message_id else message, })
                conversation_id.last_activity_datetime = fields.Datetime.now()

        return obj


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_message_create_valid_field_names(self):
        result = super()._get_message_create_valid_field_names()
        return result.union({'kw_livechat_bot_button_html'})

    def _get_notify_valid_parameters(self):
        result = super()._get_notify_valid_parameters()
        return result.union({'button'})
