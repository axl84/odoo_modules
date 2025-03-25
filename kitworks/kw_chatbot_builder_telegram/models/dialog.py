# flake8: noqa: E501
import base64

import logging
import tempfile

from telebot import types
from odoo import models, fields, api, _
from odoo.addons.kw_mixin.models.transliterate_clean import CleanUpMixin
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

INPUTS = ['free_input_single', 'question_name',
          'question_email', 'update_contact_field']


class StepTelegramButton(models.Model):
    _name = 'kw.chatbot.step.telegram.button'
    _description = 'Step Telegram button'

    DEFAULT_PYTHON_CODE = """# Available variables:
    #  - env: Odoo Environment on which the action is triggered
    #  - model: Odoo Model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - float_compare: Odoo function to compare floats based on specific precisions
    #  - log: log(message, level='info'): logging function to record debug information in ir.logging table
    #  - UserError: Warning Exception to use with raise
    #  - Command: x2Many commands namespace
    #  - sender_user: Telegram user who sent the message
    #  - sender_partner: Telegram user's partner
    # To return an action, assign: action = {...}\n\n\n\n"""

    name = fields.Char(
        required=True, )  # todo: translate=True,
    sequence = fields.Integer(
        default=1, )
    active = fields.Boolean(
        default=True, )
    step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    callback_data = fields.Char(compute='_compute_callback_data', )
    successful_text_line_id = fields.One2many(
        comodel_name='kw.telegram.button.notification.line',
        inverse_name='telegram_button_id', string='Text Line', )
    successful_notification = fields.Text(required=True, compute='_compute_ready_message', )
    unsuccessful_text_line_id = fields.One2many(
        comodel_name='kw.telegram.button.un.notification.line',
        inverse_name='telegram_button_id', string='Text Line', )
    unsuccessful_notification = fields.Text(required=True, compute='_compute_unready_message', )
    url = fields.Char()
    notification_id = fields.Many2one(
        comodel_name='kw.chatbot.notification', invisible=True, )
    notification_model_name = fields.Char(
        related='notification_id.model_id.model')
    fields_lines = fields.One2many(
        comodel_name='ir.actions.server', inverse_name='telegram_button_id')
    model_id = fields.Many2one(
        comodel_name='ir.model', string='Model', )
    model_name = fields.Char(
        related='model_id.model', )
    forward_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    state = fields.Selection(
        [('code', 'Execute Python Code'),
         ('object_create', 'Create a new Record	'),
         ('object_write', 'Update a Record'),
         ('multi', 'Execute several actions	'),
         ('email', 'Send Email	'),
         ('followers', 'Add Followers'),
         ('next_activity', 'Create Next Activity'),
         ('sms', 'Send SMS Text Message	'),
         ('send_notification', 'Send Notification'),
         ('forward_step', 'Forward Step'),
         ('url_button', 'URL'),
         ('dynamic_button', 'Dynamic Button'),
         ],
        default='object_write', required=True, copy=True,
        help="Type of server action. The following values are available:\n"
             "- 'Execute Python Code': a block of python code that will be executed\n"
             "- 'Create': create a new record with new values\n"
             "- 'Update a Record': update the values of a record\n"
             "- 'Execute several actions': define an action that triggers several other server actions\n"
             "- 'Send Email': automatically send an email (Discuss)\n"
             "- 'Add Followers': add followers to a record (Discuss)\n"
             "- 'Create Next Activity': create an activity (Discuss)")
    code = fields.Text(string='Python Code', groups='base.group_system',
                       default=DEFAULT_PYTHON_CODE,
                       help="Write Python code that the action will execute. Some variables are "
                            "available for use; help about python expression is given in the help tab.")
    target_model_id = fields.Many2one('ir.model', string='Target Model',
                                      help="Model for record creation / update. Set this field only to specify a different model than the base model.")
    target_model_name = fields.Char(related='target_model_id.model', string='Target Model Name', readonly=True)
    link_field_id = fields.Many2one('ir.model.fields',
                                    help="Provide the field used to link the newly created record "
                                         "on the record used by the server action.")
    # Followers
    partner_ids = fields.Many2many('res.partner', string='Add Followers')
    # Template
    template_id = fields.Many2one(
        'mail.template', 'Email Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]",
    )

    # Multi
    child_ids = fields.Many2many('ir.actions.server',
                                 string='Child Actions',
                                 help='Child server actions that will be executed. Note that the last return returned action value will be used as global return value.')
    # Next Activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity',
        domain="['|', ('res_model', '=', False), ('res_model', '=', model_name)]",
        ondelete='restrict')
    activity_summary = fields.Char('Summary')
    activity_note = fields.Html('Note')
    activity_date_deadline_range = fields.Integer(string='Due Date In')
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')
    activity_user_type = fields.Selection([
        ('specific', 'Specific User'),
        ('generic', 'Generic User From Record')], default="specific",
        help="Use 'Specific User' to always assign the same user on the next activity. Use 'Generic User From Record' to specify the field name of the user to choose on the record.")
    activity_user_id = fields.Many2one('res.users', string='Responsible')
    activity_user_field_name = fields.Char('User field name', help="Technical name of the user on the record",
                                           default="user_id")
    # SMS
    sms_template_id = fields.Many2one(
        'sms.template', 'SMS Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]",
    )
    sms_mass_keep_log = fields.Boolean('Log as Note', default=True)
    # send notification
    notification_for_send = fields.Many2one(
        comodel_name='kw.chatbot.notification', )

    uns_notification_for_send = fields.Many2one(
        string='Unsuccessful Notification',
        comodel_name='kw.chatbot.notification', )

    use_parent_record = fields.Boolean(
        default=False, )
    model_notification_id = fields.Many2one(
        comodel_name='ir.model', string='Child Model',
        compute='_compute_model_notification_id', )
    model_notification_name = fields.Char()
    child_field_id = fields.Many2one(
        comodel_name='ir.model.fields', )
    child_field_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        compute_sudo=True, compute='_compute_child_field')
    url_field_id = fields.Many2one(
        comodel_name='ir.model.fields', )
    id_record = fields.Integer()
    product_id = fields.Many2one(
        comodel_name='product.product', )

    dynamic_button_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Field')
    dynamic_button_action = fields.Selection(
        selection=[('update', 'Update record'),
                   ('comparison', 'Comparison'), ],
        default='update', string='Action')
    dynamic_button_domain = fields.Char(string='Match all records')
    dynamic_button_name_model = fields.Char(
        compute='_compute_dynamic_button_name_model')
    comparison_value_type = fields.Selection(
        selection=[('value', 'Value'),
                   ('field', 'Field'), ],
        default='field', string='Result Type')
    comparison_value = fields.Char(string='Value')
    comparison_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Field')
    comparison_record_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Record Field')
    comparison_type = fields.Selection(
        selection=[('eq', '='),
                   ('not_eq', '!='),
                   ('gt', '>'),
                   ('gte', '>='),
                   ('lt', '<'),
                   ('lte', '<='), ],
        default='eq', string='Action')
    comparison_result_text = fields.Char(
        default='Failed')

    button_name = fields.Text()

    inverse_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Inverse Field')
    dynamic_button_field_ttype = fields.Char()

    write_type = fields.Selection(
        selection=[('value', 'Value'),
                   ('tg_input', 'Telegram Input')],
        ondelete={'tg_input': 'set default'})
    change_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Record Field')

    button_step_ids = fields.One2many(
        comodel_name='kw.chatbot.telegram.button.step',
        inverse_name='telegram_button_id')

    search_type = fields.Selection(selection=[
        ('children', 'In Children'),
        ('parent', 'In Parent'), ], default='children')

    send_notification_type = fields.Selection(selection=[
        ('field_search', 'Field Search'),
        ('record', 'Record'), ], default='record')
    limit = fields.Integer(default=10)
    search_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Record Field')
    record_fields_ids = fields.Many2many(
        comodel_name='ir.model.fields', ondelete='cascade')
    send_new_record = fields.Boolean(
        default=False)
    new_record_notification_id = fields.Many2one(
        comodel_name='kw.chatbot.notification')

    is_resend_notification = fields.Boolean(
        default=False, string='Resend Notification')

    @api.onchange('send_notification_type')
    def _onchange_send_notification_type(self):
        for obj in self:
            if obj.send_notification_type == 'field_search':
                obj.use_parent_record = False
            if obj.send_notification_type != 'field_search':
                obj.search_field_id = False

    @api.onchange('search_type')
    def _compute_child_field(self):
        for obj in self:
            field_ids = self.env['ir.model.fields']
            if obj.model_id and obj.model_notification_id:
                if obj.search_type == 'children':
                    field_ids = self.env['ir.model.fields'].search([
                        ('relation', '=', obj.model_id.model),
                        ('model_id', '=', obj.model_notification_id.id)])
                if obj.search_type == 'parent':
                    field_ids = self.env['ir.model.fields'].search([
                        ('model_id', '=', obj.model_id.id),
                        ('relation', '=', obj.model_notification_id.model)])
            obj.child_field_ids = [(6, 0, field_ids.ids)]


    @api.onchange('dynamic_button_field_id')
    def _onchange_dynamic_button_field_ttype(self):
        for obj in self:
            if obj.dynamic_button_field_id:
                obj.dynamic_button_field_ttype \
                    = obj.dynamic_button_field_id.ttype

    def _compute_dynamic_button_name_model(self):
        for obj in self:
            obj.dynamic_button_name_model = ''
            if obj.dynamic_button_field_id:
                if obj.dynamic_button_field_id.ttype in [
                    'many2one', 'many2many', 'one2many']:
                    model = obj.dynamic_button_field_id.relation
                    obj.dynamic_button_name_model = model

    @api.onchange('state')
    def _onchange_state(self):
        for rec in self:
            if rec.state in ['url_button', 'send_notification']:
                rec.model_id = rec.notification_id.model_id.id
            if rec.state == 'dynamic_button':
                rec.model_id = rec.notification_id.model_id.id
                rec.model_name = rec.notification_id.model_id.model

    @api.onchange('dynamic_button_field_id', 'button_name')
    def _onchange_dynamic_button_button(self):
        for rec in self:
            if rec.dynamic_button_field_id:
                rec.name = "{{object}}"
                rec._compute_dynamic_button_name_model()
            if rec.dynamic_button_field_id.ttype in [
                'many2one', 'many2many', 'one2many']:
                rec.name = rec.button_name

    @api.onchange('notification_for_send')
    def _compute_model_notification_id(self):
        for rec in self:
            if rec.notification_for_send:
                rec.model_notification_id = rec.notification_for_send.model_id
                rec.model_notification_name = rec.notification_for_send.model_id.model
            else:
                rec.model_notification_id = False
                rec.model_notification_name = False

    @api.onchange('unsuccessful_text_line_id')
    def _compute_unready_message(self):
        for rec in self:
            rec.unsuccessful_notification = rec._get_message_un_designer()

    @api.onchange('successful_text_line_id')
    def _compute_ready_message(self):
        for rec in self:
            rec.successful_notification = rec._get_message_designer()

    def _get_message_designer(self):
        self.ensure_one()
        message = ''
        for line in self.successful_text_line_id.sorted(key=lambda r: r.sequence):
            message += line.part_message if line.part_message else ' '
        return message

    def _get_message_un_designer(self):
        self.ensure_one()
        message = ''
        for line in self.unsuccessful_text_line_id.sorted(key=lambda r: r.sequence):
            message += line.part_message if line.part_message else ' '
        return message

    def _compute_callback_data(self):
        for rec in self:
            rec.callback_data = {'id_button': rec.id}


