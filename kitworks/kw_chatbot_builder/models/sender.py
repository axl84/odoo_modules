import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    count_available_conversations = fields.Integer(
        compute='_compute_count_available_conversations', )
    connect_only_to_my_clients = fields.Boolean(
        default=False)
    user_saleperson_id = fields.Many2one(
        comodel_name='res.users', )

    def _compute_count_available_conversations(self):
        for sender in self:
            sender.count_available_conversations = 0
            for wired in sender.conversation_ids:
                if not wired.wired_conversation_id:
                    sender.count_available_conversations += 1
