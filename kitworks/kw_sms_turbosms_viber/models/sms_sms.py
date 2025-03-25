import logging

from odoo import fields, models, _, api

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    kw_turbosms_sms_or_viber = fields.Selection(
        default='sms', required=True, string='Sms or Viber',
        selection=[('sms', _('SMS')), ('viber', _('VIBER')),
                   ('sms_viber', _('SMS and Viber')), ], )
    kw_body_viber_sms = fields.Text()
    kw_viber_numbers = fields.Char(compute='_compute_viber_widget')
    kw_sms_numbers = fields.Char(compute='_compute_sms_widget')
    kw_turbosms_is_transactional = fields.Boolean(
        string='Is transactional', )
    kw_turbosms_ttl = fields.Integer(
        string='Time-to-live', )
    kw_turbosms_image_url = fields.Char(
        string='Image url', )
    kw_turbosms_caption = fields.Char(
        string='Caption', )
    kw_turbosms_action = fields.Char(
        string='Action', )
    kw_turbosms_file_id = fields.Integer(
        string='File', )
    kw_turbosms_is_count_clicks = fields.Boolean(
        string='Count clicks', )

    @api.model
    def create(self, vals):
        if not vals.get('body') or not vals['body']:
            vals['body'] = '0'
        return super(SmsSms, self).create(vals)

    @api.onchange('kw_body_viber_sms')
    def _compute_viber_widget(self):
        for obj in self:
            if obj.kw_body_viber_sms:
                obj.kw_viber_numbers = \
                    f'{len(obj.kw_body_viber_sms)} characters, ' \
                    f'recorded in viber message | limit 1000'
            else:
                obj.kw_viber_numbers = '0 characters, ' \
                    'recorded in viber message | limit 1000'

    @api.onchange('body')
    def _compute_sms_widget(self):
        for obj in self:
            if obj.body:
                obj.kw_sms_numbers = f'{len(obj.body)} characters, ' \
                    'recorded in viber message | limit 661'
            else:
                obj.kw_sms_numbers = '0 characters, ' \
                    'recorded in viber message | limit 661'