class IrServerObjectLines(models.Model):
    _inherit = 'ir.actions.server'

    telegram_button_id = fields.Many2one(
        comodel_name='kw.chatbot.step.telegram.button')


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    telegram_keyboard_ids = fields.One2many(
        comodel_name='kw.chatbot.step.telegram.keyboard',
        inverse_name='step_id', )
    telegram_button_ids = fields.One2many(
        comodel_name='kw.chatbot.step.telegram.button',
        inverse_name='step_id', copy=True)
    telegram_stop_conv = fields.Boolean(
        default=True, )

    @api.onchange('answer_ids')
    def _compute_answer_telegram(self):
        for obj in self:

            # To avoid duplication of buttons
            if not isinstance(obj.id, int):
                continue

            obj.telegram_button_ids = False
            ids = []
            for ans in obj.answer_ids.sorted('sequence'):
                if not ans.name:
                    continue
                keyboard = self.env['kw.chatbot.step.telegram.keyboard'].sudo(
                ).create({'step_id': self.id, 'name': ans.name})
                if ans._origin:
                    languages = self.env['res.lang'].search(
                        [('active', '=', 'true')])
                    for lang in languages.mapped('code'):
                        lang_answer = ans.with_context(lang=lang).name
                        if lang_answer:
                            keyboard.with_context(lang=lang).name = lang_answer
                ids.append(keyboard.id)
            obj.telegram_keyboard_ids = [(6, 0, ids)]

    def send_schedule_step(self, conversation):
        # self - check about this
        if conversation.chat_id.messenger_id.provider == 'telegram':
            message = self.with_context(
                lang=conversation.sender_id.partner_id.lang).text
            markup = None
            buttons = False
            if self.telegram_keyboard_ids:
                markup, buttons = self.get_telegram_keyboard_markup()
            if self.telegram_button_ids:
                markup, buttons = self.get_telegram_button_markup()
            return conversation.send_message(
                text=message, reply_markup=markup, buttons=buttons)
        return super().send_schedule_step(conversation)

    def get_telegram_keyboard_markup(self):
        self.ensure_one()
        if self.telegram_keyboard_ids:
            buttons_names = []
            if self.step_type == 'request_notification' and \
                    self.go_to_step_id:
                markup = types.ReplyKeyboardMarkup(
                    row_width=2, resize_keyboard=True, one_time_keyboard=False)
            else:
                markup = types.ReplyKeyboardMarkup(
                    row_width=2, resize_keyboard=True, one_time_keyboard=True)
            if self.step_type == 'request_notification' and \
                    not self.go_to_step_id:
                for k in self.answer_ids:
                    if k.notification_id:
                        markup = types.ReplyKeyboardMarkup(
                            row_width=2, resize_keyboard=True,
                            one_time_keyboard=False)
                        break

            buttons = []
            for k in self.telegram_keyboard_ids.sorted('sequence'):
                buttons.append(types.KeyboardButton(
                    k.name, request_location=k.is_location))
                buttons_names.append(k.name)
            markup.add(*buttons)
            return markup, buttons_names
        return None

    def get_telegram_button_markup(self):
        self.ensure_one()
        if self.telegram_button_ids:
            buttons = []
            markup = types.InlineKeyboardMarkup()
            for k in self.telegram_button_ids:
                if k.url:
                    markup.add(types.InlineKeyboardButton(
                        k.name, url=k.url))
                    buttons.append(k.name)
                if k.callback_data:
                    markup.add(types.InlineKeyboardButton(
                        k.name, callback_data=k.callback_data))
                    buttons.append(k.name)
            return markup, buttons
        return None

    # pylint: disable=R0915,R0911,R0914,R0912
    def telegram_get_response(self, conversation, bot, message):
        self.ensure_one()
        if self.triggering_answer_domain:
            domain = safe_eval(self.triggering_answer_domain)
            # check in sender_id.partner_id in domain
            check_partner = self.env['res.partner'].sudo().search(
                domain)
            if conversation.sender_id.partner_id in check_partner:
                _logger.info(f'Partner {conversation.sender_id.partner_id}'
                             f' in domain {domain}')
            else:
                _logger.info(f'Partner {conversation.sender_id.partner_id}'
                             f' not in domain {domain}')
                redirect_step = self.triggering_answer_redirect_step_id
                if redirect_step and redirect_step.answer_ids:
                    conversation.last_step_id = redirect_step.id
                if self.step_type == 'request_notification':
                    step = redirect_step
                    step.telegram_get_response(conversation, bot, message)
                    if not conversation.input_step_id:
                        conversation.telegram_next_step(step, bot, message)
                    return False
                if redirect_step and redirect_step.step_type in INPUTS:
                    step = redirect_step
                    step.telegram_get_response(conversation, bot, message)
                    if not conversation.input_step_id:
                        conversation.telegram_next_step(step, bot, message)
                    return False
                return {
                    'redirect': self.triggering_answer_redirect_step_id}
        if conversation.dialog_id:
            if self.step_type in INPUTS:
                text_msg = self.with_context(lang=conversation.sender_id.partner_id.lang).text
                if self.step_type == 'update_contact_field' and \
                        self.update_contact_field.name in \
                        ['phone', 'mobile']:
                    keyboard = types.ReplyKeyboardMarkup(
                        row_width=1, resize_keyboard=True)
                    button_phone = types.KeyboardButton(
                        text=self.telegram_send_contact_text,
                        request_contact=True)
                    keyboard.add(button_phone)
                    conversation.send_message(
                        text=text_msg, reply_markup=keyboard)
                    conversation.input_step_id = self.id
                    return True
                if self.step_type == 'update_contact_field' and \
                        self.update_contact_field.ttype in \
                        ['many2one', 'many2many']:
                    markup, buttons = None, []
                    markup = types.InlineKeyboardMarkup()
                    # button = False
                    for but in self.env[
                        self.update_contact_field.relation].search([]):
                        call_back = {
                            'id': but.id,
                            't': 'UCF'
                        }
                        text = but.with_context(
                            lang=conversation.sender_id.partner_id.lang).name
                        button = types.InlineKeyboardButton(
                            text=text, callback_data=str(call_back))
                        buttons.append(button)
                    # markup = types.ReplyKeyboardMarkup(
                    #     row_width=1, resize_keyboard=True)
                    markup.add(*buttons)
                    conversation.send_message(
                        text=text_msg, reply_markup=markup, buttons=buttons)
                    self.telegram_stop_conv = True
                    conversation.input_step_id = self.id
                    return True
                if self.step_type == 'update_contact_field' and \
                        self.update_contact_field.ttype == 'boolean':
                    markup, buttons = None, []
                    markup = types.InlineKeyboardMarkup()
                    # button = False
                    for but in [True, False]:
                        call_back = {
                            'id': f'{but}',
                            't': 'UCF'
                        }
                        button = types.InlineKeyboardButton(
                            text=f'{but}', callback_data=str(call_back))
                        buttons.append(button)
                    # markup = types.ReplyKeyboardMarkup(
                    #     row_width=1, resize_keyboard=True)
                    markup.add(*buttons)
                    conversation.send_message(
                        text=text_msg, reply_markup=markup, buttons=buttons)
                    conversation.input_step_id = self.id
                    return True
                if self.step_type == 'update_contact_field' and \
                        self.update_contact_field.ttype == 'selection':
                    markup, buttons = None, []
                    markup = types.InlineKeyboardMarkup()
                    # button = False
                    for but in self.env[self.update_contact_field.model].fields_get(
                            allfields=[self.update_contact_field.name])[self.update_contact_field.name]['selection']:
                        call_back = {
                            'id': but[0],
                            't': 'UCF'
                        }
                        button = types.InlineKeyboardButton(
                            text=but[1], callback_data=str(call_back))
                        buttons.append(button)
                    # markup = types.ReplyKeyboardMarkup(
                    #     row_width=1, resize_keyboard=True)
                    markup.add(*buttons)
                    conversation.send_message(
                        text=text_msg, reply_markup=markup, buttons=buttons)
                    conversation.input_step_id = self.id
                    return False
                if self.step_type == 'update_contact_field':
                    markup = None
                    buttons = False
                    if self.telegram_keyboard_ids:
                        markup, buttons = self.get_telegram_keyboard_markup()
                    conversation.send_message(
                        text=text_msg, reply_markup=markup, buttons=buttons)
                else:
                    conversation.send_message(text=text_msg)
                conversation.input_step_id = self.id
                conversation.last_step_id = self.id
                return True

        if self.step_type == 'create_lead':
            self.create_lead(conversation)
            conversation.telegram_next_step(self, bot, message)
            return True

        markup = None
        buttons = False
        if self.telegram_keyboard_ids:
            markup, buttons = self.get_telegram_keyboard_markup()
        if self.telegram_button_ids:
            markup, buttons = self.get_telegram_button_markup()
        media_murkup, media = [], []
        for obj in self.media_ids:
            if obj.media_type == 'video':
                media_file = tempfile.NamedTemporaryFile()
                media_file.write(base64.b64decode(obj.media_file))
                media_file.seek(0)
                media_murkup.append(types.InputMediaVideo(
                    open(media_file.name, 'rb')))
                media.append(media_file.name)
            elif obj.media_type == 'image':
                media_file = tempfile.NamedTemporaryFile()
                media_file.write(base64.b64decode(obj.image_file))
                media_file.seek(0)
                media_murkup.append(types.InputMediaPhoto(
                    open(media_file.name, 'rb')))
                media.append(media_file.name)
        if media_murkup:
            bot.send_media_group(conversation.telegram_id, media_murkup)
            conversation.telegram_out_message(text={'media': media})
        if not markup:
            markup = types.ReplyKeyboardRemove()

        if self.step_type == 'forward_operator':
            if not self.is_not_send_send_text:
                text_msg = self.with_context(lang=conversation.sender_id.partner_id.lang).text
                conversation.send_message(
                    text=text_msg, reply_markup=markup, buttons=buttons)
            _operator = self.operator_forward(conversation, message)

            # go to step redirect_to step_id if the operator is not available
            if not _operator and self.redirect_step_id:
                conversation.is_no_reply = True
                step = self.redirect_step_id
                step.telegram_get_response(conversation, bot, message)
                return True

            if not _operator:
                return {'redirect': self.redirect_step_id}
            return True
        # translate text on language of conversation sender lang
        text_msg = self.with_context(lang=conversation.sender_id.partner_id.lang).text
        conversation.send_message(
            text=text_msg, reply_markup=markup, buttons=buttons)
        if conversation.dialog_id:
            if self.step_type == 'text' and self.select_flow == 'default':
                return False
        return True

    def telegram_add_partner(self, conversation, bot, message):
        self.ensure_one()
        # _logger.info('telegram_add_partner')
        conversation.sudo().is_creation_awaiting = True
        if conversation.sender_id.partner_id:
            conversation.send_message(text=_('Partner already exist'))
            return conversation.sender_id.partner_id
        if not conversation.sender_id.partner_phone \
                or not conversation.sender_id.partner_name:
            keyboard = types.ReplyKeyboardMarkup(row_width=1,
                                                 resize_keyboard=True)
            button_phone = types.KeyboardButton(
                text=self.telegram_send_contact_text, request_contact=True)
            keyboard.add(button_phone)
            conversation.send_message(text=_('Please share contact'),
                                      reply_markup=keyboard)
        else:
            conversation.send_message(
                text=_('Please write your email (example@example.com)'))
        return True

    def telegram_partner_contact(self, conversation, bot, message):
        self.ensure_one()
        # _logger.info('telegram_partner_contact')
        contact = message.get('contact')
        phone = CleanUpMixin.kw_clean_digit_only(contact.get('phone_number'))
        if not conversation.sender_id.partner_phone and \
                self.chatbot_check_phone(conversation, phone):
            conversation.sudo().sender_id.partner_phone = phone
        if not conversation.sender_id.partner_name and \
                contact.get('first_name'):
            conversation.sudo().sender_id.partner_name = \
                contact.get('first_name')
        if conversation.sender_id.partner_name and \
                conversation.sender_id.partner_phone:
            if not conversation.sender_id.partner_email:
                conversation.send_message(
                    text=_('Please write your email (example@example.com)'))
            else:
                self.telegram_partner_create(conversation, bot, message)
            return True
        return True

    def telegram_partner_email(self, conversation, bot, message):
        self.ensure_one()
        # _logger.info('telegram_partner_email')
        text = conversation.telegram_get_message_data(message)
        if not conversation.sender_id.partner_email and \
                self.chatbot_check_email(conversation, text):
            conversation.sudo().sender_id.partner_email = text
            self.telegram_partner_create(conversation, bot, message)
        else:
            conversation.send_message(
                text=_('Please write correct email '))
        return True

    def telegram_partner_create(self, conversation, bot, message):
        self.ensure_one()
        # _logger.info('telegram_partner_create')
        if conversation.is_creation_awaiting:
            conversation.sudo().sender_id.partner_id = \
                self.chatbot_add_partner(conversation)
            conversation.is_creation_awaiting = False
            markup, buttons = None, []
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton(
                text=_('Continue?'),
                callback_data='/start')
            markup.add(btn)
            markup.add(*buttons)
            conversation.send_message(
                text=_('Create contact success'),
                reply_markup=markup, buttons=buttons)
        return True


