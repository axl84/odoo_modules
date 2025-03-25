import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

"""
Чат - это отдельная именованная сущность в мессенджере, представление
диалога в конктретном мессерджере
"""


class Sender(models.Model):
    _name = 'kw.chatbot.sender'
    _description = 'Sender'

    name = fields.Char(
        required=True, )
    active = fields.Boolean(
        default=True, )
    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger', )
    partner_id = fields.Many2one(
        comodel_name='res.partner', )
    provider = fields.Selection(
        related='messenger_id.provider')
    chatbot_message_ids = fields.One2many(
        comodel_name='kw.chatbot.message', inverse_name='sender_id', )
    conversation_ids = fields.One2many(
        comodel_name='kw.chatbot.conversation', inverse_name='sender_id', )

    odoo_livechat_id = fields.Char()

    partner_phone = fields.Char()

    partner_email = fields.Char()

    partner_name = fields.Char()

    sequence = fields.Integer(
        default=10, readonly=False, )

    user_id = fields.Many2one(
        comodel_name='res.users', compute='_compute_user_id', )
    is_ready_for_consult = fields.Boolean(
        default=False, readonly=True, )
    aproved_consultant = fields.Boolean(
        default=False, readonly=True, )
    is_chatbot_consultant = fields.Boolean(
        default=False, readonly=True, )

    @api.onchange('partner_id.name')
    def _compute_name(self):
        for obj in self:
            if obj.partner_id:
                obj.name = obj.partner_id.name

    def _compute_user_id(self):
        for obj in self:
            obj.user_id = False
            if obj.partner_id:
                # get user by partner
                user = self.env['res.users'].search([
                    ('partner_id', '=', obj.partner_id.id)], limit=1)
                if user:
                    obj.user_id = user.id

    def aprove_sender(self):
        for obj in self:
            obj.write({
                'aproved_consultant': True,
                'is_ready_for_consult': True,
                'is_chatbot_consultant': True, })
            obj.notification_operators(
                message=f'Operator {obj.name} Aproved')
            return {'type': 'ir.actions.client', 'tag': 'reload', }

    def reject_sender(self):
        for obj in self:
            obj.write({
                'aproved_consultant': False,
                'is_ready_for_consult': False,
                'is_chatbot_consultant': False, })
            obj.notification_operators(
                message=f'Operator {obj.name} Rejected')
            return {'type': 'ir.actions.client', 'tag': 'reload', }

    @api.model
    def get_or_create(self, messenger, **kwargs):

        def check_context(context):
            try:
                index = int(context)
            except Exception as e:
                _logger.debug(e)
                index = False
            return index

        if messenger.provider != 'odoo_livechat':
            _logger.debug(messenger, kwargs)
        sender_id = kwargs.get('sender')
        index = kwargs.get('sender')
        if not sender_id:
            raise ValueError('Cant process message: "sender" not provided')
        if check_context(sender_id):
            sender = self.env['res.partner'].search([
                ('id', '=', sender_id)], limit=1)
            sender_id = sender.name
            index = sender.id
        odoo_livechat_sender = self.sudo().search([
            ('odoo_livechat_id', '=', index)], limit=1)
        if not odoo_livechat_sender:
            odoo_livechat_sender = self.sudo().create({
                'messenger_id': messenger.id,
                'name': sender_id,
                'odoo_livechat_id': index, })
        return odoo_livechat_sender

    @api.constrains('aproved_consultant')
    def aproved_sender_message(self):
        for obj in self:
            senders = self.env['kw.chatbot.conversation'].search([
                ('sender_id', '=', obj.id),
                ('dialog_id.bots_type', '=', 'is_consultant_bot')])
            for sender in senders:
                if sender.dialog_id.operator_in_odoo_only:
                    continue
                if obj.aproved_consultant:
                    sender.send_message(text=sender.dialog_id.aprove_msg)
                else:
                    sender.send_message(text=sender.dialog_id.reject_msg)

    def notification_operators(self, message=False):
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Notification'),
                'message': message,
                'sticky': False,
            }
        }
        return notification

    def archive_of_sender_dialogs(self):
        """
        Archive of current sender dialogs
        """
        for conversation in self.conversation_ids:
            conversation.action_archive()

    def unlink(self):
        """
        Deleting the sender and archiving all his dialogs
        """
        self.archive_of_sender_dialogs()

        return super(Sender, self).unlink()

    def action_archive(self):
        """
        Archive the sender and archiving all his dialogs
        """
        self.archive_of_sender_dialogs()

        return super(Sender, self).action_archive()
