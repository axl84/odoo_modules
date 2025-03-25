import logging

from odoo import models, fields, api
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class Channel(models.Model):
    _inherit = 'discuss.channel'

    is_bot_channel = fields.Boolean(
        compute='_compute_bot_channel', )
    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', )

    # def execute_command_leave(self, **kwargs):
    #     partner = self.env.user.partner_id
    #     self.write({'channel_partner_ids': [Command.unlink(partner.id)]})
    #     return super(Channel, self).execute_command_leave()

    # pylint: disable=R0912,R0915
    def execute_command_end(self, **kwargs):
        """
        Create a message as send /end in plain text
        """
        conversation_id = self.conversation_id
        sender_id = self.conversation_id.sender_id
        command_text = kwargs.get('body', '').rstrip()

        admin_conversation_id = conversation_id
        # Owner this '/end' command is always Admin
        if conversation_id.wired_conversation_id and conversation_id.wired_conversation_id.sender_id:
            sender_id = conversation_id.wired_conversation_id.sender_id
            admin_conversation_id = conversation_id.wired_conversation_id

        # set wired conversation - bcs it's from admin
        current_message = self.env['kw.chatbot.message'].sudo().create({
            'odoo_livechat_id': sender_id.id,
            'conversation_id': admin_conversation_id.id,
            'sender_id': sender_id.id,
            'text': command_text,
            'name': command_text, })

        # for run next step if dialog ended by operator from odoo UI
        if conversation_id.chat_id.provider == 'telegram' \
                and conversation_id.last_step_id \
                and conversation_id.last_step_id.go_to_step_id:
            bot = conversation_id.chat_id.telegram_get_telegram_bot()
            conversation_id.telegram_next_step(conversation_id.last_step_id,
                                               bot, current_message)

        # for run next step viber if dialog ended by operator from odoo UI
        if conversation_id.chat_id.provider == 'viber' \
                and conversation_id.last_step_id \
                and conversation_id.last_step_id.go_to_step_id:
            bot = conversation_id.chat_id.viber_get_viber_bot()
            conversation_id.viber_next_step(
                    step=conversation_id.last_step_id, bot=bot, message='',
                    next_step=conversation_id.last_step_id.go_to_step_id)

        return current_message

    def _convert_visitor_to_lead(self, partner, key):
        lead = super(Channel, self)._convert_visitor_to_lead(partner, key)
        description = ''.join(
            '{}: {}<br/>'.format(
                message.author_id.name or self.anonymous_name,
                html2plaintext(message.body)) if html2plaintext(
                message.body) else ''
            for message in self.message_ids.sorted('id'))
        conversation_id = self.env['kw.chatbot.conversation']
        tag = self.env['crm.tag']
        partner_id = self.env['res.partner']
        if self.conversation_id:
            conversation_id = self.conversation_id.id
            partner_id = self.conversation_id.sender_id.partner_id \
                if self.conversation_id.sender_id.partner_id else False
            tag = self.env['crm.tag'].search([
                ('name', '=', self.conversation_id.chat_id.name), ])
            if not tag:
                tag = self.env['crm.tag'].create({
                    'name': self.conversation_id.chat_id.name, })

        lead.write({
            'tag_ids': [(4, tag.id)] if tag else False,
            'description': description,
            'partner_id': partner_id.id if partner_id else False,
            'company_id': partner_id.company_id.id if partner_id else False,
            'kw_conversation_id': conversation_id, })

        return lead

    def _compute_bot_channel(self):
        # _logger.info('_compute_bot_channel')
        for channel in self:
            res_partner_bot = channel.channel_partner_ids.filtered(
                lambda x: x.is_livechat_bot)
            if res_partner_bot and len(channel.channel_partner_ids.ids) == 2:
                channel.is_bot_channel = True
            else:
                channel.is_bot_channel = False

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        # _logger.info('message_post')
        # _logger.info(kwargs)
        button = kwargs.get('button') if kwargs.get('button') else False
        # flake8: noqa
        kw_parent_id = kwargs.get('kw_parent_id') if kwargs.get('kw_parent_id') else False
        kw_reply = kwargs.get('id_reply') if kwargs.get('id_reply') else False
        if kw_parent_id:
            parent_id = self.env['mail.message'].sudo().search([
                ('kw_message_id', '=', kw_reply)])
            kw_message_id = self.env['kw.chatbot.message'].sudo().search([
                ('name', '=', kw_reply),
                ('telegram_id', '=', int(kw_reply))])
            if not parent_id:
                parent_id = self.env['mail.message'].sudo().search([
                    ('kw_message_id', '=', kw_message_id[0].id + 1)])
            for msg in parent_id:
                for kw_msg in kw_message_id:
                    if str(msg.description) == kw_msg.text:
                        kwargs['parent_id'] = msg.id
                        break
        else:
            parent_id = False
        res = super(Channel, self.with_context(mail_create_nosubscribe=True)
                    ).message_post(message_type=message_type,
                                   kw_livechat_bot_button_html=button,
                                   **kwargs)
        return res

    @api.model
    def check_mail_channel(self, **kwargs):
        # _logger.info('check_mail_channel')
        # _logger.info(kwargs)
        if kwargs:
            channel = self.env['discuss.channel'].sudo().search([
                ('id', '=', kwargs.get('index'))])
            if channel.is_bot_channel:
                res_partner_bot = channel.channel_partner_ids.filtered(
                    lambda x: x.is_livechat_bot)
                chat = self.env['kw.chatbot.chat'].sudo().search([
                    ('odoo_livechat_res_partner_id', '=', res_partner_bot.id)
                ], limit=1)
                if not chat:
                    # _logger.info('Wrong chat connection')
                    return 'Invalid url'
                chat.odoo_livechat_process_call(channel, kwargs)
        return None


class ChannelPartner(models.Model):
    _inherit = 'discuss.channel.member'

    is_bot_operator = fields.Boolean(
        default=False, )
