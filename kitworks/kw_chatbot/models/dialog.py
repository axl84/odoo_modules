import logging
import base64

from odoo import models, fields, api, modules, _

_logger = logging.getLogger(__name__)

"""
Диалог - это алгоритм, скрипт или последовательность вопросов и ответов,
который должен привести либо к получению пользователем нужной информации
или передачи нужной информации в систему
"""


class Dialog(models.Model):
    _name = 'kw.chatbot.dialog'
    _description = 'Dialog'

    name = fields.Char(
        required=True, )
    active = fields.Boolean(
        default=True, )
    is_messenger_specific = fields.Boolean()

    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger', )
    chatbot_chat_ids = fields.One2many(
        comodel_name='kw.chatbot.chat', inverse_name='dialog_id', )

    conversations_ids = fields.One2many(
        comodel_name='kw.chatbot.conversation', inverse_name='dialog_id', )
    sender_ids = fields.Many2many(
        comodel_name='kw.chatbot.sender', compute='_compute_senders')

    operator_ids = fields.Many2many(
        comodel_name='kw.chatbot.sender',
        compute='_compute_operator', )

    not_found_msg = fields.Text(
        default='press /start to talk', translate=True)
    connect_operator_msg = fields.Text(
        default='connected to chat. Please start messaging!', translate=True)
    msg_for_end_consultation = fields.Text(
        default='If you would like to end your consultation Press: /end',
        translate=True)
    moderation_msg = fields.Text(
        default='Please wait for approval you as consultant', translate=True)
    aprove_msg = fields.Text(
        default='You Aproved', )
    msg_after_not_found_operator = fields.Text(
        translate=True, default='Sorry, no operator available',
        string='Message after not found operator')
    reject_msg = fields.Text(
        default='You Reject', )
    end_consultation_msg = fields.Text(
        default='Сonsultation completed', translate=True)

    bots_type = fields.Selection(
        selection=[('is_consultant_bot', 'Consultant Bot'), ],
        tracking=True, default='is_consultant_bot', required=True, )

    is_partner = fields.Boolean(
        string="Is Create Partner", default=True)

    user_ids = fields.Many2many(
        'res.users', string='Operators')
    are_you_inside = fields.Boolean(
        string='Are you inside the matrix?',
        compute='_compute_are_you_inside', store=False, readonly=True)

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', )
    operator_in_odoo_only = fields.Boolean(
        default=True, )
    max_count_chats_for_operator = fields.Integer(
        default=1, string='Max number of parallel chats', )
    execute_sudo = fields.Boolean(default=True, )
    is_setup_config = fields.Boolean(default=False, )

    kw_chatbot_dialog_count = fields.Integer(
        compute='_compute_kw_chatbot_dialog_count',
        string='Number of Dialogs')

    @api.depends('name')
    def _compute_kw_chatbot_dialog_count(self):
        for dialog in self:
            dialog.kw_chatbot_dialog_count = len(dialog.search([]))

    # def send_message_to_conversations(self, message):
    #     conversations = self.mapped('conversations_ids')
    #     if not conversations:
    #         return
    #     for conversation in conversations:
    #         conversation.send_message(message)
    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        # get current company
        company = self.env.company
        if not res.company_id:
            res.company_id = company.id
        return res

    @api.depends('sender_ids')
    def _compute_operator(self):
        for obj in self:
            operator = self.env['kw.chatbot.sender']
            if obj.sender_ids:
                operator = obj.sender_ids.filtered(
                    lambda x: x.is_chatbot_consultant)
            obj.operator_ids = [(6, 0, operator.ids)]

    def create_chatbot_chat_button(self):
        return {
            'name': _('Chatbot Chat'),
            'view_mode': 'form',
            'res_model': 'kw.chatbot.chat',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'domain': [('dialog_id', '=', self.id), ],
            'context': {
                'default_dialog_id': self.id,
                'search_dialog_id': self.id, }}

    def _compute_are_you_inside(self):
        for channel in self:
            channel.are_you_inside = bool(
                self.env.uid in [u.id for u in channel.user_ids])

    def create_livechat_conversation(self, user_id, create_mail_channel=True):
        for count_chat in range(self.max_count_chats_for_operator):
            livechat_name = 'Operator - {} - {} - {}'.format(
                user_id.id, self.name, count_chat)
            livechat_sender = self.env['kw.chatbot.sender'].sudo().search([
                ('partner_id', '=', self.env.user.partner_id.id), ], limit=1)
            messenger = self.env['kw.chatbot.messenger'].sudo().search([
                ('provider', '=', 'odoo_livechat')], limit=1)
            user = self.env['res.users'].search([
                ('id', '=', user_id.id)], limit=1)
            if not livechat_sender:
                livechat_sender = self.env['kw.chatbot.sender'].sudo().create({
                    'messenger_id': messenger.id,
                    'name': user.name,
                    'partner_id': self.env.user.partner_id.id,
                })
            conversation = self.env['kw.chatbot.conversation'].sudo().search([
                ('sender_id', '=', livechat_sender.id),
                ('name', '=', livechat_name), ])
            chat_id = self.env['kw.chatbot.chat'].sudo().search([
                ('provider', '=', 'odoo_livechat')], limit=1)
            if not conversation:
                conversation = \
                    self.env['kw.chatbot.conversation'].sudo().create({
                        'name': livechat_name,
                        'dialog_id': self.id,
                        'chat_id': chat_id.id,
                        'sender_id': livechat_sender.id, })
            if create_mail_channel:
                mail_channel = self.env['discuss.channel'].search(
                    [("conversation_id", '=', conversation.id)],
                    limit=1)
                if not mail_channel:
                    mail_channel = self.env['discuss.channel'].create(
                        {'name': 'Chanel for {}'.format(user.name),
                         'conversation_id': conversation.id,
                         'channel_type': 'group'})
                conversation.write({'mail_channel_id': mail_channel.id})

    def action_setting(self):
        # return open form wizard
        return {
            'name': _('Setup Chat Bot Wizard'),
            'view_mode': 'form',
            'view_id': self.env.ref(
                'kw_chatbot.setup_chat_bot_wizard_wizard_menu').id,
            'res_model': 'setup.chat.bot.wizard',
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_join(self):
        self.ensure_one()
        self.create_livechat_conversation(
            user_id=self.env.user, create_mail_channel=False)
        self.env.user.is_chatbot_consultant = True
        for count_chat in range(self.max_count_chats_for_operator):
            _logger.info('count_chat: %s', count_chat)
            livechat_sender = self.env['kw.chatbot.sender'].sudo().search([
                ('partner_id', '=', self.env.user.partner_id.id), ], limit=1)
            if livechat_sender:
                livechat_sender.is_chatbot_consultant = True
                livechat_sender.aproved_consultant = True
                livechat_sender.is_ready_for_consult = True
        return self.write({'user_ids': [(4, self._uid)]})

    def action_quit(self):
        self.ensure_one()
        self.env.user.is_chatbot_consultant = False
        for count_chat in range(self.max_count_chats_for_operator):
            _logger.info('count_chat %s', count_chat)
            livechat_sender = self.env['kw.chatbot.sender'].sudo().search([
                ('partner_id', '=', self.env.user.partner_id.id)], limit=1)
            if livechat_sender:
                livechat_sender.is_chatbot_consultant = False
                livechat_sender.aproved_consultant = False
                livechat_sender.is_ready_for_consult = False
                # unlink all conversations for this sender
                livechat_sender.conversation_ids.filtered(
                    lambda x: x.dialog_id.id == self.id).unlink()
        return self.write({'user_ids': [(3, self._uid)]})

    @api.depends('conversations_ids')
    @api.onchange('conversations_ids')
    def _compute_senders(self):
        for obj in self:
            obj.sender_ids = [(5, 0, 0)]
            for con in obj.conversations_ids:
                obj.sender_ids = [(4, con.sender_id.id)]

    def _default_image(self):
        image_path = modules.get_module_resource(
            'kw_chatbot', 'static/src/dialog_logo',
            'is_consultant_bot.png')
        return base64.b64encode(open(image_path, 'rb').read())

    image_128 = fields.Image("Image", max_width=128, max_height=128,
                             default=_default_image)
