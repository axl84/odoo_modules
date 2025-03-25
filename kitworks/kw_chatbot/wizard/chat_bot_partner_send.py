import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SendChat(models.TransientModel):
    _name = 'chat.bot.partner.send'
    _description = 'chat.bot.partner.send'
    _inherit = ['kw.chatbot.message', ]

    chat_id = fields.Many2one(
        comodel_name='kw.chatbot.chat', related='conversation_id.chat_id', )
    name = fields.Char()

    partner_id = fields.Many2one(
        comodel_name='res.partner', )
    sender_id = fields.Many2one(
        comodel_name='kw.chatbot.sender', required=True, )
    sender_ids = fields.Many2many(
        comodel_name='kw.chatbot.sender', compute='_compute_senders', )
    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', required=True, )
    conversation_ids = fields.Many2many(
        comodel_name='kw.chatbot.conversation',
        compute='_compute_conversation', )

    def action_send(self):
        self.conversation_id.send_message(self.text)

    @api.depends('partner_id')
    def _compute_senders(self):
        for obj in self:
            obj.sender_ids = \
                [(6, 0, self.env['kw.chatbot.sender'].sudo().
                  search([('partner_id', '=', obj.partner_id.id)]).
                  mapped('id'))]

    @api.depends('sender_id')
    def _compute_conversation(self):
        for obj in self:
            obj.conversation_ids = False
            if obj.sender_id:
                obj.conversation_ids = \
                    [(6, 0, self.env['kw.chatbot.conversation'].sudo().search(
                        [('sender_id', '=', obj.sender_id.id)]).mapped('id'))]


class SendChatMass(models.TransientModel):
    _name = 'chat.bot.partner.send.mass'
    _description = 'chat.bot.partner.send.mass'
    _inherit = ['kw.chatbot.message', ]

    kw_partner_ids = fields.Many2many(
        comodel_name='res.partner', )
    sender_ids = fields.Many2many(
        comodel_name='kw.chatbot.sender', )
    chat_id = fields.Many2one(
        comodel_name='kw.chatbot.chat', )
    name = fields.Char()

    text = fields.Text()

    conversation_ids = fields.Many2many(
        comodel_name='kw.chatbot.conversation', )

    @api.onchange('chat_id')
    def _change_chat_id(self):
        for obj in self:
            if obj.chat_id:
                obj.conversation_ids = \
                    [(6, 0, self.env['kw.chatbot.conversation'].sudo().search(
                        [('chat_id', '=', obj.chat_id.id),
                         ('partner_id', 'in', obj.kw_partner_ids.ids)]).
                      mapped('id'))]

    def action_send(self):
        for obj in self.conversation_ids:
            obj.send_message(self.text)
