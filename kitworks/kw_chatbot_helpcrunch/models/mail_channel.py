import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Channel(models.Model):
    _inherit = 'discuss.channel'

    def _convert_visitor_to_lead(self, partner, key):
        lead = super(Channel, self)._convert_visitor_to_lead(partner, key)
        if lead.kw_conversation_id:
            con_id = lead.kw_conversation_id
            chat = con_id.chat_id
            hc_channel = con_id.sender_id.help_crunch_channel_id
            hc_channel_name = 'HelpCrunch/{} ({})'.format(
                hc_channel.type, hc_channel.display_name)
            source_id = self.env['utm.source'].search([
                ('name', '=', hc_channel_name)])
            if not source_id:
                source_id = self.env['utm.source'].create({
                    'name': hc_channel_name})
            if chat.provider != 'help_crunch':
                return lead
            lead.write({
                'source_id': source_id.id,
                'user_id':
                    chat.helpcrunch_crm_user_id.id
                    if chat.helpcrunch_crm_user_id else False,
                'type': chat.helpcrunch_crm_type,
                'team_id':
                    chat.helpcrunch_crm_team_id.id
                    if chat.helpcrunch_crm_team_id else False, })
        return lead
