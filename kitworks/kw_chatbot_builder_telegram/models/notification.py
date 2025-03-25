# flake8: noqa: E501
import logging
import ast
import re
from telebot import types

from odoo.tools.safe_eval import safe_eval

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

INPUTS = ['free_input_single', 'question_name',
          'question_email']


class Notification(models.Model):
    _inherit = 'kw.chatbot.notification'

    telegram_button_ids = fields.One2many(
        comodel_name='kw.chatbot.step.telegram.button',
        inverse_name='notification_id', )
    message_not_found = fields.Text(
       default='Sorry, I don\'t understand you')
    related_fields_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        relation='kw_chatbot_builder_telegram_related_fields_ids_rel', )
    sorted_field_id = fields.Many2one(
        comodel_name='ir.model.fields', )
    filtered_fields_ids = fields.One2many(
        comodel_name='kw.chatbot.telegram.filtered.fields',
        inverse_name='notification_id')

    is_days_filter = fields.Boolean(
        default=False, string='Use Days Filter' )

    value_type = fields.Selection(
        selection=[('day', 'Day'),
                   ('weekday', 'Weekday'), ],
        default='day', )
    filter_value = fields.Integer(
        default=0)
    filter_field_id = fields.Many2one(
        comodel_name='ir.model.fields', )
    filter_type = fields.Selection(
        selection=[('eq', '='),
                   ('not_eq', '!='),
                   ('gt', '>'),
                   ('gte', '>='),
                   ('lt', '<'),
                   ('lte', '<='), ],
        default='eq', string='Type')
    is_unique_by_field = fields.Boolean(
        default=False, string='Unique by Field')
    unique_filter_field_id = fields.Many2one(
        comodel_name='ir.model.fields', )

    def copy_data(self, default=None):
        # from notifications copy telegram_button_ids
        if default is None:
            default = {}
        default['telegram_button_ids'] = [
            (0, 0, x.copy_data()[0]) for x in self.telegram_button_ids]
        return super().copy_data(default=default)

    def prepare_notification_text(self, record, **kwargs):
        result = super().prepare_notification_text(record, **kwargs)
        if not result or result.strip() == '':
            result = self.message_not_found
        return result

    def prepare_notification_message(self, template, record):
        rm = self.env['sms.template']._render_template(
            template_src=template,
            model=record._name, res_ids=[record.id], )
        clean = re.compile('<.*?>')
        text = re.sub(r'<br.*?>', '\n', rm[record.id])
        text = text.replace('[', '')
        text = text.replace(']', '')
        text = re.sub(clean, '', text)
        return text

    # pylint: disable=R0914,R0912
    def send_message(self, record, text, conversation_id, **kwargs):
        if conversation_id.chat_id.messenger_id.provider == 'telegram' \
                and not kwargs.get('buttons') and self.telegram_button_ids:
            markup, buttons = None, []
            markup = types.InlineKeyboardMarkup()
            for bt in self.telegram_button_ids:
                callback_data = ast.literal_eval(bt.callback_data.replace(
                    "'", '"'))
                callback_data['id_record'] = record.id
                callback_data['id_con'] = self.id
                if bt.state == 'url_button':
                    url = getattr(record, bt.url_field_id.name)
                    url = self.prepare_url(url)
                    if self.is_url_working(url):
                        btn = types.InlineKeyboardButton(
                            text=_(bt.name), url=url)
                        markup.add(btn)
                elif bt.state == 'dynamic_button':
                    if bt.dynamic_button_field_id.ttype == 'selection':
                        s_model = self.env[bt.dynamic_button_field_id.model]
                        s_data = s_model.fields_get(
                            allfields=[bt.dynamic_button_field_id.name])
                        for but in s_data[bt.dynamic_button_field_id.name][
                            'selection']:
                            db_button = bt.dynamic_button_field_id.id
                            cd = self.env['ir.model.fields.selection'].search([
                                ('field_id', '=', db_button),
                                ('value', '=', but[0])])
                            callback_data['db_id'] = cd.id
                            bt_text = bt.name.replace('{{object}}', but[1])
                            btn = types.InlineKeyboardButton(
                                text=bt_text, callback_data=str(callback_data))
                            markup.add(btn)
                    if bt.dynamic_button_field_id.ttype in [
                        'many2one', 'many2many', 'one2many']:
                        rec_domain = []
                        if (bt.dynamic_button_field_id.ttype == 'one2many'
                                and bt.inverse_field_id):
                            rec_domain.append((
                                bt.inverse_field_id.name, '=', record.id))
                        records = self.env[
                            bt.dynamic_button_field_id.relation].search(
                            rec_domain)
                        if bt.dynamic_button_domain:
                            domain = safe_eval(bt.dynamic_button_domain)
                            records = self.env[
                                bt.dynamic_button_field_id.relation].search(
                                domain)
                        for but in records:
                            callback_data['db_id'] = but.id

                            bt_text = self.prepare_notification_message(
                                bt.button_name, but)
                            btn = types.InlineKeyboardButton(
                                text=bt_text, callback_data=str(callback_data))
                            markup.add(btn)
                else:
                    button_name = bt.name
                    if record:
                        button_name = self.render_message(
                            bt.name, record, **kwargs)
                    btn = types.InlineKeyboardButton(
                        text=_(button_name), callback_data=str(callback_data), )
                    markup.add(btn)
            markup.add(*buttons)
            kwargs.update({
                'sender_user': conversation_id.sender_id.user_id,
                'reply_markup': markup, 'buttons': buttons})
        return super().send_message(record, text, conversation_id, **kwargs)

    def _get_eval_context(self):
        return {
            'uid': self.env.uid,
            'user': self.env.user,
            'context': self.env.context,
            'self': self,
            'record': self,
        }


class TelegramFilteredFields(models.Model):
    _name = 'kw.chatbot.telegram.filtered.fields'
    _description = 'Telegram Filtered Fields'

    notification_id = fields.Many2one(
        comodel_name='kw.chatbot.notification', )
    sequence = fields.Integer()
    model_id = fields.Many2one(
        comodel_name='ir.model', )
    filtered_type = fields.Selection(
        default='conversation', required=True, selection=[
            ('own_model', 'Own Model'),
            ('contact', 'Contact'),
            ('conversation', 'Conversation Activity')], )
    field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        ondelete='cascade',
        domain="[('model_id', '=', model_id),"
               " ('ttype', 'in', ['many2one', 'many2many'])]")
    partner_field_ids = fields.Many2many(
        comodel_name='ir.model.fields', compute_sudo=True,
        compute='_compute_partner_fields', )
    partner_field_id = fields.Many2one(
        comodel_name='ir.model.fields', )

    @api.onchange('field_id', 'filtered_type')
    def _compute_partner_fields(self):
        for obj in  self:
            if not obj.field_id or obj.filtered_type == 'conversation':
                obj.partner_field_ids = [(6, 0, [])]
                obj.partner_field_id = False
            else:
                model_id = self.env['ir.model'].sudo().search(
                    [('model', '=', 'res.partner')], limit=1)
                field_ids = self.env['ir.model.fields'].sudo().search([
                    ('relation', '=', obj.field_id.relation),
                    ('model_id', '=', model_id.id)])
                obj.partner_field_ids = [(6, 0, field_ids.ids)]
                if not field_ids:
                    obj.partner_field_id = False
