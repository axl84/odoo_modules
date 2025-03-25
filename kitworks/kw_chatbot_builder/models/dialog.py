import logging
import base64
import textwrap
from datetime import datetime, timedelta

from odoo import models, fields, api, modules, _

_logger = logging.getLogger(__name__)

SCHEDULE_INTERVALS = [
    ('minutes', 'Every minute'),
    ('hourly', 'Every hour'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly')
]


class Step(models.Model):
    _name = 'kw.chatbot.step'
    _description = 'Step'
    _order = 'sequence, text'

    name = fields.Char(
        string='Code', readonly=False, translate=True, )
    active = fields.Boolean(
        default=True, )
    sequence = fields.Integer(
        default=10, )
    dialog_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog', )
    show_livechat_btn = fields.Boolean(compute='_compute_show_livechat_btn', )
    text = fields.Text(required=True, translate=True, )

    is_messenger_specific = fields.Boolean()

    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger', )
    alias_ids = fields.One2many(
        comodel_name='kw.chatbot.step.alias', inverse_name='step_id', )
    media_ids = fields.One2many(
        comodel_name='kw.chatbot.step.media', inverse_name='step_id', )
    step_type = fields.Selection([
        ('text', 'Text'),
        # ('question_selection', 'Question'),
        ('update_contact_field', 'Update Contact info'),
        ('forward_operator', 'Forward to Operator'),
        ('free_input_single', 'Free Input'),
        ('create_lead', 'Create Lead'),
        ('request_notification', 'Step with Buttons'),
        ('schedule', 'Schedule'),
    ], default='text', required=True)
    # schedule
    schedule_interval = fields.Selection(selection=SCHEDULE_INTERVALS, string='Interval', default='daily')
    schedule_time = fields.Integer(string='Period', default=1)
    schedule_last_run = fields.Datetime(string='Last Run', help='Date and time of last run')
    schedule_next_run = fields.Datetime(string='Next Run', help='Date and time of next run')
    update_contact_field = fields.Many2one(
        comodel_name='ir.model.fields',
        domain=[('model', '=', 'res.partner'), ], )
    update_contact_field_name = fields.Char(
        related='update_contact_field.name')

    name_update_contact_field = fields.Char(related="update_contact_field.name")

    merge_by_phone_number = fields.Boolean(
        default=False)

    msg_after_update_contact_field = fields.Text(
        translate=True, default='Thank you for your information', string='Message after update contact field')
    add_contact_tag_ids = fields.Many2many(
        comodel_name='res.partner.category', relation='kw_chatbot_step_add_contact_tag_rel', )
    remove_contact_tag_ids = fields.Many2many(
        comodel_name='res.partner.category', )
    answer_ids = fields.One2many(
        comodel_name='chatbot.dialog.answer', inverse_name='dialog_step_id',
        copy=True, string='Answers')
    # triggering_answer_ids = fields.Many2many(
    #     'chatbot.dialog.answer',
    #     domain="[('dialog_step_id.sequence', '<', sequence)]",
    #     compute='_compute_triggering_answer_ids', readonly=False, store=True,
    #     copy=False,
    #     string='Only If',
    #     help='Show this step only if all of these answers have been selected.')
    go_to_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', _order='text, sequence', )
    model_res_partner_id = fields.Many2one(
        comodel_name='ir.model', compute='_compute_model_res_partner_id',
        default=lambda self: self.env.ref('base.model_res_partner').id, )
    model_res_partner_name = fields.Char(
        related='model_res_partner_id.model', )
    triggering_answer_domain = fields.Char(string='Show only to partner with', )
    triggering_answer_redirect_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', string='if not suitable for the domain redirect to', )
    odoo_livechat_button_ids = fields.One2many(
        comodel_name='kw.chatbot.step.livechat.button',
        inverse_name='step_id', )

    is_consultant_ready = fields.Boolean()

    is_consultant_not_ready = fields.Boolean()

    bot_operators_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog')
    bot_operators_ids = fields.Many2many(
        comodel_name='kw.chatbot.dialog', compute='_compute_bots_ids', )

    crm_user_id = fields.Many2one(
        comodel_name='res.users', string='Salesperson')
    crm_team_id = fields.Many2one(
        comodel_name='crm.team', string='Sales Team')
    crm_type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')],
        default='opportunity', )
    crm_tag_ids = fields.Many2many(
        comodel_name='crm.tag', string='Tags', )
    select_flow = fields.Selection([
        ('default', 'Default'),
    ], default='default', string='Select Standard Flow', required=True)
    redirect_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step',
        string='If not available operator go to step')
    is_not_send_send_text = fields.Boolean(
        default=False, string="Don't send step text")

    telegram_send_contact_text = fields.Char(
        string="Name of the send contact button", default="Send contact",
        translate=True, )

    @api.onchange('text')
    def _compute_name(self):
        for step in self:
            if step.text:
                step.name = step.text[:50]
            else:
                step.name = 'default_step'

    def _compute_show_livechat_btn(self):
        for step in self:
            step.show_livechat_btn = False
            for channel in step.dialog_id.chatbot_chat_ids:
                if channel.messenger_id.provider == 'odoo_livechat':
                    step.show_livechat_btn = True
                    break

    def open_step_form_view_edit(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'kw.chatbot.step',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'mode': 'edit',
        }

    # def run_step(self):
    #     if self.step_type == 'schedule':
    #         self.schedule_step()
    #     else:
    #         _logger.warning(f'Unknown step type {self.step_type} for step {self.id}')

    def send_schedule_step(self, conversation):
        message = self.with_context(
            lang=conversation.sender_id.partner_id.lang).text
        return conversation.send_message(message)

    def schedule_step(self):
        now = datetime.now()
        steps = self.search([('step_type', '=', 'schedule'), ('schedule_next_run', '<=', now)])
        # filter steps by schedule interval
        _logger.info(f'Found {len(steps)} steps to run')
        for step in steps:
            dialogs = step.dialog_id
            for dialog in dialogs:
                conversations = dialog.conversations_ids
                for conversation in conversations:
                    step.send_schedule_step(conversation)
            # update next run
            if step.schedule_interval == 'hourly':
                step.schedule_next_run = now + timedelta(hours=1)
            elif step.schedule_interval == 'daily':
                step.schedule_next_run = now + timedelta(days=1)
            elif step.schedule_interval == 'weekly':
                step.schedule_next_run = now + timedelta(weeks=1)
            elif step.schedule_interval == 'monthly':
                step.schedule_next_run = now + timedelta(days=30)
            elif step.schedule_interval == 'yearly':
                step.schedule_next_run = now + timedelta(days=365)
            elif step.schedule_interval == 'minutes':
                step.schedule_next_run = now + timedelta(minutes=step.schedule_time)
            step.write({'schedule_last_run': now, 'schedule_next_run': step.schedule_next_run})

    def _compute_model_res_partner_id(self):
        for rec in self:
            rec.model_res_partner_id = self.env.ref(
                'base.model_res_partner').id

    def create_lead(self, conversation):
        text_msg = self.with_context(
            lang=conversation.sender_id.partner_id.lang).text
        lead = self.env['crm.lead'].with_context(uid=self.env.uid).create({
            'name': f'Dialog to {conversation.sender_id.name} | '
                    f'{datetime.today().date()}',
            'kw_conversation_id': conversation.id,
            'user_id': self.crm_user_id.id if self.crm_user_id else False,
            'partner_id': conversation.sender_id.partner_id.id
            if conversation.sender_id.partner_id else False,
            'type': self.crm_type,
            'company_id': conversation.company_id.id,
            'tag_ids': [(6, 0, self.crm_tag_ids.ids)],
            'team_id': self.crm_team_id.id if self.crm_user_id else False})
        if lead and self.dialog_id.send_msg_after_create_lead:
            conversation.send_message(text=text_msg)
        for obj in conversation.chatbot_message_ids:
            if obj.needed_for_lead:
                lead.write({
                    'description':
                        f'{lead.description if lead.description else " "} '
                        f'{obj.sender_id.name}: {obj.text} '
                        f'<br/>'})
                obj.needed_for_lead = False

        tag = self.env['crm.tag'].search([
            ('name', '=', conversation.chat_id.name), ])
        if not tag:
            tag = self.env['crm.tag'].create({
                'name': conversation.chat_id.name, })
        lead.sudo().write({'tag_ids': [(4, tag.id)]})

        return lead

    def get_salesperson_operator(self, partner_id):
        user_id = partner_id.user_id
        if user_id:
            operator = self.bot_operators_id.conversations_ids.search([
                ('sender_id.is_ready_for_consult', '=', True),
                ('wired_conversation_id', '=', False),
                ('sender_id.aproved_consultant', '=', True),
                ('sender_id.partner_id', '=', user_id.partner_id.id)], )
            return operator
        return False

    def get_response(self, conversation, bot, message):
        return False

    def get_correct_operator_bot(self, operator):
        """
        Get operator from current consultant bot
        """
        if operator:
            # get conversations only for consultant bot in current step(self)
            current_bot_conversations = operator.conversation_ids.filtered(
                lambda conv: conv.dialog_id == self.bot_operators_id)

            for conversation in current_bot_conversations:
                if not conversation.wired_conversation_id:
                    operator = conversation
                    return operator

        return False

    # pylint: disable=R1710, R0912
    def operator_forward(self, conversation, message):
        _logger.info(f'operator_forward {conversation.id}')
        # pylint: disable=R1702
        if conversation.dialog_id and \
                conversation.dialog_id.bots_type == 'is_communication_bot':
            _logger.info(f'269 forward')
            if not conversation.wired_conversation_id:
                conversation.last_step_id = self.id
                operators = self.bot_operators_id.operator_ids
                if self.bot_operators_id.operator_in_odoo_only:
                    # get operators only from Odoo UI
                    operators = operators.filtered(
                        lambda op: op.provider == 'odoo_livechat')
                operator = self.get_available_operator(
                    operators, conversation)
                if not operator:
                    text = conversation.dialog_id.with_context(
                        lang=conversation.sender_id.partner_id.lang).msg_after_not_found_operator

                    if not text:
                        return False

                    conversation.send_message(text=text)
                    return False

                operator.write({
                    'wired_conversation_id': conversation.id, })
                conversation.write({
                    'wired_conversation_id': operator.id, })
                if operator.user_id:
                    operator.open_popup_first_message()

                try:
                    text_msg = ''
                    conversation.is_customer_send = True
                    sender_name = conversation.sender_id.name
                    if conversation.chat_id.is_automatic_send_greet:
                        text_msg = conversation.dialog_id.with_context(
                            lang=conversation.sender_id.partner_id.lang).connect_operator_msg
                        conversation.send_message(
                            text=text_msg)

                    if conversation.chat_id.is_send_and_consultation:
                        text_msg = conversation.dialog_id.with_context(
                            lang=conversation.sender_id.partner_id.lang).msg_for_end_consultation
                        conversation.send_message(
                            text=text_msg)
                    if text_msg:
                        operator.send_message(
                            text=text_msg)
                    conversation.is_customer_send = True
                    operator.send_message(
                        text=f'{sender_name} '
                             f'need consultation')
                    conversation.is_customer_send = False

                except Exception as e:
                    _logger.info('Error in operator_forward')
                    _logger.debug(e)
                return conversation

    def get_available_operator(self, operators, conversation):
        omc_operators = operators.filtered(
            lambda x: x.user_saleperson_id and x.connect_only_to_my_clients)
        if omc_operators and conversation.sender_id.partner_id:
            sp_id = conversation.sender_id.partner_id.user_id
            omc_operators = omc_operators.filtered(
                lambda x: x.user_saleperson_id.id == sp_id.id)
            if omc_operators:
                return omc_operators
        operators = operators.filtered(
            lambda x: not x.connect_only_to_my_clients)
        filtered_operators = operators.filtered(
            lambda r: r.count_available_conversations > 0)
        sorted_operators = filtered_operators.sorted(
            reverse=True, key=lambda r: r.count_available_conversations)

        if sorted_operators:
            for sorted_operator in sorted_operators:
                current_operator = self.get_correct_operator_bot(
                    operator=sorted_operator)
                if current_operator:
                    return current_operator

        return False

    @api.onchange('step_type')
    def _compute_bots_ids(self):
        for obj in self:
            obj.bot_operators_ids = [(
                6, 0, self.env['kw.chatbot.dialog'].search([
                    ('bots_type', '=', 'is_consultant_bot')]).ids)]

    @api.model
    def create(self, vals_list):
        vals_list['name'] = vals_list.get('text')
        res = super(Step, self).create(vals_list)
        return res

    @api.depends('sequence')
    @api.onchange('sequence')
    def _compute_sequence(self):
        # when sequence change, change sequence in step
        for obj in self:
            if obj.sequence:
                obj.sequence = obj.sequence
            else:
                obj.sequence = 0

    # @api.depends('sequence')
    # @api.onchange('sequence')
    # def _compute_triggering_answer_ids(self):
    #     for step in self.filtered('triggering_answer_ids'):
    #         update_command = [Command.unlink(answer.id) for answer in
    #                           step.triggering_answer_ids
    #                           if
    #                           answer.dialog_step_id.sequence >=
    #                           step.sequence]
    #         if update_command:
    #             step.triggering_answer_ids = update_command

    # @api.onchange('triggering_answer_ids')
    # def _compute_aliases(self):
    #     for obj in self:
    #         obj.alias_ids = False
    #         for trig in obj.triggering_answer_ids:
    #             obj.alias_ids = [(0, 0, {'name': trig.name})]

    @api.onchange('answer_ids')
    def _compute_answer_odoo_livechat(self):
        for obj in self:
            obj.odoo_livechat_button_ids = False
            for ans in obj.answer_ids:
                obj.odoo_livechat_button_ids = [(0, 0, {'name': ans.name})]

    def odoo_livechat_button_start(self):
        self.ensure_one()
        alias = self.env['kw.chatbot.step.alias'].sudo(
        ).search([('name', '=', '/start'),
                  ('step_id', '=', self.id)], limit=1)
        text = self.name if alias else 'Start'
        return {'callback_data': '/start', 'name': text}

    def get_odoo_livechat_button(self, name, callback_data=False):
        self.ensure_one()
        if not callback_data:
            callback_data = name
        return {'callback_data': callback_data, 'name': name}

    def close_wired_conversation(self, conversation):
        self.ensure_one()
        conversation.wired_conversation_id.sudo(
        ).wired_conversation_id = False
        conversation.sudo(
        ).wired_conversation_id = False

    def get_offline_sender_mode(self, conversation):
        self.ensure_one()
        partner_id = self.env['res.partner'].search(
            [('id', '=', conversation.sender_id.odoo_livechat_id)])
        if partner_id:
            partner_id.sudo().kw_is_available_consultant = False

    def get_consultant_conversation_from_text(self, text):
        self.ensure_one()
        partner_id = int(text.split(' ')[1])
        consultant = self.env['kw.chatbot.sender'].sudo().search([
            ('odoo_livechat_id', '=', partner_id)], limit=1)
        consultant_conversation = self.env['kw.chatbot.conversation'].sudo(
        ).search([('chat_id.is_consultant_chat', '=', True),
                  ('sender_id', '=', consultant.id), ], limit=1)

        return consultant_conversation, consultant

    # odoo livechat
    def odoo_livechat_get_response(self, conversation, channel, message):
        self.ensure_one()
        # _logger.info('Step odoo_livechat_get_response communicate')
        text = message.get('body')
        if (self.name == text or self.env['kw.chatbot.step.alias'].sudo(
        ).search([('name', '=ilike', text),
                  ('step_id', '=', self.id)], limit=1)):
            markup = []
            if self.odoo_livechat_button_ids:
                for k in self.odoo_livechat_button_ids:
                    markup.append(k.get_odoo_livechat_button_markup())
            conversation.send_message(
                text=self.text,
                markup=markup)

    def odoo_livechat_close_wired_conversation(
            self, conversation, channel, message):
        # _logger.info('odoo_livechat_close_wired_conversation')
        self.ensure_one()
        markup = [self.get_odoo_livechat_button(
            _('Restart?'), '/start')]
        if conversation.wired_conversation_id:
            consult_conv = conversation.wired_conversation_id
            if consult_conv.chat_id.messenger_id.provider == 'odoo_livechat':
                consult_conv.send_message(
                    text=_('The consultation is over'), markup=markup, )
            self.close_wired_conversation(conversation)
            conversation.send_message(
                text=_('The consultation is over'), markup=markup, )
        return True

    def odoo_livechat_get_communicate(
            self, conversation, channel, message):
        self.ensure_one()
        # _logger.info('odoo_livechat_get_communicate')
        res_partner_ids = self.env['res.partner'].search([
            ('kw_is_consultant', '=', True),
            ('im_status', '=', 'online'),
            ('kw_is_available_consultant', '=', True)])
        if not res_partner_ids:
            conversation.send_message(
                text=_('There are currently no active consultants'))
            return True
        markup = []
        for partner in res_partner_ids:
            btn = self.get_odoo_livechat_button(
                partner.name,
                f'/begin_consultation {partner.id}')
            markup.append(btn)
        conversation.send_message(text=_('Choose a consultant'),
                                  markup=markup)
        return True

    def odoo_livechat_start_consultation(
            self, conversation, channel, message):
        # _logger.info('facebook_start_consultation')
        self.ensure_one()
        text = message.get('body')
        consultant_conversation, consultant = \
            self.get_consultant_conversation_from_text(text)
        if consultant_conversation:
            m = [self.get_odoo_livechat_button(
                name=_('Close the consultation'),
                callback_data='/close_wired_conversation')]
            consultant_conversation.send_message(
                text=_('Open consultation with the user'
                       ' (for others you offline)'), markup=m)
            conversation.sudo(
            ).wired_conversation_id = consultant_conversation.id
            consultant_conversation.sudo(
            ).wired_conversation_id = conversation.id
            self.get_offline_sender_mode(consultant_conversation)
        conversation.send_message(
            text=_(f'Consultant {consultant.name} joined,'
                   f' and will answer your question soon.'),
            markup=[self.get_odoo_livechat_button(
                _('Close the consultation'),
                '/close_wired_conversation')])
        return True

    def odoo_livechat_availability_consultant(
            self, conversation, channel, message):
        self.ensure_one()
        visitor = \
            conversation.mail_channel_id.channel_partner_ids.filtered(
                lambda x: not x.is_livechat_bot)
        if visitor and visitor.kw_is_consultant:
            markup = \
                [self.get_odoo_livechat_button(
                    _('Go Online'), '/set_consultant_ready'),
                    self.get_odoo_livechat_button(
                        _('Go Offline'), '/set_consultant_not_ready')]
            conversation.send_message(
                text=_('Do you want to start consulting??'), markup=markup)
        else:
            markup = [self.odoo_livechat_button_start()]
            conversation.send_message(
                text=_('This is consultant only chat. Plz wait '
                       'until admin approve you access'), markup=markup)
        return True

    def odoo_livechat_set_consultant_ready(
            self, conversation, channel, message):
        self.ensure_one()
        visitor = \
            conversation.mail_channel_id.channel_partner_ids.filtered(
                lambda x: not x.is_livechat_bot)
        visitor.kw_is_available_consultant = True
        conversation.send_message(text=_('You are being in online now'))
        return True

    def odoo_livechat_set_consultant_not_ready(
            self, conversation, channel, message):
        self.ensure_one()
        visitor = \
            conversation.mail_channel_id.channel_partner_ids.filtered(
                lambda x: not x.is_livechat_bot)
        visitor.kw_is_available_consultant = False
        conversation.send_message(text=_('You are being in offline now'))
        return True

    def chatbot_check_phone(self, conversation, phone):
        self.ensure_one()
        if len(phone) != 10 and len(phone) != 12:
            return False
        return True

    def chatbot_check_email(self, conversation, email):
        self.ensure_one()
        if len(email) < 4 or email[0] == '.' or email[-1] == '.' \
                or '.' not in email:
            return False
        return True

    def chatbot_add_partner(self, conversation, **kwargs):
        self.ensure_one()
        if conversation.sender_id.partner_phone:
            kw_partner_phone = conversation.sender_id.partner_phone
            partner_id = self.env['res.partner'].sudo().search([
                ('kw_phone_number_name', 'like', kw_partner_phone)], limit=1)
            if partner_id:
                return partner_id
            if conversation.sender_id.partner_email \
                    and conversation.sender_id.partner_name:
                partner_id = self.env['res.partner'].sudo().create({
                    'name': conversation.sender_id.partner_name,
                    'phone': kw_partner_phone, 'is_company': False,
                    'email': conversation.sender_id.partner_email, })
                return partner_id
        return False