class MessageNotificationLineButton(models.Model):
    _name = 'kw.telegram.button.notification.line'
    _description = 'Message Notification Line'

    telegram_button_id = fields.Many2one('kw.chatbot.step.telegram.button', )
    model_id = fields.Many2one('ir.model',
                               required=True,
                               ondelete='cascade',
                               related='telegram_button_id.model_id', )
    model_name = fields.Char(related='model_id.model', )
    fields_id = fields.Many2one('ir.model.fields',
                                ondelete='cascade',
                                domain="[('model_id', '=', model_id)]",
                                )
    sub_model = fields.Char(related='fields_id.relation', )
    sub_fields_id = fields.Many2one('ir.model.fields',
                                    ondelete='cascade',
                                    domain="[('model_id', '=', model_id)]",
                                    )
    text_before = fields.Char()  # todo: translate=True
    text_after = fields.Char()  # todo: translate=True
    sequence = fields.Integer()
    need_after_before_text_new_line = fields.Boolean(default=False, string='New line after text')
    need_after_after_text_new_line = fields.Boolean(default=True, string='New line after text')
    part_message = fields.Char(compute='_compute_part_message', )

    @api.onchange('text_before', 'need_after_before_text_new_line', 'text_after', 'need_after_after_text_new_line')
    def _compute_text(self):
        for rec in self:
            rec.text_before = rec.text_before.replace('<br/>', '') if rec.text_before else ''
            if rec.need_after_before_text_new_line:
                rec.text_before = '%s<br/>' % rec.text_before
            else:
                rec.text_before = '%s' % rec.text_before.replace('<br/>', '')
            rec.text_after = rec.text_after.replace('<br/>', '') if rec.text_after else ''
            if rec.need_after_after_text_new_line:
                rec.text_after = '%s<br/>' % rec.text_after
            else:
                rec.text_after = '%s' % rec.text_after.replace('<br/>', '')

    # @api.onchange('text_after', 'need_after_after_text_new_line')
    # def _compute_text_after(self):
    #     for rec in self:
    #         rec.text_after = rec.text_after.replace('<br/>', '') if rec.text_after else ''
    #         if rec.need_after_after_text_new_line:
    #             rec.text_after = '%s<br/>' % rec.text_after
    #         else:
    #             rec.text_after = '%s' % rec.text_after.replace('<br/>', '')

    def _compute_part_message(self):
        for rec in self:
            text_before = rec.text_before or ''
            text_after = rec.text_after or ''
            if rec.fields_id.ttype in ['many2one', 'one2many', 'many2many'] \
                    and rec.sub_fields_id:
                part_message = '%s {{object.%s.%s}} %s' % (
                    text_before,
                    rec.fields_id.name,
                    rec.sub_fields_id.name,
                    text_after)
            else:
                if rec.fields_id:
                    part_message = \
                        '%s {{object.%s}} %s' % (text_before,
                                                 rec.fields_id.name,
                                                 text_after)
                else:
                    part_message = '%s %s' % (text_before, text_after)
            rec.part_message = part_message
            # if rec.line_message_need_serial_number:
            #     rec.part_message = '%s. %s' % (rec.sequence, rec.part_message)


