import logging

from datetime import datetime, timedelta
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    last_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    input_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    wired_conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', )
    is_customer_send = fields.Boolean(
        default=False, )

    button_res_id = fields.Integer()
    button_model = fields.Char()

    write_field = fields.Char()
    write_field_type = fields.Char()
    write_field_relation = fields.Char()

    is_record_write = fields.Boolean(
        default=False, )
    last_notification_id = fields.Many2one(
        comodel_name='kw.chatbot.notification', )

    model_activity_ids = fields.One2many(
        comodel_name='kw.chatbot.model.activity',
        inverse_name='conversation_id', )

    is_no_reply = fields.Boolean(
        compute='_compute_is_no_reply',
        store=True,
    )

    @api.depends('wired_conversation_id')
    def _compute_is_no_reply(self):
        """
        Uncheck this box when the operator has answered in the conversation
        """
        for record in self:
            if record.wired_conversation_id:
                record.is_no_reply = False

    # pylint: disable=R1719
    def _is_chatbot_statistics_installed(self):
        """
        Check for 'kw_chatbot_statistics' module is installed
        """
        module_statistics = self.env['ir.module.module'].search(
            [('name', '=', 'kw_chatbot_statistics')], limit=1
        )

        if not module_statistics:
            return False

        return True if module_statistics.state == 'installed' else False

    def set_evaluation(self, evaluation=0):
        """
        Set evaluation method for UI Odoo code run in step button
        """
        if not self._is_chatbot_statistics_installed():
            return False

        if not evaluation:
            return False

        if not (self and
                self.chat_id and
                self.dialog_id and
                self.sender_id):
            return False

        statistic_record = self.env['kw.chatbot.operator.activity'].search([
            ('chat_id', '=', self.chat_id.id),
            ('dialog_id', '=', self.dialog_id.id),
            ('conversation_id', '=', self.id),
            ('sender_id', '=', self.sender_id.id)
        ], order='date_start desc', limit=1)

        if not statistic_record:
            return False

        statistic_record.evaluation = evaluation

        return True

    # pylint: disable=R0912,R0915,R0911
    def write(self, vals):
        """
        When adding an operator, a new record is created in the statistics
        """
        result = super(Conversation, self).write(vals)

        # [Important] -> Skip if module 'kw_chatbot_statistics' not installed
        if not self._is_chatbot_statistics_installed():
            return result

        # Skip if an operator is not added
        if 'wired_conversation_id' not in vals:
            return result

        # Skip if the current dialog of the operator
        if self.dialog_id.bots_type == 'is_consultant_bot':
            return result

        # Skip if sender of this conversation is admin
        if self.sender_id.is_chatbot_consultant:
            return result

        # Skip if the operator disconnects from the dialog
        if not vals.get('wired_conversation_id'):
            return result

        # Get wired conversation for get operator
        wired_id = int(vals.get('wired_conversation_id'))
        wired_conv_id = self.env['kw.chatbot.conversation'].browse(wired_id)

        # Skip if not operator
        if not wired_conv_id:
            return result

        operator_id = wired_conv_id.partner_id
        chat_id = self.chat_id
        dialog_id = self.dialog_id
        conv_id = self
        sender_id = self.sender_id
        date_start = fields.Datetime.now()

        # Skip if record is already created
        if not self._is_statistic_record_not_created_yet(operator_id=operator_id,
                                                         chat_id=chat_id,
                                                         dialog_id=dialog_id,
                                                         conversation_id=conv_id,
                                                         sender_id=sender_id):
            return result

        try:
            self.env['kw.chatbot.operator.activity'].create({
                'operator_id': operator_id.id if operator_id else False,
                'chat_id': chat_id.id if chat_id else False,
                'dialog_id': dialog_id.id if dialog_id else False,
                'conversation_id': conv_id.id if conv_id else False,
                'sender_id': sender_id.id if sender_id else False,
                'date_start': date_start if date_start else False,
            })

        except Exception as e:
            _logger.error(f"Failed to create operator activity: {e}")

        return result

    def _is_statistic_record_not_created_yet(self,
                                             operator_id=False,
                                             chat_id=False,
                                             dialog_id=False,
                                             conversation_id=False,
                                             sender_id=False):
        """
        Return True if statistic record not created by this values
        """
        # [Important] -> Skip if module 'kw_chatbot_statistics' not installed
        if not self._is_chatbot_statistics_installed():
            return False

        if not (operator_id and chat_id and dialog_id and conversation_id and
                sender_id):
            return False

        statistic_record = self.env['kw.chatbot.operator.activity'].search([
            ('operator_id', '=', operator_id.id),
            ('chat_id', '=', chat_id.id),
            ('dialog_id', '=', dialog_id.id),
            ('conversation_id', '=', conversation_id.id),
            ('sender_id', '=', sender_id.id),
            ('date_end', '=', False)
        ], order='date_start desc', limit=1)

        if statistic_record:
            return False

        return True

    def get_record(self):
        self.ensure_one()
        return self.env[self.button_model].sudo().search(
            [('id', '=', self.button_res_id)], limit=1)

    def leave_mail_channel(self):
        for obj in self:
            if (not obj.wired_conversation_id and obj.mail_channel_id
                    and obj.chat_id.messenger_id.provider != 'odoo_livechat'):
                partners = obj.mail_channel_id.channel_member_ids
                # temporary comment about fix leave from chat by /end because in v16 we can't change channel_type
                # if len(partners) > 2:
                #     obj.mail_channel_id.channel_type = 'group'
                unfollow_partners = partners.filtered(
                    lambda x: x.partner_id != obj.partner_id)
                for p_id in unfollow_partners:
                    self.env.user = p_id.partner_id.user_id
                    obj.livechat_open_popup(
                        mail_channel=obj.mail_channel_id,
                        state='closed',
                        partner_id=p_id.partner_id)
                    obj.mail_channel_id.execute_command_leave()

    def livechat_open_and_subscribe_button(self):
        if self.is_consult_with_odoo:
            return super(
                Conversation, self).livechat_open_and_subscribe_button()
        mail_channel = self.env['discuss.channel'].search([
            ("conversation_id", '=', self.id)], limit=1)
        if mail_channel:
            mail_partner = self.env['discuss.channel.member'].sudo()
            mail_operator_id = mail_partner.search([
                ('channel_id', '=', mail_channel.id),
                ('partner_id', '=', self.env.user.partner_id.id), ], limit=1)
            if not mail_operator_id:
                mail_partner.create({
                    'channel_id': mail_channel.id, 'is_bot_operator': True,
                    'partner_id': self.env.user.partner_id.id, })
                # channel = mail_channel.channel_info()
                # mail_channel.channel_pin(
                #     uuid=channel[0].get('uuid'), pinned=True)
                mail_channel.channel_pin(pinned=True)
            conversation = self.env['kw.chatbot.conversation'].search([
                ('partner_id', '=', self.env.user.partner_id.id)])
            if self.chat_id.provider == 'odoo_livechat':
                raise exceptions.ValidationError(
                    _('Wait for {} finish conversation').format(
                        self.sender_id.name))
            if self.wired_conversation_id and conversation or \
                    self.partner_id.id == self.env.user.partner_id.id:
                if self.wired_conversation_id.partner_id.id \
                        == self.env.user.partner_id.id:
                    self.livechat_open_popup(
                        mail_channel=mail_channel, state='open',
                        partner_id=self.env.user.partner_id, )
                else:
                    raise exceptions.ValidationError(
                        _('Wait for {} finish conversation').format(
                            self.sender_id.name))
            conversation = conversation.filtered(
                lambda f: f.chat_id.provider == 'odoo_livechat')
            if not conversation:
                raise exceptions.ValidationError(
                    _('You are not the operator of any of the dialogue'))
            conversation = conversation[0]
            if conversation:
                conversation.write({
                    'wired_conversation_id':
                        mail_channel.conversation_id.id, })
                conversation.sender_id.is_ready_for_consult = False
                mail_channel.conversation_id.write({
                    'wired_conversation_id': conversation.id, })

        mail_channel.channel_pin(pinned=True)
        mail_channel.channel_fold(state='open', state_count=10)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def odoo_livechat_does_not_found(self):
        if not self.wired_conversation_id and \
                not self.chat_id.is_consultant_chat:
            return super(Conversation, self).odoo_livechat_does_not_found()
        return False

    def odoo_livechat_out_message(self, text=False):
        if not self.wired_conversation_id:
            return super(Conversation, self).odoo_livechat_out_message(
                text=text)
        return False

    def completion_consultation_for_time(self):
        for obj in self.env['kw.chatbot.conversation'].search(
                [('last_activity_datetime', '!=', False)]):
            time = obj.dialog_id.dialogue_end_time

            correct_time = self._get_correct_time_end(conversation=obj)
            # set time from step-bot settings
            if correct_time:
                time = correct_time

            if obj.last_activity_datetime <= \
                    (datetime.today() - timedelta(minutes=time)) \
                    and obj.wired_conversation_id:
                obj.wired_conversation_id = False
                obj.leave_mail_channel()
            if obj.last_activity_datetime <= \
                    (datetime.today() - timedelta(minutes=time)) \
                    and obj.operator_live_id:
                w_c = obj.operator_live_id.wired_conversation_id
                if w_c:
                    obj.operator_live_id.wired_conversation_id = False
                    w_c.leave_mail_channel()
                obj.operator_live_id = False

    @staticmethod
    def _get_correct_time_end(conversation=False):
        """
        Get correct time for end dialogue by operator side
        """
        if not (conversation and conversation.sender_id and
                conversation.wired_conversation_id and
                conversation.wired_conversation_id.dialog_id):
            return False

        # Get end dialogue time from user dialog settings
        if conversation.sender_id.is_chatbot_consultant:
            wired_conversation = conversation.wired_conversation_id
            time = wired_conversation.dialog_id.dialogue_end_time
            return time

        return False

    def open_popup_first_message(self):
        self.ensure_one()
        if self.user_id and self.wired_conversation_id:
            self.env.user = self.user_id
            mail_partner = self.env['discuss.channel.member'].sudo()
            mail_channel_id = self.wired_conversation_id.mail_channel_id
            if mail_channel_id:
                mail_operator_id = mail_partner.search([
                    ('channel_id', '=', mail_channel_id.id),
                    ('partner_id', '=',
                     self.env.user.partner_id.id), ],
                    limit=1)
                if not mail_operator_id:
                    mail_partner.create({
                        'channel_id': mail_channel_id.id,
                        'is_pinned': True,
                        'partner_id': self.env.user.partner_id.id, })

                mail_channel_id.channel_pin(pinned=True)
                mail_channel_id.channel_fold(state='open')

    def send_message(self, text, **kwargs):
        self.ensure_one()
        button = False
        if self.chat_id.messenger_id.provider == 'odoo_livechat' and \
                self.wired_conversation_id:
            conversation = self.wired_conversation_id
            mail_channel = conversation.mail_channel_id
            author_id = conversation.sender_id.partner_id
            operator = self.env['discuss.channel.member'].search([
                ('channel_id', '=', mail_channel.id),
                ('partner_id', '=', self.sender_id.partner_id.id)])
            if not operator:
                self.env['discuss.channel.member'].create({
                    'channel_id': mail_channel.id, 'is_bot_operator': True,
                    'partner_id': self.sender_id.partner_id.id, })
                # channel = mail_channel.channel_info()
                # mail_channel.channel_pin(
                #     uuid=channel[0].get('uuid'), pinned=True)
                mail_channel.channel_pin(pinned=True)
            subtype = self.env['mail.message.subtype'].search(
                [('default', '=', True)], limit=1)
            if mail_channel:
                mail_channel.with_context(
                    mail_create_nosubscribe=True,
                    content_type='text/html;charset=utf-8').message_post(
                    author_id=author_id.id if author_id else False,
                    body=text, button=button,
                    message_type='comment',
                    subtype_id=subtype.id, **kwargs)
            return None
        return super(Conversation, self).send_message(text, **kwargs)

    def send_file(self, files, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider == 'odoo_livechat' and \
                self.wired_conversation_id:
            conversation = self.wired_conversation_id
            mail_channel = conversation.mail_channel_id
            author_id = conversation.sender_id.partner_id
            operator = self.env['discuss.channel.member'].search([
                ('channel_id', '=', mail_channel.id),
                ('partner_id', '=', self.sender_id.partner_id.id)])
            if not operator:
                self.env['discuss.channel.member'].create({
                    'channel_id': mail_channel.id, 'is_bot_operator': True,
                    'partner_id': self.sender_id.partner_id.id, })
                # channel = mail_channel.channel_info()
                # mail_channel.channel_pin(
                #     uuid=channel[0].get('uuid'), pinned=True)
                mail_channel.channel_pin(pinned=True)
            subtype = self.env['mail.message.subtype'].search(
                [('default', '=', True)], limit=1)
            for file in files:
                file.res_model = 'mail.compose.message'
            mail_channel.with_context(
                mail_create_nosubscribe=True).message_post(
                author_id=author_id.id if author_id else False,
                attachment_ids=files.ids,
                message_type='comment',
                subtype_id=subtype.id)
            return None
        return super(Conversation, self).send_file(files, **kwargs)


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    # pylint: disable=R0912,R0915,R0914
    @api.model
    def create(self, vals_list):
        obj = super().create(vals_list)
        data_send = {}
        if obj.is_double_message:
            return obj

        message_owner, statistic_conversation = self._get_user_conversation_for_statistics(message=obj)
        # get current statistic for update info
        statistic_record = self._get_available_statistic_record(statistic_conversation=statistic_conversation)

        if obj.conversation_id.wired_conversation_id:
            # set if admin answered
            if message_owner and message_owner['owner'] == 'admin':
                self._set_is_answer(statistic_record=statistic_record)
                self._set_first_answer_date(statistic_record=statistic_record)

            # set last message owner
            if message_owner:
                self._set_who_answered_last(statistic_record=statistic_record,
                                            sender=message_owner['owner'])

        if obj.conversation_id.wired_conversation_id and obj.text != '/end':
            message = obj.text
            chat = obj.conversation_id.chat_id
            mess_text = message
            wired_conv_chat = obj.conversation_id.wired_conversation_id.chat_id
            if chat.is_send_operator_name or wired_conv_chat.is_send_operator_name:
                mess_text = '{}: {}'.format(
                    obj.conversation_id.sender_id.name, message)
            wired_conv = obj.conversation_id.wired_conversation_id
            if chat.provider != 'odoo_livechat' \
                    and wired_conv.chat_id.provider == 'odoo_livechat':
                obj.conversation_id.is_customer_send = True
                mess_text = message
            if not obj.conversation_id.wired_conversation_id.is_customer_send:
                if not obj.attachment_ids:
                    if mess_text:
                        if obj.kw_parent_id:
                            # flake8: noqa
                            data_send = obj.conversation_id.wired_conversation_id.send_message(
                                text=mess_text, **{
                                    'kw_parent_id': obj.kw_parent_id.id,
                                    'id_reply': obj.kw_parent_id.name})
                            # empty parent_id
                            obj.kw_parent_id = False
                        else:
                            # flake8: noqa
                            data_send = obj.conversation_id.wired_conversation_id.send_message(
                                text=mess_text)
                else:
                    chat = obj.conversation_id.wired_conversation_id.chat_id
                    if chat.provider != 'odoo_livechat' and mess_text:
                        obj.conversation_id.wired_conversation_id.send_message(
                            text=mess_text)
                    obj.conversation_id.wired_conversation_id.send_file(
                        files=obj.attachment_ids)
                obj.write({
                    'sender_id': obj.conversation_id.sender_id.id, })
                if data_send and isinstance(data_send, dict):
                    obj.write(data_send)
            obj.conversation_id.wired_conversation_id.is_customer_send = False
            return obj
        vals_list_wired = vals_list.copy()
        conv_id = obj.conversation_id
        if conv_id.wired_conversation_id:
            vals_list_wired['conversation_id'] = \
                conv_id.wired_conversation_id.id
            vals_list_wired['is_dialog_message'] = True
            obj.is_dialog_message = True
            if obj.text == '/end':
                if conv_id.chat_id.provider == 'odoo_livechat':
                    conv_id.send_message(
                        text=conv_id.wired_conversation_id.dialog_id.with_context(
                            lang=conv_id.wired_conversation_id.sender_id.partner_id.lang).end_consultation_msg)
                    conv_id.sender_id.is_ready_for_consult = True
                    wired_conversation_id = conv_id.wired_conversation_id
                    conv_id.wired_conversation_id.wired_conversation_id = False
                    conv_id.wired_conversation_id = False
                    conv_id.is_closed = True
                    for c in [wired_conversation_id, conv_id]:
                        c.leave_mail_channel()
                else:
                    conv_id.is_customer_send = True
                    dialog_msg_id = conv_id.wired_conversation_id.dialog_id
                    sender_id = conv_id.wired_conversation_id.sender_id
                    conv_id.is_closed = True
                    conv_id.wired_conversation_id.send_message(
                        text=dialog_msg_id.with_context(
                            lang=conv_id.sender_id.partner_id.lang).end_consultation_msg)
                    conv_id.send_message(
                        text=conv_id.dialog_id.with_context(
                            lang=conv_id.sender_id.partner_id.lang).end_consultation_msg)
                    sender_id.is_ready_for_consult = True
                    wired_conversation_id = conv_id.wired_conversation_id
                    conv_id.wired_conversation_id.wired_conversation_id = False
                    conv_id.wired_conversation_id = False
                    conv_id.is_closed = True
                    for c in [wired_conversation_id, conv_id]:
                        c.leave_mail_channel()

                # set date finished dialogue by operator for statistics
                self._set_date_end(statistic_record=statistic_record)

        return obj

    # pylint: disable=R1719
    def _is_chatbot_statistics_installed(self):
        """
        Check for 'kw_chatbot_statistics' module is installed
        """
        module_statistics = self.env['ir.module.module'].search(
            [('name', '=', 'kw_chatbot_statistics')], limit=1
        )

        if not module_statistics:
            return False

        return True if module_statistics.state == 'installed' else False

    # pylint: disable=R0912,R0915
    def _get_user_conversation_for_statistics(self, message=False):
        """
        Get last fully correct statistic record for write new info

        Returns:
            tuple: A tuple containing:
                - bool: True if the message sender - admin, False - user.
                - kw.chatbot.conversation: The user conversation
        """
        # skip in module 'kw_chatbot_statistics' is not installed
        if not self._is_chatbot_statistics_installed():
            return False, False

        # 'admin' or 'user' or False
        message_owner = {
            'owner': False,
        }

        # Skip if not correct message
        if not message:
            return message_owner, False

        # Skip if this message not from real user or real admin
        if (message.is_call_back_message and
                not message.sender_id.is_chatbot_consultant):
            return message_owner, False

        # Skip if this message is first in this dialogue
        if not message.conversation_id.wired_conversation_id:
            return message_owner, False

        # Set owner message info
        message_owner['owner'] = 'admin' if message.sender_id.is_chatbot_consultant else 'user'

        conv = message.conversation_id
        wired_conv = message.conversation_id.wired_conversation_id

        # Skip if conv or wired_conv is missing
        if not conv or not wired_conv:
            return message_owner, False

        # Set user conversation
        conversation = conv if message_owner['owner'] == 'user' else wired_conv

        return message_owner, conversation

    def _get_available_statistic_record(self, statistic_conversation=False):
        """
        Get current statistic record for update info
        """
        # skip in module 'kw_chatbot_statistics' is not installed
        if not self._is_chatbot_statistics_installed():
            return False

        if not (statistic_conversation and
                statistic_conversation.wired_conversation_id and
                statistic_conversation.wired_conversation_id.partner_id and
                statistic_conversation.chat_id and
                statistic_conversation.dialog_id and
                statistic_conversation.sender_id):
            return False

        operator_id = statistic_conversation.wired_conversation_id.partner_id
        chat_id = statistic_conversation.chat_id
        dialog_id = statistic_conversation.dialog_id
        sender_id = statistic_conversation.sender_id

        statistic_record = self.env['kw.chatbot.operator.activity'].search([
            ('operator_id', '=', operator_id.id),
            ('chat_id', '=', chat_id.id),
            ('dialog_id', '=', dialog_id.id),
            ('conversation_id', '=', statistic_conversation.id),
            ('sender_id', '=', sender_id.id)
        ], order='date_start desc', limit=1)

        return statistic_record if statistic_record else False

    def _set_first_answer_date(self, statistic_record=False):
        """
        Set date when admin first answered
        """
        # skip in module 'kw_chatbot_statistics' is not installed
        if not self._is_chatbot_statistics_installed():
            return False

        # Skip if not record
        if not statistic_record:
            return False
        # Skip if already statistic contains first answer date
        if statistic_record.first_answer_date:
            return False

        statistic_record.first_answer_date = fields.Datetime.now()
        return True

    def _set_date_end(self, statistic_record=False):
        """
        Set date when admin press '/end' and finished dialogue
        """
        # skip in module 'kw_chatbot_statistics' is not installed
        if not self._is_chatbot_statistics_installed():
            return False

        if not statistic_record:
            return False
        # Skip if this date is already contains
        if statistic_record.date_end:
            return False

        statistic_record.date_end = fields.Datetime.now()
        return True

    def _set_who_answered_last(self, statistic_record=False, sender=False):
        """
        Set owner last message by sender message ['client' or 'operator']
        """
        # skip in module 'kw_chatbot_statistics' is not installed
        if not self._is_chatbot_statistics_installed():
            return False

        if not (statistic_record and sender):
            return False

        if sender == 'user':
            statistic_record.who_answered_id = 'client'
            return True

        if sender == 'admin':
            statistic_record.who_answered_id = 'operator'
            return True

        return False

    def _set_is_answer(self, statistic_record=False):
        """
        Set True if Admin answered in the dialogue
        """
        # skip in module 'kw_chatbot_statistics' is not installed
        if not self._is_chatbot_statistics_installed():
            return False

        if not statistic_record:
            return False

        statistic_record.is_answer = True

        return True


class ModelActivity(models.Model):
    _name = 'kw.chatbot.model.activity'
    _description = 'Model Activity'

    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', )
    res_id = fields.Integer(readonly=True)
    res_model = fields.Char(readonly=True)

    def get_record(self):
        self.ensure_one()
        return self.env[self.res_model].sudo().search(
            [('id', '=', self.res_id)], limit=1)
