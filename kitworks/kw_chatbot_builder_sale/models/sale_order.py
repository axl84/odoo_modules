from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    kw_conversation_id = fields.Many2one(
        compute_sudo=True,
        compute='_compute_conversation',
        comodel_name='kw.chatbot.conversation', )

    def _compute_conversation(self):
        conversation_ids = self.env['kw.chatbot.conversation'].sudo()
        for obj in self:
            conversation_id = conversation_ids.search(
                [('partner_id', '=', obj.partner_id.id),
                 ('company_id', '=', self.env.company.id), ], limit=1)
            obj.write({
                'kw_conversation_id': conversation_id.id
                if conversation_id else False})

    def livechat_open_and_subscribe_button(self):
        if self.kw_conversation_id:
            self.kw_conversation_id.livechat_open_and_subscribe_button()
