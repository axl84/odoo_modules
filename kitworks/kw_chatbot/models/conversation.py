import logging

import textwrap

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)

"""
Разговор - это каждая отдельная инициация диалога. Каждый разговор завершается
либо вместе с завершением диалога, либо при отключении пользователя
"""


class Conversation(models.Model):
    _name = 'kw.chatbot.conversation'
    _description = 'Conversation'
    _order = "display_name"

    name = fields.Char(
        required=True, string='Code', readonly=False, )
    display_name = fields.Char(
        compute='_compute_display_name', recursive=True,
        store=True, index=True)
    active = fields.Boolean(
        default=True, )
    is_closed = fields.Boolean(
        default=False, )
    last_activity_datetime = fields.Datetime(
        string='Last activity', )
    chat_id = fields.Many2one(
        comodel_name='kw.chatbot.chat', required=True, )
    dialog_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog', )
    chatbot_message_ids = fields.One2many(
        comodel_name='kw.chatbot.message', inverse_name='conversation_id', )
    chatbot_message_id = fields.Many2one(
        comodel_name='kw.chatbot.message', )
    sender_id = fields.Many2one(
        comodel_name='kw.chatbot.sender', )
    data = fields.Text()
    question_ids = fields.One2many(
        comodel_name='kw.chatbot.input.question',
        inverse_name='conversation_id', )
    is_personal = fields.Boolean(default=False, )

    odoo_livechat_id = fields.Integer()

    mail_channel_id = fields.Many2one(comodel_name='discuss.channel')

    is_creation_awaiting = fields.Boolean()

    partner_id = fields.Many2one(
        comodel_name='res.partner', related='sender_id.partner_id')
    user_id = fields.Many2one(
        comodel_name='res.users', related='sender_id.user_id')

    is_odoo_livechat_send = fields.Boolean()

    lint_tracker_id = fields.Many2one(
        comodel_name='link.tracker', )
    utm_campaign = fields.Char(
        related='lint_tracker_id.campaign_id.name', )
    utm_medium = fields.Char(
        related='lint_tracker_id.medium_id.name', )
    utm_source = fields.Char(
        related='lint_tracker_id.source_id.name', )

    operator_live_id = fields.Many2one(comodel_name='res.users')
    is_consult_with_odoo = fields.Boolean(
        default=False, )

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        related='dialog_id.company_id')

    chat_history = fields.Html(compute='_compute_chat_history')

    @api.depends('chatbot_message_ids')
    def _compute_chat_history(self):
        chat_history = ""
        for message in self.chatbot_message_ids:
            if message.is_bot_message:
                chat_history += "<div style='background-color: " \
                                "#F5F5F5; color: #000000; text-align: right;" \
                                " padding: 5px; margin-bottom: 5px;'>"
            else:
                chat_history += "<div style='background-color:" \
                                " #333333; color: #FFFFFF; text-align: left;" \
                                " padding: 5px; margin-bottom: 5px;'>"

            chat_history += "<span style='font-weight:" \
                            " bold;'>{}" \
                            "</span><br>".format(message.sender_id.name)
            chat_history += "<span style='font-size: " \
                            "small;'>{}</span><br>".format(message.create_date)
            chat_history += message.text if message.text else ""
            chat_history += "</div>"

        self.chat_history = chat_history

    @staticmethod
    def _get_create_date_from_partner(partner):
        return partner['create_date']

    # flake8: noqa: E501
    def merge_contact_by_phone_number(self, mobile):
        if self.partner_id:

            clean_mobile = mobile
            mobile_field_name = 'mobile'
            phone_field_name = 'phone'

            res_partner_fields = self.env['res.partner']._fields
            is_res_partner_has_cleaned_field = 'kw_mobile_cleaned' in res_partner_fields and \
                                               'kw_phone_cleaned' in res_partner_fields
            mobile_without_symbols = ''.join(filter(str.isnumeric, mobile))

            if mobile_without_symbols and is_res_partner_has_cleaned_field:
                mobile_field_name = 'kw_mobile_cleaned'
                phone_field_name = 'kw_phone_cleaned'
                clean_mobile = mobile_without_symbols

            p_by_m = self.env['res.partner'].search([(
                f'{mobile_field_name}', 'ilike', clean_mobile)])
            p_by_p = self.env['res.partner'].search([
                ('id', 'not in', p_by_m.ids),
                (f'{phone_field_name}', 'ilike', clean_mobile)])
            partner_ids = p_by_m + p_by_p
            if partner_ids:

                partner_ids = sorted(partner_ids, key=self._get_create_date_from_partner)
                partner_ids_for_merge = partner_ids[0] + partner_ids[-1]

                m = self.env['base.partner.merge.automatic.wizard'].sudo()
                m = m.with_context(
                    default_dst_partner_id=partner_ids[0],
                    default_partner_ids=[(6, 0, partner_ids_for_merge.ids)]
                ).create({})
                m.action_merge()
                self.sender_id.partner_id = partner_ids[0].ids[0]

    def write(self, vals_list):
        """
        When all dialogues are archived and the Consultant
        bot is active - the channels will be resumed
        """
        res = super(Conversation, self).write(vals_list)

        if 'active' not in vals_list.keys():
            return res

        # archive process here
        if not vals_list['active']:
            for obj in self:
                is_consultant = obj.env.user.is_chatbot_consultant
                is_bot_type_consultant = \
                    obj.dialog_id.bots_type == 'is_consultant_bot'

                if is_consultant and is_bot_type_consultant:
                    obj.dialog_id.action_quit()
                    obj.dialog_id.action_join()

        return res

    def _compute_display_name(self):
        for obj in self:
            if obj.sender_id:
                obj.display_name = obj.sender_id.name
            else:
                obj.display_name = obj.name

    def name_get(self):
        if self._context.get(
                'chatbot_chat_bot_conversation_display_short_name'):
            return super().name_get()
        result = []
        for conv in self:
            chat_name = conv.chat_id.name.replace('\n', ' ')
            name_chat = textwrap.shorten(
                chat_name, width=26, placeholder=" [...]")
            if conv.sender_id:
                sender_name = conv.sender_id.name.replace('\n', ' ')
                name_sender = textwrap.shorten(
                    sender_name, width=26, placeholder=" [...]")
                result.append((
                    conv.id, "%s | Chat: %s " % (
                        name_sender, name_chat,)))
            else:
                result.append((
                    conv.id, "Chat: %s [%s]" % (name_chat, conv.name,)))
        return result

    def livechat_open_popup(self, mail_channel, state, partner_id):
        if not mail_channel:
            raise exceptions.ValidationError(
                _('Mail Channel not found'))
        self.env['bus.bus']._sendone(
            partner_id, 'discuss.Thread/fold_state',
            {'id': mail_channel.id,
             'foldStateCount': 10,
             'model': 'discuss.channel',
             'fold_state': state, })

    def livechat_open_and_subscribe_button(self):
        mail_channel = self.env['discuss.channel'].search([
            ("conversation_id", '=', self.id)], limit=1)
        mail_partner = self.env['discuss.channel.member'].sudo()
        mail_operator_id = mail_partner.search([
            ('channel_id', '=', mail_channel.id),
            ('partner_id', '=', self.env.user.partner_id.id), ], limit=1)
        if self.is_consult_with_odoo and not mail_operator_id:
            mail_operator_id = mail_partner.create({
                'channel_id': mail_channel.id, 'is_bot_operator': True,
                'partner_id': self.env.user.partner_id.id, })
            mail_channel.channel_pin(pinned=True)
        if mail_operator_id:
            if mail_channel:
                self.livechat_open_popup(
                    mail_channel=mail_channel, state='open',
                    partner_id=self.env.user.partner_id, )

    def get_or_create_partner(self, sender_id, company_id=False):
        if sender_id.partner_id:
            return sender_id.partner_id
        partner_id = self.env['res.partner'].sudo().create({
            'name': sender_id.name})
        if company_id:
            partner_id.write({'company_id': company_id.id, })
        if self.chat_id and self.chat_id.default_contact_lang:
            partner_id.write({'lang': self.chat_id.default_contact_lang})
        sender_id.write({'partner_id': partner_id.id})
        return partner_id

    def connect_live_chat(self, text=None, attachment=None):
        if self.dialog_id and self.dialog_id.bots_type == 'is_consultant_bot':
            self.is_consult_with_odoo = True
            operator = self.dialog_id.user_ids.search([
                ('is_chatbot_consultant', '=', True), ], limit=1)
            mail_channel = self.env['discuss.channel'].search(
                [("conversation_id", '=', self.id)],
                limit=1)
            if not mail_channel:
                mail_channel = self.env['discuss.channel'].create(
                    {'name': self.sender_id.name,
                     'conversation_id': self.id,
                     'channel_type': 'group'})
                if self.dialog_id.is_partner:
                    self.get_or_create_partner(
                        sender_id=self.sender_id,
                        company_id=self.chat_id.company_id)
                    self.env['discuss.channel.member'].sudo().create({
                        'channel_id': mail_channel.id,
                        'partner_id': self.partner_id.id})
            mail_operator_id = self.env['discuss.channel.member'].search([
                ('channel_id', '=', mail_channel.id),
                ('partner_id', '=', operator.partner_id.id), ],
                limit=1)
            if not mail_operator_id and operator:
                self.env['discuss.channel.member'].create({
                    'channel_id': mail_channel.id, 'is_bot_operator': True,
                    'partner_id': operator.partner_id.id, })
                if self.chat_id.is_automatic_send_greet:
                    self.send_message('{} {}'.format(
                        operator.name,
                        self.dialog_id.with_context(
                            lang=self.sender_id.partner_id.lang
                        ).connect_operator_msg))
            if attachment:
                return self.livechat_send_file(
                    mail_channel=mail_channel, attachment=attachment)
            return self.livechat_send_message(
                mail_channel=mail_channel, text=text)
        return False

    def livechat_send_file(self, mail_channel, attachment):
        subtype = self.env['mail.message.subtype'].search(
            [('default', '=', True)], limit=1)
        mail_channel_id = mail_channel.with_context(
            mail_create_nosubscribe=True,
            mail_post_autofollow=True,
            content_type='text/html;charset=utf-8')
        if self.dialog_id.is_partner:
            self.get_or_create_partner(
                sender_id=self.sender_id,
                company_id=self.chat_id.company_id)
        livechat_mess_id = mail_channel_id.message_post(
            author_id=self.partner_id.id,
            attachment_ids=attachment.ids,
            message_type='comment',
            subtype_id=subtype.id, )
        return livechat_mess_id

    def livechat_send_message(self, mail_channel, text):
        subtype = self.env['mail.message.subtype'].search(
            [('default', '=', True)], limit=1)
        mail_channel_id = mail_channel.with_context(
            mail_create_nosubscribe=True,
            mail_post_autofollow=True,
            content_type='text/html;charset=utf-8')
        if self.dialog_id.is_partner:
            self.get_or_create_partner(
                sender_id=self.sender_id,
                company_id=self.chat_id.company_id)
        livechat_mess_id = mail_channel_id.message_post(
            author_id=self.partner_id.id,
            body=text,
            message_type='comment',
            subtype_id=subtype.id, )
        return livechat_mess_id

    def create_live_chat_channel(self, partner_id):
        mail_channel = self.env['discuss.channel'].search(
            [("conversation_id", '=', self.id)],
            limit=1)
        if not mail_channel:
            mail_channel = self.env['discuss.channel'].create(
                {'name': partner_id.name,
                 'conversation_id': self.id,
                 'channel_type': 'group'})
            self.env['discuss.channel.member'].create({
                'channel_id': mail_channel.id, 'is_bot_operator': True,
                'partner_id': partner_id.id, })
            mail_channel.channel_pin(pinned=True)
            self.write({'mail_channel_id': mail_channel.id})
        return mail_channel

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'odoo_livechat':
            return _logger.debug(text, kwargs)
        if self.mail_channel_id:
            self.is_odoo_livechat_send = True
            res_bot = self.mail_channel_id.channel_partner_ids.filtered(
                lambda x: x.is_livechat_bot)
            button = False
            if kwargs.get('markup'):
                button = self.get_html_button(kwargs.get('markup'))
            subtype = self.env['mail.message.subtype'].search(
                [('default', '=', True)], limit=1)
            self.mail_channel_id.with_context(
                mail_create_nosubscribe=True,
                content_type='text/html;charset=utf-8').message_post(
                author_id=res_bot.id,
                body=text,
                button=button,
                message_type='comment',
                subtype_id=subtype.id)
        return None

    def send_file(self, files, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'odoo_livechat':
            return _logger.debug(files, kwargs)
        if self.mail_channel_id:
            self.is_odoo_livechat_send = True
            res_bot = self.mail_channel_id.channel_partner_ids.filtered(
                lambda x: x.is_livechat_bot)
            subtype = self.env['mail.message.subtype'].search(
                [('default', '=', True)], limit=1)
            for file in files:
                file.res_model = 'mail.compose.message'
            self.mail_channel_id.with_context(
                mail_create_nosubscribe=True).message_post(
                author_id=res_bot.id,
                attachment_ids=files.ids,
                message_type='comment',
                subtype_id=subtype.id)
        return None

    def get_html_button(self, markup):
        self.ensure_one()
        html = ''
        for btn in markup:
            html += '<div><button type="button" channel-index="{}"' \
                    ' callback-value="{}" class="btn btn-primary ' \
                    'js_chatbot_button_handle' \
                    '">{}</button></div><br>'.format(self.mail_channel_id.id,
                                                     btn.get('callback_data'),
                                                     btn.get('name'))
        return html

    def odoo_livechat_create_log(self, name=False, body=False):
        self.ensure_one()
        self.env['kw.chatbot.log'].create({
            'name': name,
            'messenger_id': self.chat_id.messenger_id.id,
            'body': body,
            'chat_id': self.chat_id.id,
            'dialog_id': self.dialog_id.id,
            'sender_id': self.sender_id.id,
            'conversation_id': self.id,
        })

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'odoo_livechat':
            return _logger.debug(chat, kwargs)
        sender = kwargs.get('sender')
        if not sender:
            raise ValueError('Cant process: "sender_id" not provided')
        conversation = self.sudo().search([
            ('sender_id', '=', sender.id),
            ('company_id', '=', chat.company_id.id),
            ('chat_id', '=', chat.id)], limit=1)
        if not conversation:
            conversation = self.sudo().create({
                'name': sender.odoo_livechat_id,
                'dialog_id': chat.dialog_id.id,
                'company_id': chat.company_id.id,
                'sender_id': sender.id,
                'chat_id': chat.id, })
        return conversation

    def odoo_livechat_get_response(self, channel, message):
        self.ensure_one()
        # _logger.info('Conversation odoo_livechat_get_response')
        # _logger.info(message)
        self.is_odoo_livechat_send = False
        # for step in self.dialog_id.chatbot_step_ids:
        #     if step.odoo_livechat_get_response(
        #             conversation=self, channel=channel, message=message):
        #         break
        if not self.is_odoo_livechat_send:
            self.odoo_livechat_does_not_found()

    def odoo_livechat_does_not_found(self):
        self.ensure_one()
        self.send_message(
            text=_('Unable to find anything for your query = ('))


class Message(models.Model):
    _name = 'kw.chatbot.message'
    _description = 'Conversation'

    name = fields.Char(
        string='Code', default='Message')
    active = fields.Boolean(
        default=True, )
    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', )
    text = fields.Text()

    sender_id = fields.Many2one(
        comodel_name='kw.chatbot.sender', )
    is_bot_message = fields.Boolean(
        default=False, )
    is_dialog_message = fields.Boolean(
        default=False, )
    is_call_back_message = fields.Boolean(
        default=False, )
    is_double_message = fields.Boolean(
        default=False, )
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment', )

    odoo_livechat_id = fields.Char()

    raw_json = fields.Text()
    kw_parent_id = fields.Many2one(
        'kw.chatbot.message', 'Parent Message')
    needed_for_lead = fields.Boolean(
        default=True, )


class InputQuestion(models.Model):
    _name = 'kw.chatbot.input.question'
    _description = 'Conversation Question'

    question = fields.Char()
    answer = fields.Char()
    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation')
