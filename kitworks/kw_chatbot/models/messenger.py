import logging

from odoo import models, fields, api, _
from odoo.addons.base.models import ir_module

_logger = logging.getLogger(__name__)


class Messenger(models.Model):
    _name = 'kw.chatbot.messenger'
    _description = 'Messenger'
    _order = 'module_state, state, sequence, name'

    name = fields.Char(
        required=True, string='Code', )
    color = fields.Integer(
        compute='_compute_color', )
    description = fields.Html()

    sequence = fields.Integer(
        default=10, help='Determine the display order')
    provider = fields.Selection(
        default='odoo_livechat', required=True, selection=[
            ('telegram', 'Telegram'),
            ('facebook', 'Facebook'),
            ('instagram', 'Instagram'),
            ('odoo_livechat', 'Odoo Live-chat'),
            ('help_crunch', 'HelpCrunch'),
            ('wepster', 'Wepster'),
            ('umnico', 'Umnico'),
            ('echat', 'E-Chat'),
            ('whatsapp', 'WhatsApp'),
            ('viber', 'Viber')], )
    company_id = fields.Many2one(
        comodel_name='res.company', required=True,
        default=lambda self: self.env.company.id, )
    state = fields.Selection(
        required=True, default='disabled', selection=[
            ('disabled', 'Disabled'), ('enabled', 'Enabled'),
            ('test', 'Test Mode')], )
    is_log_enabled = fields.Boolean(
        default=True, )
    module_name = fields.Char(
        required=True, )
    module_id = fields.Many2one(
        comodel_name='ir.module.module', string='Corresponding Module',
        compute='_compute_by_module_name', compute_sudo=True, )
    module_state = fields.Selection(
        selection=ir_module.STATES, string='Installation State',
        compute='_compute_by_module_name', store=True, compute_sudo=True, )
    image_128 = fields.Image(
        string='Image', max_width=128, max_height=128, )
    chatbot_chat_ids = fields.One2many(
        comodel_name='kw.chatbot.chat', inverse_name='messenger_id', )

    def create_chatbot_chat_button(self):
        name = f"{self.name if self.name else ''} Messenger"
        return {
            'name': _('Chatbot Chat'),
            'view_mode': 'form',
            'res_model': 'kw.chatbot.chat',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'domain': [('messenger_id', '=', self.id), ],
            'context': {
                'default_messenger_id': self.id,
                'search_messenger_id': self.id,
                'default_name': name,
                'search_name': name, }}

    @api.depends('state', 'module_state')
    def _compute_color(self):
        for obj in self:
            if not obj.module_id:
                obj.color = 8  # light green
            elif obj.module_id and not obj.module_state == 'installed':
                obj.color = 7  # cyan
            elif obj.module_id and obj.state == 'disabled':
                obj.color = 3  # yellow
            elif obj.module_id and obj.state == 'test':
                obj.color = 4  # blue
            elif obj.module_id and obj.state == 'enabled':
                obj.color = 7  # green

    def button_immediate_install(self):
        if self.module_id and self.module_state != 'installed':
            self.module_id.button_immediate_install()
            return {'type': 'ir.actions.client', 'tag': 'reload', }
        return None

    def _compute_by_module_name(self):
        for obj in self:
            m = self.env['ir.module.module'].search([
                ('name', '=', obj.module_name)], limit=1)
            obj.module_id = m or False
            obj.module_state = m.state if m else False

    def set_state_enabled(self):
        self.write({'state': 'enabled'})

    def open_purchase_url(self):
        return {'type': 'ir.actions.act_url', 'target': 'self',
                'url': 'https://kitworks.systems', }