class MessageNotificationLineButtonUn(models.Model):
    _name = 'kw.telegram.button.un.notification.line'
    _description = 'Message Notification Line'

    telegram_button_id = fields.Many2one('kw.chatbot.step.telegram.button', )
    model_id = fields.Many2one('ir.model',
                               required=True,
                               ondelete='cascade',
                               related='telegram_button_id.model_id', )
    model_name = fields.Char(related='model_id.model', )
    fields_id = fields.Many2one('ir.model.fields',
                                ondelete='cascade',
                                domain="[('model_id', '=', model_id)]",
                                )
    sub_model = fields.Char(related='fields_id.relation', )
    sub_fields_id = fields.Many2one('ir.model.fields',
                                    ondelete='cascade',
                                    domain="[('model_id', '=', model_id)]",
                                    )
    text_before = fields.Char()  # todo: translate=True
    text_after = fields.Char()  # todo: translate=True
    sequence = fields.Integer()
    need_after_before_text_new_line = fields.Boolean(default=False, string='New line after text')
    need_after_after_text_new_line = fields.Boolean(default=True, string='New line after text')
    part_message = fields.Char(compute='_compute_part_message', )

    @api.onchange('text_before', 'need_after_before_text_new_line', 'text_after', 'need_after_after_text_new_line')
    def _compute_text(self):
        for rec in self:
            rec.text_before = rec.text_before.replace('<br/>', '') if rec.text_before else ''
            if rec.need_after_before_text_new_line:
                rec.text_before = '%s<br/>' % rec.text_before
            else:
                rec.text_before = '%s' % rec.text_before.replace('<br/>', '')
            rec.text_after = rec.text_after.replace('<br/>', '') if rec.text_after else ''
            if rec.need_after_after_text_new_line:
                rec.text_after = '%s<br/>' % rec.text_after
            else:
                rec.text_after = '%s' % rec.text_after.replace('<br/>', '')

    # @api.onchange('text_after', 'need_after_after_text_new_line')
    # def _compute_text_after(self):
    #     for rec in self:
    #         rec.text_after = rec.text_after.replace('<br/>', '') if rec.text_after else ''
    #         if rec.need_after_after_text_new_line:
    #             rec.text_after = '%s<br/>' % rec.text_after
    #         else:
    #             rec.text_after = '%s' % rec.text_after.replace('<br/>', '')

    def _compute_part_message(self):
        for rec in self:
            text_before = rec.text_before or ''
            text_after = rec.text_after or ''
            if rec.fields_id.ttype in ['many2one', 'one2many', 'many2many'] \
                    and rec.sub_fields_id:
                part_message = '%s {{object.%s.%s}} %s' % (
                    text_before,
                    rec.fields_id.name,
                    rec.sub_fields_id.name,
                    text_after)
            else:
                if rec.fields_id:
                    part_message = \
                        '%s {{object.%s}} %s' % (text_before,
                                                 rec.fields_id.name,
                                                 text_after)
                else:
                    part_message = '%s %s' % (text_before, text_after)
            rec.part_message = part_message
            # if rec.line_message_need_serial_number:
            #     rec.part_message = '%s. %s' % (rec.sequence, rec.part_message)