class Dialog(models.Model):
    _inherit = 'kw.chatbot.dialog'

    chatbot_step_ids = fields.One2many(
        comodel_name='kw.chatbot.step', inverse_name='dialog_id')

    image_128 = fields.Image(
        "Image", max_width=128, max_height=128,
        compute='_compute_image_128', )

    bots_type = fields.Selection(selection_add=[
        ('is_communication_bot', 'Communication Bot'), ],
        ondelete={'is_communication_bot': 'set default'})
    communication_sender_ids = fields.Many2many(
        comodel_name='kw.chatbot.sender',
        compute='_compute_communication_senders')
    max_waiting_time = fields.Integer(
        default=10,
        help='Max waiting time in minutes for consultant '
             'to answer the question', )
    dialogue_end_time = fields.Integer(default=15, )
    msg_after_max_waiting_time = fields.Text(
        default='Thank you for contacting us. '
                'We will contact you as soon as possible.',
        translate=True,
        string='Message after max waiting time')
    wait_start_message = fields.Boolean(default=True, string='Wait for start message')
    send_msg_after_create_lead = fields.Boolean(default=True, string='Send message after create lead')

    def open_step_form_view(self):
        all_steps = self.chatbot_step_ids
        if all_steps:
            sequence = max(all_steps.mapped('sequence')) + 1
        else:
            sequence = 1
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'kw.chatbot.step',
            'view_mode': 'form',
            'res_id': False,
            'target': 'current',
            'context': {'default_dialog_id': self.id,
                        'default_sequence': sequence},
        }

    def send_thank_you_messages(self):

        _logger.info('send_thank_you_messages')
        # get all dialogs
        dialogs = self.env['kw.chatbot.dialog'].search([('bots_type', '=', 'is_communication_bot')])
        for dialog in dialogs:
            for conversation in dialog.conversations_ids:

                if not conversation.wired_conversation_id:
                    continue

                if conversation.is_closed:
                    continue
                last_activity_time = conversation.last_activity_datetime
                _logger.info('last_activity_time %s for conversation %s',
                             last_activity_time, conversation.id)
                if datetime.now() - last_activity_time > timedelta(minutes=dialog.max_waiting_time):
                    text = dialog.with_context(lang=conversation.sender_id.partner_id.lang).msg_after_max_waiting_time
                    conv_id = conversation.wired_conversation_id
                    subtype = self.env['mail.message.subtype'].search(
                        [('default', '=', True)], limit=1)
                    conversation.mail_channel_id.message_post(
                        author_id=conv_id.partner_id.id,
                        body=text,
                        message_type='comment',
                        subtype_id=subtype.id, )
                    # conversation.send_message(
                    #     text=text)
                    # conversation.last_activity_datetime = datetime.now()
                    conversation.is_closed = True

    @api.depends('conversations_ids')
    @api.onchange('conversations_ids')
    def _compute_communication_senders(self):
        for obj in self:
            obj.communication_sender_ids = [(5, 0, 0)]
            for con in obj.conversations_ids:
                obj.communication_sender_ids = [(4, con.sender_id.id)]

    def _compute_image_128(self):
        for odj in self:
            if odj.bots_type == 'is_communication_bot':
                image_path = modules.get_module_resource(
                    'kw_chatbot_builder', 'static/src/dialog_logo',
                    'is_communication_bot.png')
            else:
                image_path = modules.get_module_resource(
                    'kw_chatbot_builder', 'static/src/dialog_logo',
                    'is_consultant_bot.png')
            image = base64.b64encode(open(image_path, 'rb').read())
            odj.image_128 = image


