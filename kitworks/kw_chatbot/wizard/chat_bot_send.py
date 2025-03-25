import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SendChat(models.TransientModel):
    _name = 'chat.bot.send'
    _inherit = ['kw.chatbot.message']
    _description = 'ChatBotSend'

    chat_id = fields.Many2one(
        comodel_name='kw.chatbot.chat', related='conversation_id.chat_id')
    name = fields.Char(default='None')
    sender_id = fields.Many2one(
        comodel_name='kw.chatbot.sender', )
    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', required=True)
    conversation_ids = fields.Many2many(
        comodel_name='kw.chatbot.conversation',
        compute='_compute_conversation', )

    def action_send(self):
        self.conversation_id.send_message(self.text)

    @api.depends('sender_id')
    def _compute_conversation(self):
        for obj in self:
            obj.conversation_ids = False
            if obj.sender_id:
                obj.conversation_ids = \
                    [(6, 0, self.env['kw.chatbot.conversation'].sudo().search(
                        [('sender_id', '=', obj.sender_id.id),
                         ('company_id', '=', self.env.company.id)
                         ]).mapped('id'))]

    @api.onchange('sender_id')
    def default_conversation(self):
        for obj in self:
            if len(obj.conversation_ids) == 1:
                obj.conversation_id = obj.sender_id.conversation_ids[0].id
