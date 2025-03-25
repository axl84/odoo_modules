import logging

from odoo import api, fields, models
from odoo.addons.base.models import ir_module

_logger = logging.getLogger(__name__)


class SmsProvider(models.Model):
    _name = 'kw.sms.provider'
    _description = 'SMS provider'
    _order = 'module_state, state, sequence, name'

    name = fields.Char(
        required=True, )
    color = fields.Integer(
        compute='_compute_color', )
    description = fields.Html()

    sequence = fields.Integer(
        default=10, help='Determine the display order')
    provider = fields.Selection(
        default='sandbox', required=True, selection=[
            ('sandbox', 'SandBox (logging only)'),
            ('turbosms', 'TurboSMS'), ('alphasms', 'АльфаSMS'),
            ('letsads', 'LetsAds.com'), ], )
    company_id = fields.Many2one(
        comodel_name='res.company', required=True,
        default=lambda self: self.env.company.id, )
    state = fields.Selection(
        required=True, default='disabled', selection=[
            ('disabled', 'Disabled'), ('enabled', 'Enabled'),
            ('test', 'Test Mode')],
        ondelete={'disabled': 'cascade', 'enabled': 'cascade',
                  'test': 'cascade'},
        help=('In test mode, a fake payment is processed through a test '
              'payment interface. This mode is advised when setting up the '
              'acquirer. Watch out, test and production modes require '
              'different credentials.'))
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
        return {'type': 'ir.actions.do_nothing', }

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

    def sms_send(self, sms_id):
        self.ensure_one()
        m = '{}_sms_send'.format(self.provider)
        if hasattr(self, m):
            return getattr(self, m)(sms_id)
        if self.is_log_enabled:
            self.env['kw.sms.log'].create({
                'request': 'send sms id {}'.format(sms_id),
                'provider_id': self.id, })
        return True

    def sms_status(self, sms_id):
        self.ensure_one()
        m = '{}_sms_status'.format(self.provider)
        if hasattr(self, m):
            if self.is_log_enabled:
                self.env['kw.sms.log'].create({
                    'request': 'send sms id {}'.format(sms_id),
                    'provider_id': self.id, })
            return getattr(self, m)(sms_id)
        return True

    def sms_sender(self, sender_name):
        self.ensure_one()
        m = '{}_sms_sender'.format(self.provider)
        if hasattr(self, m):
            return getattr(self, m)(sender_name)
        return sender_name
