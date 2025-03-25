# pylint: disable=W7950
import logging
import re

from odoo.addons.http_routing.models.ir_http import slugify
from odoo.addons.kw_graph_api.models.graph_api import FacebookGraphApi
from odoo.addons.kw_chatbot_whatsapp.data.lang_list import Languages
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _name = 'kw.chatbot.whatsapp.template'
    _description = 'Whatsapp Template'

    name = fields.Char(
        required=True, )
    status = fields.Selection([
        ('draft', 'Draft'),
        ('error', 'Error'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')],
        default='draft', copy=False, tracking=True)
    template_id = fields.Char(
        string="WhatsApp Template ID", copy=False, readonly=1)
    lang = fields.Selection(
        required=True,
        selection=Languages, string='Language')
    template_name = fields.Char(
        compute='_compute_template_name',
        readonly=False, store=True)
    chat_id = fields.Many2one(
        required=True,
        comodel_name='kw.chatbot.chat')

    template_category = fields.Selection(selection=[
        ('authentication', 'Authentication'),
        ('marketing', 'Marketing'),
        ('utility', 'Utility')], string="Category", default='marketing')

    model_id = fields.Many2one(
        comodel_name='ir.model',
        ondelete='cascade', required=True)
    model = fields.Char(
        string='Related Template Model',
        related='model_id.model',
        precompute=True, store=True, readonly=True)

    body_text = fields.Text(
        string="Template Body")
    header_text = fields.Text(
        string="Template Header", size=60)
    footer_text = fields.Text(
        string="Template Footer")

    error_msg = fields.Text(string="Error", readonly=1)

    conversation_ids = fields.Many2many(
        compute_sudo=True,
        comodel_name='kw.chatbot.conversation',
        compute='_compute_conversation', )

    def _compute_conversation(self):
        for obj in self:
            if obj.chat_id:
                obj.conversation_ids = \
                    [(6, 0, self.env['kw.chatbot.conversation'].sudo().search(
                        [('chat_id', '=', obj.chat_id.id)]).mapped('id'))]
            else:
                obj.conversation_ids = False

    @api.depends('name')
    def _compute_template_name(self):
        for template in self:
            if template.status == 'draft':
                template.template_name = re.sub(
                    r'\W+', '_', slugify(template.name or ''))

    def whatsapp_reset_to_draft(self):
        self.ensure_one()
        self.status = 'draft'

    def whatsapp_submit_template(self):
        self.ensure_one()
        try:
            if self.template_uid:
                self.update_whatsapp_template()
                self.status = 'pending'
            else:
                response = self.get_new_whatsapp_template()
                if response:
                    self.write({
                        'wa_template_uid': response['id'],
                        'status': response['status'].lower()})
        except Exception as e:
            _logger.info(e)

    def prepare_whatsapp_template_data(self):
        self.ensure_one()
        json_data = {
            'name': self.template_name,
            'language': self.lang,
            'category': self.template_category.upper(),
            'components': self._get_template_component(), }
        return json_data

    def get_new_whatsapp_template(self):
        self.ensure_one()
        json_data = self.prepare_whatsapp_template_data()
        try:
            headers = {
                'Content-Type': 'application/json'}
            res = FacebookGraphApi().post_facebook_graph(
                url='/{}/message_templates'.format(
                    self.chat_id.whatsapp_business_account),
                body=json_data, headers=headers)
            if res.get('error'):
                message = res['error']['error']['message']
                self.write({
                    'error_msg': message,
                    'status': 'error'})
                res = False
        except Exception as e:
            _logger.info(e)
            res = False
        return res

    def update_whatsapp_template(self):
        json_data = {
            "name": "seasonal_promotion",
            "language": self.lang,
            "category": self.template_category.upper(),
            'components': self._get_template_component(), }
        try:
            headers = {
                'Content-Type': 'application/json'}
            res = FacebookGraphApi().post_facebook_graph(
                url='/{}'.format(self.template_uid),
                body=json_data, headers=headers)
            if res.get('error'):
                message = res.get['error']['error']['message']
                self.write({
                    'error_msg': message,
                    'status': 'error'})
                res = False
        except Exception as e:
            _logger.info(e)
            res = False
        return res

    def _get_template_component(self):
        component = []
        if self.header_text:
            head_component = {
                'type': 'HEADER', 'format': 'TEXT', 'text': self.header_text}
            component.append(head_component)
        if self.body_text:
            body_component = {'type': 'BODY', 'text': self.body_text}
            component.append(body_component)
        if self.footer_text:
            footer_component = {'type': 'FOOTER', 'text': self.footer_text}
            component.append(footer_component)
        return component

    def send_whatsapp_template(self):
        return {
            'name': _('Send Template'),
            'view_mode': 'form',
            'res_model': 'send.wa.template.wizard',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {
                'default_template_id': self.id,
                'default_conversation_ids':
                    [(6, 0, self.conversation_ids.ids)]}}
