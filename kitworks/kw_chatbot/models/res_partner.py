import logging
from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    chat_ids = fields.One2many(
        comodel_name='kw.chatbot.chat',
        inverse_name='odoo_livechat_res_partner_id', )
    is_livechat_bot = fields.Boolean(
        default=False, )
    kw_is_consultant = fields.Boolean(
        compute='_compute_kw_is_consultant',
        string="Is Consult", )
    kw_is_available_consultant = fields.Boolean(
        string="Available for Consult", default=False)

    sender_ids = fields.One2many(
        comodel_name='kw.chatbot.sender', inverse_name='partner_id', )

    conversation_ids = fields.Many2many(
        compute='_compute_conversation',
        comodel_name='kw.chatbot.conversation', compute_sudo=True)

    # @api.onchange('name')
    # def onchange_name(self):
    #     if self.sender_ids:
    #         for sender in self.sender_ids:
    #             # sender.name = self.name
    #             self.sender_ids = [(1, sender.id, {'name': self.name})]

    def _compute_conversation(self):
        conversation_ids = self.env['kw.chatbot.conversation'].sudo()
        for obj in self:
            conversation_ids = conversation_ids.search(
                [('partner_id', '=', obj.id),
                 ('company_id', '=', self.env.company.id), ])
            obj.write({'conversation_ids': [(6, 0, conversation_ids.ids)]})
            if obj.conversation_ids:
                for conversation in obj.conversation_ids:
                    tag = self.env['res.partner.category'].search([
                        ('name', '=', conversation.chat_id.name), ])
                    if not tag:
                        self.env['res.partner.category'].create({
                            'name': conversation.chat_id.name,
                            'partner_ids': obj.ids})
                    else:
                        tag.write({'partner_ids': [(4, obj.id)]})

    def conversation_action_button(self):
        return {
            'name': _('Chatbot Conversation'),
            'view_mode': 'tree,form',
            'res_model': 'kw.chatbot.conversation',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_partner_id': self.id}}

    def _compute_im_status(self):
        res = super(ResPartner, self)._compute_im_status()
        for partner in self:
            if partner.is_livechat_bot:
                partner.im_status = 'online'
        return res

    def _compute_kw_is_consultant(self):
        for partner in self:
            user_id = self.env['res.users'].search([
                ('partner_id', '=', partner.id)], limit=1)
            if user_id.is_chatbot_consultant:
                partner.kw_is_consultant = True
            else:
                partner.kw_is_consultant = False