class ChatbotDialogAnswer(models.Model):
    _name = 'chatbot.dialog.answer'

    name = fields.Char(required=True, translate=True, )
    sequence = fields.Integer(default=1, )
    redirect_link = fields.Char(
        help="The visitor will be redirected "
             "to this link upon clicking the option "
             "(note that the script will end if "
             "the link is external to the "
             "livechat website).", )
    dialog_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', string='Script Step',
        required=True, ondelete='cascade', )
    dialog_script_id = fields.Many2one(related='dialog_step_id.dialog_id')
    model_id = fields.Many2one('ir.model',
                               related='notification_id.model_id')
    model_name = fields.Char(related='model_id.model', )
    is_personal_data = fields.Boolean(default=False, )
    update_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Update field',
        domain="[('model_id', '=', 'res.partner'), ('name', 'in', ['name', 'email'])]", )
    is_used_new_domain = fields.Boolean(default=False, )
    extra_domain = fields.Char(
        help="Extra domain to filter records, "
             "for example: [('is_company', '=', True)]. If you select "
             "this domain, the domain from the notification will be ignored.")
    model_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Search by personal field', order='name')
    notification_id = fields.Many2one('kw.chatbot.notification', )
    refund_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', string='Go to step', )

    def name_get(self):
        if self._context.get('chatbot_dialog_answer_display_short_name'):
            return super().name_get()

        result = []
        for answer in self:
            # flake8: noqa: E501
            answer_message = answer.dialog_step_id.text.replace('\n', ' ') if answer.dialog_step_id.text else ' '
            shortened_message = textwrap.shorten(
                answer_message, width=26, placeholder=" [...]")
            result.append((
                answer.id,
                "%s: %s" % (shortened_message, answer.name)
            ))
        return result


