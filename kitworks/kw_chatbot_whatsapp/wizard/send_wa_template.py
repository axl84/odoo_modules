import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class SendWhatsappTemplateWizard(models.TransientModel):
    _name = 'send.wa.template.wizard'
    _description = 'Send Whatsapp Template Wizard'

    template_id = fields.Many2one(
        comodel_name='kw.chatbot.whatsapp.template')
    conversation_ids = fields.Many2many(
        comodel_name='kw.chatbot.conversation')

    def action_send(self):
        for conversation_id in self.conversation_ids.filtered(
                lambda x: x.chat_id.provider == 'whatsapp'):
            conversation_id.send_whatsapp_template(template=self.template_id)
