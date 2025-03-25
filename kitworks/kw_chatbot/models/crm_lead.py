import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    kw_conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', )

    def livechat_open_and_subscribe_button(self):
        if self.kw_conversation_id:
            self.kw_conversation_id.livechat_open_and_subscribe_button()
