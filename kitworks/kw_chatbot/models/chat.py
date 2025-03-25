import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

"""
Чат - это отдельная именованная сущность в мессенджере, представление
диалога в конктретном мессерджере
"""


@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


class Chat(models.Model):
    _name = 'kw.chatbot.chat'
    _description = 'Chat'

    name = fields.Char(
        required=True, default='Messenger')
    active = fields.Boolean(
        default=True, )
    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger', required=True, )
    messenger_ids = fields.Many2many(
        comodel_name='kw.chatbot.messenger',
        compute_sudo=True, compute='_compute_messengers', )
    dialog_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog', required=False, )
    dialog_ids = fields.Many2many(
        comodel_name='kw.chatbot.dialog', )
    is_developer_mode = fields.Boolean()

    provider = fields.Selection(
        related='messenger_id.provider', )

    log_id = fields.Many2one(
        comodel_name='kw.chatbot.log', )

    odoo_livechat_res_partner_id = fields.Many2one(
        comodel_name='res.partner', string='Livechat Bot',
        domain=[('is_livechat_bot', '=', True), ('chat_ids', '=', False)], )

    is_communication_chat = fields.Boolean()

    is_consultant_chat = fields.Boolean()

    is_send_operator_name = fields.Boolean(
        default=False, )
    is_automatic_send_greet = fields.Boolean(
        default=True, )
    is_send_and_consultation = fields.Boolean(
        default=True, help='How and consultation')

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        related='dialog_id.company_id')
    default_contact_lang = fields.Selection(selection=_lang_get)

    def search_dialog(self):
        dialog_ids = self.dialog_ids
        dialog_ids = dialog_ids.search(
            [('bots_type', '=', 'is_consultant_bot'),
             ('company_id', '=', self.env.company.id)])
        if dialog_ids:
            return dialog_ids.ids
        return dialog_ids

    @api.depends('messenger_id', 'dialog_id')
    def _compute_messengers(self):
        for obj in self:
            dialog_ids = obj.search_dialog()
            messenger_ids = \
                self.env['kw.chatbot.messenger'].sudo().search(
                    [('state', 'in', ['enabled', 'test']),
                     ('company_id', '=', self.env.company.id), ]).mapped('id')
            obj.sudo().write({
                'dialog_ids': [(6, 0, dialog_ids)],
                'messenger_ids': [(6, 0, messenger_ids)], })
            if not obj.dialog_id:
                dialog_id = self.env['kw.chatbot.dialog'].sudo().search([
                    ('bots_type', '=', 'is_consultant_bot'),
                    ('company_id', '=', self.env.company.id)], limit=1)
                obj.write({
                    'dialog_id': dialog_id.id})

    def odoo_livechat_message_handler(self, channel, message):
        self.ensure_one()
        # _logger.info('odoo_livechat_process_message')
        visitor = channel.channel_partner_ids.filtered(
            lambda x: not x.is_livechat_bot)
        if not visitor:
            visitor = 'Visitor {}'.format(channel.id)
        else:
            visitor = visitor.id
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id, sender=visitor)
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        conversation.odoo_livechat_create_log(name='IN', body=message)
        conversation.mail_channel_id = channel.id
        conversation.chatbot_message_id = \
            self.env['kw.chatbot.message'].sudo().create({
                'odoo_livechat_id': sender.id,
                'conversation_id': conversation.id,
                'sender_id': sender.id, 'text': message.get('body'),
                'name': message.get('body'), })
        conversation.last_activity_datetime = fields.Datetime.now()
        conversation.odoo_livechat_get_response(channel, message)

    def odoo_livechat_callback_handler(self, channel, message):
        self.ensure_one()
        # _logger.info('odoo_livechat_callback_handler')
        visitor = channel.channel_partner_ids.filtered(
            lambda x: not x.is_livechat_bot)
        if not visitor:
            visitor = 'Visitor {}'.format(channel.id)
        else:
            visitor = visitor.id
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id, sender=visitor)
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        conversation.odoo_livechat_create_log(name='IN', body=message)
        conversation.mail_channel_id = channel.id
        conversation.chatbot_message_id = \
            self.env['kw.chatbot.message'].sudo().create({
                'odoo_livechat_id': sender.id,
                'is_call_back_message': True,
                'conversation_id': conversation.id,
                'sender_id': sender.id,
                'text': message.get('body'),
                'name': message.get('body'), })
        conversation.last_activity_datetime = fields.Datetime.now()
        conversation.odoo_livechat_get_response(channel, message)

    def odoo_livechat_process_call(self, channel, message):
        self.ensure_one()
        # _logger.info('odoo_livechat_process_call')
        if channel and message:
            if message.get('call_data'):
                self.odoo_livechat_message_handler(
                    channel, message.get('call_data'))
            elif message.get('callback_data'):
                self.odoo_livechat_callback_handler(
                    channel, message.get('callback_data'))
