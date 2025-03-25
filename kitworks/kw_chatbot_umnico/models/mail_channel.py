import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Channel(models.Model):
    _inherit = 'discuss.channel'

    def _convert_visitor_to_lead(self, partner, key):
        lead = super(Channel, self)._convert_visitor_to_lead(partner, key)
        if lead.kw_conversation_id:
            chat = lead.kw_conversation_id.chat_id
            if chat.provider != 'umnico':
                return lead
            lead.write({
                'user_id':
                    chat.umnico_crm_user_id.id
                    if chat.umnico_crm_user_id else False,
                'type': chat.umnico_crm_type,
                'team_id':
                    chat.umnico_crm_team_id.id
                    if chat.umnico_crm_team_id else False, })
        return lead
