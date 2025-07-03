"""
This model was created to save different categories of conversation
"""

from odoo import models, fields


class ConversationCategory(models.Model):
    _name = 'kw.chatbot.conversation.category'
    _description = 'Conversation Category'

    name = fields.Char()