class StepTelegramKeyboard(models.Model):
    _name = 'kw.chatbot.step.telegram.keyboard'
    _description = 'Step Telegram Keyboard'

    name = fields.Char(
        required=True, string='Code', translate=True, )
    sequence = fields.Integer(default=1, )
    step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    active = fields.Boolean(
        default=True, )
    is_location = fields.Boolean(
        default=False, string='Location Request', )


class StepTelegramButtonStep(models.Model):
    _name = 'kw.chatbot.telegram.button.step'

    DEFAULT_PYTHON_CODE = """# Available variables:
    #  - env: Odoo Environment on which the action is triggered
    #  - model: Odoo Model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - float_compare: Odoo function to compare floats based on specific precisions
    #  - log: log(message, level='info'): logging function to record debug information in ir.logging table
    #  - UserError: Warning Exception to use with raise
    #  - Command: x2Many commands namespace
    #  - sender_user: Telegram user who sent the message
    #  - sender_partner: Telegram user's partner
    # To return an action, assign: action = {...}\n\n\n\n"""

    sequence = fields.Integer(default=10, )
    telegram_button_id = fields.Many2one(
        comodel_name='kw.chatbot.step.telegram.button')
    model_id = fields.Many2one(
        readonly=True, required=True,
        comodel_name='ir.model',
        ondelete='cascade', )
    model_name = fields.Char(
        related='model_id.model' )
    step_type = fields.Selection(
        selection=[('step', 'Step'),
                   ('notification', 'Notification'),
                   ('code', 'Python Code')],
        default='step', )
    action_type = fields.Selection(
        selection=[('before_action', 'Before'),
                   ('after_action', 'After')],
        default='after_action', )
    action_result_type = fields.Selection(
        selection=[('anyway', 'Anyway'),
                   ('successful', 'Successful'),
                   ('unsuccessful', 'Unsuccessful')],
        default='successful', )
    bind_record = fields.Boolean(
        default=False)
    domain = fields.Char(string='Match all records', )
    is_domain = fields.Boolean(
        compute='_compute_is_domain', )
    successful_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    successful_notification_id = fields.Many2one(
        comodel_name='kw.chatbot.notification', )
    code = fields.Text(
        string='Python Code', groups='base.group_system',
        default=DEFAULT_PYTHON_CODE,
        help="Write Python code that the action will execute. Some variables "
             "are available for use; help about python expression "
             "is given in the help tab.")

    @api.onchange('domain')
    def _compute_is_domain(self):
        for obj in self:
            obj.is_domain = False
            if obj.domain:
                obj.is_domain = True

    @api.onchange('action_type')
    def _onchange_action_type(self):
        for obj in self:
            if obj.action_type == 'before_action':
                obj.action_result_type = 'anyway'

    @api.onchange('step_type')
    def _onchange_step_type(self):
        for obj in self:
            if obj.step_type == 'step':
                obj.write({
                    'bind_record': False,
                    'successful_notification_id': False, })
            if obj.step_type == 'notification':
                obj.write({
                    'bind_record': False,
                    'successful_step_id': False, })


class ChatbotDialogAnswer(models.Model):
    _inherit = 'chatbot.dialog.answer'

    @api.model
    def create(self, vals_list):
        result = super(ChatbotDialogAnswer, self).create(vals_list)
        for obj in result:
            if obj.dialog_step_id:
                obj.dialog_step_id._compute_answer_telegram()
        return result

    def write(self, vals):
        result = super(ChatbotDialogAnswer, self).write(vals)
        for obj in self:
            if vals.get('name') or vals.get('sequence') and obj.dialog_step_id:
                obj.dialog_step_id._compute_answer_telegram()
        return result

    def unlink(self):
        dialog_step_id = self.dialog_step_id
        result = super(ChatbotDialogAnswer, self).unlink()
        if dialog_step_id:
            dialog_step_id._compute_answer_telegram()
        return result
