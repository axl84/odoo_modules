import logging
import re

from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class Channel(models.Model):
    _inherit = 'mail.message'

    kw_message_id = fields.Many2many(
        comodel_name='kw.chatbot.message', )

    # pylint: disable=R1702
    @api.model
    def create(self, vals_list):
        obj = super().create(vals_list)
        text = re.compile('<.*?>')
        message = re.sub(text, '', obj.body)
        if obj.parent_id:
            if obj.parent_id.kw_message_id:
                # flake8: noqa
                obj.kw_message_id = obj.parent_id.kw_message_id[len(obj.parent_id.kw_message_id) - 1]
        if obj.model == 'discuss.channel':
            mail_channel = self.env[obj.model].browse(obj.res_id)
            conversation_id = mail_channel.conversation_id
            if conversation_id and conversation_id.chat_id \
                    and conversation_id.chat_id.provider == 'odoo_livechat':
                conversation_id.chatbot_message_id = \
                    self.env['kw.chatbot.message'].sudo().create({
                        'odoo_livechat_id': conversation_id.sender_id.id,
                        'is_call_back_message': True,
                        'conversation_id': conversation_id.id,
                        'sender_id': conversation_id.sender_id.id,
                        'text': message,
                        'name': message, })
                conversation_id.last_activity_datetime = fields.Datetime.now()
        if obj.message_type == 'comment' and obj.author_id \
                and obj.model == 'discuss.channel':
            operator = self.env['res.users'].search([
                ('partner_id', '=', obj.author_id.id)], limit=1)
            mail_channel = self.env['discuss.channel'].search(
                [("id", '=', obj.res_id)], limit=1)
            if mail_channel.conversation_id \
                    and operator.is_chatbot_consultant \
                    and mail_channel.conversation_id.is_consult_with_odoo:
                dialog_id = mail_channel.conversation_id.dialog_id
                chat_id = dialog_id.chatbot_chat_ids.filtered(
                    lambda x: x.id == mail_channel.conversation_id.chat_id.id)
                if mail_channel.conversation_id and chat_id \
                        and dialog_id.bots_type == 'is_consultant_bot':
                    text = re.compile('<.*?>')
                    message = re.sub(text, '', obj.body)
                    if dialog_id.is_partner:
                        msg = message
                        chat = mail_channel.conversation_id.chat_id
                        if message:
                            wired_conv_chat = mail_channel.conversation_id.wired_conversation_id.chat_id
                            is_chat_name = wired_conv_chat.is_send_operator_name
                            if chat.is_send_operator_name or is_chat_name:
                                msg = f'{operator.name}: {message}'
                            mail_channel.conversation_id.send_message(text=msg)
                        if obj.attachment_ids:
                            mail_channel.conversation_id.send_file(
                                files=obj.attachment_ids)
        return obj