class StepAlias(models.Model):
    _name = 'kw.chatbot.step.alias'
    _description = 'Step alias'

    name = fields.Char(
        required=True, string='Code', )
    active = fields.Boolean(
        default=True, )
    step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    dialog_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog', related='step_id.dialog_id',
        store=True, )
    dialog_answer_id = fields.Many2one(
        comodel_name='chatbot.dialog.answer', )


class StepMedia(models.Model):
    _name = 'kw.chatbot.step.media'
    _description = 'Step media'

    name = fields.Char(
        required=True, string='Code', )
    active = fields.Boolean(
        default=True, )
    media_type = fields.Selection(
        selection=[('video', 'Video'), ('image', 'Image')],
        default='image', required=True, )
    image_file = fields.Image("Step Image File")
    media_file = fields.Binary("Step Video File")
    step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    dialog_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog', related='step_id.dialog_id',
        store=True, )


class StepOdooLivechatButton(models.Model):
    _name = 'kw.chatbot.step.livechat.button'
    _description = 'Step odoo_livechat button'

    name = fields.Char(
        required=True, string='Code', )
    active = fields.Boolean(
        default=True, )
    step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    callback_data = fields.Char()

    def get_odoo_livechat_button_markup(self):
        self.ensure_one()
        return {'callback_data': self.callback_data, 'name': self.name}
