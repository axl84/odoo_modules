# pylint: disable=C0302
import logging
import ast
import re
import json
from datetime import datetime, time
from telebot import types

from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.tools.safe_eval import safe_eval

from odoo import models, fields, _, tools, Command

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'
    commands = [
        types.BotCommand('start', 'Run bot'),
    ]

    last_button_id = fields.Many2one(
        comodel_name='kw.chatbot.step.telegram.button', )
    is_searching_record = fields.Boolean(
        default=False, )

    @staticmethod
    def ensure_dict(text):
        if isinstance(text, dict):
            return True
        if isinstance(text, str):
            try:
                text = text.replace("'", '"')
                json.dumps(json.loads(text), indent=2, ensure_ascii=False)
                return True
            except json.JSONDecodeError:
                return False
        else:
            return False

    @staticmethod
    def validate_answer_data(search_type, text):
        if search_type in ['many2one', 'integer', 'float', 'monetary']:
            try:
                return int(text)
            except ValueError:
                return False
        if search_type == 'boolean':
            if text.lower() == 'true':
                return True
        return text

    # pylint: disable=R0911,R0912,R0915,R0914
    def telegram_get_response(self, bot, message):
        if self.chat_id and self.chat_id.tg_command_ids:
            self.chat_id.telegram_update_command()
        else:
            bot.set_my_commands(self.commands)
        _logger.info(message)
        self.env['kw.chatbot.log'].sudo().create({
            'conversation_id': self.id,
            'body': message,
            'name': 'IN',
            'method': type(message),
        })
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if not self.wired_conversation_id:
                self.send_message(
                    text='Press /start to go online or /end to go offline')

        # update context, change lang from sender lang
        if self.sender_id:
            if self.sender_id.user_id:
                self.env.context = dict(
                    self.env.context, lang=self.sender_id.user_id.lang)
                self.env.user = self.sender_id.user_id
            if self.sender_id.partner_id:
                self.env.context = dict(
                    self.env.context, lang=self.sender_id.partner_id.lang)
                self.env.user = self.sender_id.partner_id.user_id
        self.is_telegram_send = False
        text = self.telegram_get_message_data(message)
        if isinstance(text, dict) and text.get('latitude'):
            return super().telegram_get_response(bot, message)
        if self.is_searching_record and '/' not in text:
            text = self.validate_answer_data(
                self.last_button_id.search_field_id.ttype, text)
            search_domain = [(
                self.last_button_id.search_field_id.name, '=', text)]
            search_model = self.last_button_id.model_notification_name
            try:
                search_records = self.env[search_model].sudo().search(
                    search_domain, limit=self.last_button_id.limit)
                notification = self.last_button_id.notification_for_send
            except Exception as e:
                _logger.info(f'Error: {e}')
                search_records = self.env[search_model]
            if not search_records and self.button_model and self.button_res_id:
                search_records = self.env[self.button_model].search([
                    ('id', '=', self.button_res_id)])
                notification = self.last_button_id.uns_notification_for_send
            self.is_searching_record = False
            return self.notification_message_send(
                record_set=search_records,
                kw_notification=notification,
                bot=bot, )
        self.is_searching_record = False
        if self.is_record_write and '/' not in text:
            w_record = self.env[self.button_model].search([
                ('id', '=', self.button_res_id)])
            if w_record:
                button = self.last_button_id
                try:
                    if self.update_record_field(
                            record=w_record, value=text,
                            field_type=self.write_field_type,
                            field_relation=self.write_field_relation,
                            field=self.write_field, ):
                        text = button.successful_notification
                        if text and w_record:
                            text = button.notification_id.render_message(
                                message=text, record=w_record)
                        if text:
                            self.send_message(text=self.render_template(
                                text=text, obj=button.model_id, rec=w_record))
                        last_notification_id = self.last_notification_id
                        text = last_notification_id.prepare_notification_text(
                            record=w_record)
                        if button.is_resend_notification:
                            self.last_notification_id.send_message(
                                record=w_record, text=text,
                                conversation_id=self, )
                        self.is_record_write = False
                except Exception as e:
                    text = button.unsuccessful_notification
                    if text and w_record:
                        text = button.notification_id.render_message(
                            message=text, record=w_record)
                    if text:
                        self.send_message(text=self.render_template(
                            text=text, obj=button.model_id, rec=w_record))
                    else:
                        self.send_message(f'Error: {e}')
                    _logger.info(f'Error: {e}')
            return True
        self.is_record_write = False
        if isinstance(text, str):
            if text.find('/end,') == 0:
                try:
                    id_next_step = int(text.replace('/end, ', ''))
                except Exception as e:
                    _logger.debug(e)
                    return False
                next_step = self.env['kw.chatbot.step'].sudo().browse(id_next_step)
                return self.telegram_next_step(
                    next_step, bot, message, **{'redirect': next_step})
        if text == '/start':
            self.input_step_id = False
        step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
            ('name', '=', text), ])
        if step_alias and step_alias.dialog_answer_id \
                and step_alias.dialog_answer_id.notification_id:
            self.send_keyboard_with_buttons(
                kw_notification=step_alias.dialog_answer_id.notification_id,
                text=step_alias.dialog_answer_id.name, bot=bot)
            self.telegram_next_step(self.last_step_id, bot, message)
            return True
        trig_step = self.env['kw.chatbot.step'].sudo().search([
            ('alias_ids', 'in', step_alias.ids),
            ('dialog_id', '=', self.dialog_id.id)], limit=1)
        if not trig_step and not self.wired_conversation_id:
            if not self.dialog_id.wait_start_message \
                    and text != '/end' and not self.ensure_dict(text):
                text = '/start'
                step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
                    ('name', '=', text), ])
                trig_step = self.env['kw.chatbot.step'].sudo().search([
                    ('alias_ids', 'in', step_alias.ids),
                    ('dialog_id', '=', self.dialog_id.id)])
        if trig_step:
            _check = True
            if trig_step.go_to_step_id:
                _check = False
                domain = safe_eval(trig_step.triggering_answer_domain) \
                    if trig_step.triggering_answer_domain else []
                # check in sender_id.partner_id in domain
                check_partner = self.env['res.partner'].sudo().search(
                    domain)
                if self.sender_id.partner_id in check_partner:
                    _check = True
                else:
                    redirect_ts = trig_step.triggering_answer_redirect_step_id
                    redirect_ts.telegram_get_response(
                        conversation=self, bot=bot, message=message)
                    if not self.input_step_id:
                        self.telegram_next_step(redirect_ts, bot, message)
                    # after domain and triggering_answer for next step
                    self.write(
                        {
                            'last_step_id': trig_step.triggering_answer_redirect_step_id,
                        })
                    return True
            if _check:
                if trig_step.telegram_get_response(
                        conversation=self, bot=bot, message=message):
                    if trig_step.step_type != 'update_contact_field' and self.write({
                        'input_step_id': False,
                        'is_telegram_send': True,
                        'last_step_id': trig_step.id,
                    }):
                        # if trig_step.step_type == 'create_lead':
                        #     self.telegram_next_step(trig_step, bot, message)
                        return True
                    if self.input_step_id:
                        return None
                    if trig_step.step_type == 'update_contact_field':
                        self.last_step_id = trig_step
                        # self.send_message(
                        #     text=trig_step.msg_before_update_contact_field)
                        return None
                self.write({
                    'is_telegram_send': True,
                    'last_step_id': trig_step.id,
                })

                self.telegram_next_step(trig_step, bot, message)
                return True
                # else:
                #     # go to next step
                #     self.telegram_next_step(self.last_step_id.go_to_step_id, bot, message)
                #     return True
        if self.input_step_id:
            answer = text
            lang = self.sender_id.partner_id.lang
            text_resp = self.input_step_id.with_context(lang=lang).msg_after_update_contact_field
            if self.input_step_id.step_type == 'update_contact_field' and \
                    self.input_step_id.update_contact_field.name in \
                    ['phone', 'mobile']:
                if isinstance(answer, str):
                    answer = answer.replace(' ', '')
                else:
                    answer = text.get('phone_number')
                record = self.sender_id.partner_id
                if record.write({self.input_step_id.update_contact_field.name: answer}):
                    if self.input_step_id.merge_by_phone_number:
                        self.merge_contact_by_phone_number(answer)
                    keyboard = types.ReplyKeyboardMarkup(
                        row_width=1, resize_keyboard=True)
                    # add empty button
                    button_phone = types.KeyboardButton(
                        text="", )
                    keyboard.add(button_phone)
                    self.send_message(text=text_resp, reply_markup=keyboard)
            # self.input_step_id = False
            elif self.input_step_id.step_type == 'update_contact_field':
                # get field to update
                field = self.input_step_id.update_contact_field.name
                # get record to update
                record = self.sender_id.partner_id
                # get value to update
                value = text
                # update record
                if isinstance(message, types.CallbackQuery):
                    try:
                        value = ast.literal_eval(message.data)
                    except SyntaxError:
                        _logger.info('json_data is not dict')
                        return False
                if isinstance(value, dict):
                    value = value.get('id')
                if record.write({field: value}):
                    self.send_message(text=text_resp)
                    # self.input_step_id = False
            # from contact delete and add tags
            for add_tag in self.input_step_id.add_contact_tag_ids:
                self.sender_id.partner_id.category_id = [(4, add_tag.id)]
            for del_tag in self.input_step_id.remove_contact_tag_ids:
                self.sender_id.partner_id.category_id = [(3, del_tag.id)]
            self.env['kw.chatbot.input.question'].create({
                'question': self.input_step_id.text,
                'answer': answer,
                'conversation_id': self.id, })
            self.write({
                'input_step_id': False,
                'last_step_id': self.input_step_id, })

            self.telegram_next_step(self.last_step_id, bot, message)
            return True

        if text == '/end' and self.last_step_id:
            self.telegram_next_step(self.last_step_id, bot, message)
            return True
        answer_for_notification = self.env['chatbot.dialog.answer'].sudo().search(
            [('name', '=', text),
             ('dialog_step_id', '=', self.last_step_id.id), ])
        _logger.info(f'answer for notification {answer_for_notification}')
        # flake8: noqa: E501
        kw_notification = answer_for_notification.notification_id if answer_for_notification else False
        if kw_notification:
            self.send_keyboard_with_buttons(kw_notification, text, bot=bot)
            self.telegram_next_step(self.last_step_id, bot, message)
            return True
        if isinstance(message, types.CallbackQuery):
            res = self.do_action_on_button_click(message.data, bot, message)
            if res == 'update_contact_field':
                self.write({
                    'input_step_id': False, })
                # 'last_step_id': self.input_step_id, })
                return self.telegram_next_step(self.last_step_id, bot, message)
            if res:
                return res

        # answer = None
        # if not step_alias:
        answer = self.env['chatbot.dialog.answer'].sudo().search([
            ('name', '=', text),
            ('dialog_step_id', '=', self.last_step_id.id)])
        _logger.info(f'Answer for next step {answer}')
        if not answer:

            # Temporary solution.There may be errors!

            answer = self.env['chatbot.dialog.answer'].sudo().search([
                ('dialog_script_id', '=', self.dialog_id.id),
                ('name', '=', text)])
            _logger.info(f'Answer in this dialog: {answer}')

        if answer and not answer.refund_step_id:
            self.write({
                'is_telegram_send': True,
                'last_step_id': answer.dialog_step_id.id, })
            if self.input_step_id:
                return None
            self.telegram_next_step(answer.dialog_step_id, bot, message)
        elif answer.refund_step_id:
            # sequence = answer.refund_step_id.sequence
            step = answer.refund_step_id
            if self.input_step_id:
                return None
            self.write({'last_step_id': step.id})
            telegram_response = answer.refund_step_id.telegram_get_response(
                conversation=self, bot=bot, message=message)
            if self.input_step_id:
                return None
            if not telegram_response:

                # situation after buttons when text have next step
                if step.step_type == 'text' and step.go_to_step_id:
                    self.telegram_next_step(step, bot, message)
                    return super().telegram_get_response(bot, message)

                self.write({'last_step_id': step.id})
                return None
            if isinstance(telegram_response, dict):
                if telegram_response.get('redirect'):
                    r_step = telegram_response.get('redirect')
                    self.write({
                        'is_telegram_send': True,
                        'last_step_id': step.id, })
                    self.telegram_next_step(
                        r_step, bot, message, **{'redirect': r_step})
                    return False
            if step.select_flow in ['sale', 'survey'] or self.input_step_id:
                return None
            # if the step to operator is after button - without run next step before end consultation
            if step.step_type in ["forward_operator", "create_lead"]:
                return super().telegram_get_response(bot, message)
            self.telegram_next_step(step, bot, message)
        _logger.info('message.data not found')
        return super().telegram_get_response(bot, message)

    # def login_in_system_by_phone(self, phone_number, sender_id):
    #     partner_model = self.env['res.partner']
    #     user_model = self.env['res.users']
    #     partner_ids = partner_model.search([('phone', '=', phone_number)])
    #     user_id = user_model.search([('partner_id', 'in', partner_ids.ids)])
    #     if user_id:
    #         wizard = self.env['base.partner.merge.automatic.wizard']
    #         if not wizard._merge(partner_ids=partner_ids.ids,
    #                              dst_partner=sender_id.partner_id):
    #             return True
    #         # merged_partner.write({'user_id': user_id.id})
    #         # sender = self.env['res.partner'].browse(sender_id)
    #         # sender.write({'partner_id': merged_partner.id})
    #         return True
    #     return False

    def update_contact_field(self, res, bot, message):
        # get field to update
        lang = self.sender_id.partner_id.lang
        text_resp = self.last_step_id.with_context(lang=lang).msg_after_update_contact_field
        field = self.last_step_id.update_contact_field
        # get record to update
        record = self.sender_id.partner_id
        # get value to update
        if res.get('id') in ['False', 'True']:
            # pylint: disable=R1719
            value = True if res.get('id') == 'True' else False
        elif field.ttype == 'selection':
            value = res.get('id')
        else:
            value = self.env[self.last_step_id.update_contact_field.relation].search([
                ('id', '=', res.get('id'))])
        # update record
        if field.ttype == 'many2one':
            if record.write({field.name: value.id}):
                self.send_message(text=text_resp)
        elif field.ttype == 'many2many':
            if record.write({field.name: [(4, value.id)]}):
                self.send_message(text=text_resp)
        elif field.ttype == 'boolean':
            if record.write({field.name: value}):
                self.send_message(text=text_resp)
        elif field.ttype == 'selection':
            if record.write({field.name: value}):
                self.send_message(text=text_resp)
        # from contact delete and add tags
        for add_tag in self.last_step_id.add_contact_tag_ids:
            self.sender_id.partner_id.category_id = [(4, add_tag.id)]
        for del_tag in self.last_step_id.remove_contact_tag_ids:
            self.sender_id.partner_id.category_id = [(3, del_tag.id)]
        return 'update_contact_field'

    # pylint: disable=R1702,R1705
    def dynamic_button_action(
            self, button, record, callback_data, bot=None, message=None):
        value = ''
        if button.dynamic_button_field_id.ttype == 'selection':
            selection_id = self.env['ir.model.fields.selection'].search([
                ('id', '=', callback_data.get('db_id'))])
            value = selection_id.value
        if button.dynamic_button_field_id.ttype in ['many2one', 'many2many']:
            value = callback_data.get('db_id')
        if button.dynamic_button_field_id.ttype == 'one2many':
            self.sudo().write({
                'button_res_id': int(callback_data.get('db_id')),
                'button_model': button.dynamic_button_field_id.relation, })
            if button.dynamic_button_action == 'comparison':
                domain = [('id', '=', self.button_res_id)]

                if button.comparison_value_type == 'value':
                    c_value = button.comparison_value
                if button.comparison_value_type == 'field':
                    c_value = getattr(
                        record, button.comparison_record_field_id.name)

                if button.comparison_type == 'eq':
                    domain.append((
                        button.comparison_field_id.name, '=', c_value))
                elif button.comparison_type == 'not_eq':
                    domain.append((
                        button.comparison_field_id.name, '!=', c_value))
                elif button.comparison_type == 'gt':
                    domain.append((
                        button.comparison_field_id.name, '>', c_value))
                elif button.comparison_type == 'gte':
                    domain.append((
                        button.comparison_field_id.name, '>=', c_value))
                elif button.comparison_type == 'lt':
                    domain.append((
                        button.comparison_field_id.name, '<', c_value))
                elif button.comparison_type == 'lte':
                    domain.append((
                        button.comparison_field_id.name, '<=', c_value))
                bt_rec = self.env[self.button_model].search(domain)
                if bt_rec:
                    return True
                else:
                    self.send_message(text=button.comparison_result_text)
                    return False
        if value:
            rec = record.sudo().write({
                button.dynamic_button_field_id.name: value})
            return rec
        return False

    def save_telegram_model_activity(self, res_model, res_id):
        tma = self.env['kw.chatbot.model.activity'].sudo()
        tma_id = tma.search([
            ('conversation_id', '=', self.id),
            ('res_model', '=', res_model)])
        if tma_id:
            tma_id.sudo().write({
                'res_id': res_id, })
        else:
            tma.create({
                'conversation_id': self.id,
                'res_id': res_id,
                'res_model': res_model})

    def _save_telegram_model_activity(
            self, notification_id, res_model, res_id):
        self.ensure_one()
        self.save_telegram_model_activity(
            res_model=res_model, res_id=res_id)
        record = self.env[res_model].sudo().search([
            ('id', '=', res_id)], limit=1)
        for obj in notification_id.related_fields_ids:
            related_record = getattr(record, obj.name)
            if related_record:
                self.save_telegram_model_activity(
                    res_model=related_record._name, res_id=related_record.id)

    def do_action_on_button_click(self, json_data, bot=None, message=None):
        try:
            res = ast.literal_eval(json_data)
        except SyntaxError:
            _logger.info('json_data is not dict')
            return False
        _logger.info(f'res: {res}')
        if isinstance(res, int):
            return False
        if res.get('t'):
            return self.update_contact_field(res, bot, message)
        # get button data
        button_data = res.get('id_button')
        _logger.info(f'button_data: {button_data}')
        button = self.env['kw.chatbot.step.telegram.button'].sudo().browse(
            button_data)
        _logger.info(f'button: {button}')
        _logger.info(f'button.fields_lines: {button.fields_lines}')
        # get record data
        record_data = res.get('id_record')
        if button.notification_id.is_save_button_activity:
            if button.notification_id.model_id and record_data:
                self._save_telegram_model_activity(
                    notification_id=button.notification_id,
                    res_model=button.notification_id.model_id.model,
                    res_id=record_data)
        if button.state == 'forward_step':
            return self.telegram_next_step(
                self.last_step_id, bot, message,
                **{'redirect': button.forward_step_id})
        if button.state == 'button_for_sale':
            return self.send_keyboard_with_buttons(
                button.notification_for_send, button.name, button, bot=bot)
        if button.state == 'send_notification':
            return self.send_keyboard_with_buttons(
                button.notification_for_send, button.name, button, json=res, bot=bot)
        record = False
        if button.model_id.model:
            record = self.env[button.notification_model_name].sudo().browse(
                record_data)
        if button.state == 'dynamic_button':
            try:
                self.sudo().write({
                    'button_res_id': int(res.get('db_id')),
                    'button_model': button.dynamic_button_field_id.relation, })
            except SyntaxError:
                _logger.info('dynamic button doesnt write')
        if not self.action_on_button_domain(
                button=button, record=record, bot=bot,
                message=message, action_type='before_action'):
            return False
        _logger.info(f'record: {record}')
        if button.state == 'dynamic_button':
            res = self.dynamic_button_action(
                button, record, res, bot=bot, message=message)
        # methods for actions to do
        if button.state == 'object_write':
            if button.write_type == 'tg_input':
                return self.action_write(button, record)
            res = self.action_write(button, record)
        if button.state == 'object_create':
            res = self.action_create(button, record)
            if res and button.send_new_record and \
                    button.new_record_notification_id:
                button.new_record_notification_id.notification_message_send(
                    records=res, conversation_ids=self, bot=bot)
        if button.state == 'code':
            res = self.action_code(record=record, button=button)
        if button.state == 'email':
            res = self.action_email(button, record)
        if button.state == 'sms':
            res = self.action_sms(button, record)
        if button.state == 'followers':
            res = self.action_followers(button, record)
        if button.state == 'next_activity':
            res = self.action_next_activity(button, record)
        action_result = True
        if res:
            text = button.successful_notification
        else:
            text = button.unsuccessful_notification
            action_result = False
        if text and record:
            text = button.notification_id.render_message(
                message=text, record=record)
        else:
            clean = re.compile('<.*?>')
            text = re.sub(clean, '', text)
        self.action_on_button_domain(
            button=button, record=record, bot=bot,
            message=message, action_type='after_action',
            text=text, result=action_result)
        if not button.button_step_ids:
            self.send_message(text=text)
        return True

    def action_on_button_domain(
            self, button, record, bot, message, **kwargs):
        action_type = kwargs.get('action_type')
        if not button.button_step_ids:
            return True
        before_action_step_ids = button.button_step_ids.filtered(
            lambda x: x.action_type == action_type)
        if not before_action_step_ids:
            return True
        if action_type == 'before_action':
            for action in before_action_step_ids:
                domain = safe_eval(action.domain)
                f_record = record.filtered_domain(domain)
                if f_record:
                    step_id = action.successful_step_id
                    notification_id = action.successful_notification_id
                    self.button_domain_forward_step(
                        step_id, notification_id, bot, message, record, action)
                    return False
            return True
        if action_type == 'after_action':
            text = kwargs.get('text')
            result = kwargs.get('result')
            if text:
                self.send_message(
                    text=self.render_template(
                        text=text, obj=button.model_id, rec=record))
            if not result:
                before_action_step_ids = before_action_step_ids.filtered(
                    lambda x: x.action_result_type in ['unsuccessful'])
            else:
                before_action_step_ids = before_action_step_ids.filtered(
                    lambda x: x.action_result_type in ['anyway', 'successful'])
            for action in before_action_step_ids:
                f_record = record
                if action.domain:
                    domain = safe_eval(action.domain)
                    f_record = record.filtered_domain(domain)
                if f_record:
                    step_id = action.successful_step_id
                    notification_id = action.successful_notification_id
                    self.button_domain_forward_step(
                        step_id, notification_id, bot, message, record, action)
        return True

    def button_domain_forward_step(
            self, step_id,  notification_id, bot, message, record, action):
        if action.step_type == 'code' and action.code:
            self.action_code(record=record, code=action.code)
        elif step_id:
            self.telegram_next_step(
                self.last_step_id, bot, message,
                **{'redirect': step_id})
        else:
            if not action.bind_record or \
                    record._name != notification_id.model_id.model:
                record = self.env[notification_id.model_id.model].search([])
            notification_id.notification_message_send(
                records=record, conversation_ids=self)
        return True

    def action_next_activity(self, button, record):
        _logger.info('action_next_activity')
        _logger.info(f'button: {button}')
        _logger.info(f'record: {record}')
        activity_type = self.env['mail.activity.type'].browse(
            button.activity_type_id.id)
        _logger.info(f'activity_type: {activity_type}')
        activity = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'note': button.activity_note,
            'res_id': record.id,
            'res_model_id': record._name,
            'user_id': button.user_id.id,
            'date_deadline': button.date_deadline,
        })
        _logger.info(f'activity: {activity}')
        return True

    def action_email(self, button, record):
        _logger.info('action_email')
        _logger.info(f'button: {button}')
        _logger.info(f'record: {record}')
        template = self.env['mail.template'].browse(button.template_id.id)
        _logger.info(f'template: {template}')
        template.send_mail(record.id, force_send=True)
        return True

    def action_sms(self, button, record):
        _logger.info('action_sms')
        _logger.info(f'button: {button}')
        _logger.info(f'record: {record}')
        template = self.env['sms.template'].browse(button.sms_template_id.id)
        _logger.info(f'template: {template}')
        template.send_sms(record.id)
        return True

    def action_followers(self, button, record):
        _logger.info('action_followers')
        _logger.info(f'button: {button}')
        _logger.info(f'record: {record}')
        if button.partner_ids:
            record.message_subscribe(button.partner_ids.ids)
        return True

    def action_code(self, record, button=None, code=None):
        eval_context = self._get_eval_context()
        eval_context['record'] = record
        if not code and button:
            code = button.code.strip()
        safe_eval(code, eval_context, mode="exec", nocopy=True)
        return eval_context.get('action')

    def action_create(self, button, record):
        eval_context = self._get_eval_context()
        eval_context['record'] = record
        fields_lines = button.fields_lines.filtered(
            lambda x: 'conversation' not in x.value)
        vals = fields_lines.eval_value(eval_context=eval_context)
        res = {line.update_field_id.name: vals[line.id] for line in fields_lines}
        if button.record_fields_ids \
                and button.model_name == button.notification_model_name:
            for field in button.record_fields_ids:
                value = getattr(record, field.name)
                res.update({field.name: value})
        con_fields_lines = button.fields_lines.filtered(
            lambda x: 'conversation' in x.value)
        if con_fields_lines:
            for field in con_fields_lines:
                l_value = field.value.replace('conversation ', '')
                eval_context['record'] = self
                value = safe_eval(l_value, eval_context)
                res.update({field.update_field_id.name: value})
        res = self.env[button.target_model_id.model].create(res)
        if button.link_field_id:
            record = self.env[self.model_id.model].browse(
                self._context.get('active_id'))
            if button.link_field_id.ttype in ['one2many', 'many2many']:
                record.write(
                    {button.link_field_id.name: [Command.link(res.id)]})
            else:
                record.write({button.link_field_id.name: res.id})
        return res

    def update_record_field(
            self, record, value, field, field_relation, field_type):
        if field_type == 'float':
            value = str(value).replace(',', '.')
        try:
            value = ast.literal_eval(value)
        except Exception as e:
            _logger.debug(e)
            return record.write({field: value})
        if isinstance(value, int) or isinstance(value, float):
            return record.write({field: value})
        if value.get('id') in ['False', 'True']:
            # pylint: disable=R1719
            value = True if value.get('id') == 'True' else False
        elif field_type == 'selection':
            value = value.get('id')
        else:
            value = self.env[field_relation].search([
                ('id', '=', value.get('id'))])
        # update record
        if field_type == 'many2one':
            if record.write({field: value.id}):
                return True
        elif field_type == 'many2many':
            if record.write({field: [(4, value.id)]}):
                return True
        if record.write({field: value}):
            return True
        return False

    def send_message_for_update_field(self, text, field):
        self.ensure_one()
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        if field.ttype in ['many2one', 'many2many']:
            for but in self.env[field.relation].sudo().search([], limit=10):
                call_back = {'id': but.id}
                f_name = but.with_context(
                    lang=self.sender_id.partner_id.lang).name
                button = types.InlineKeyboardButton(
                    text=f_name, callback_data=str(call_back))
                buttons.append(button)
        if field.ttype == 'boolean':
            for but in [True, False]:
                call_back = {'id': f'{but}'}
                button = types.InlineKeyboardButton(
                    text=f'{but}', callback_data=str(call_back))
                buttons.append(button)
        if field.ttype == 'selection':
            for but in self.env[field.model].fields_get(
                    allfields=[field.name])[field.name]['selection']:
                call_back = {'id': but[0]}
                button = types.InlineKeyboardButton(
                    text=but[1], callback_data=str(call_back))
                buttons.append(button)
        markup.add(*buttons)
        return self.send_message(
            text=text, reply_markup=markup, buttons=buttons)

    def action_write(self, button, record):
        if button.write_type == 'tg_input':
            self.sudo().write({
                'button_res_id': record.id,
                'button_model': record._name,
                'write_field': button.change_field_id.name,
                'write_field_type': button.change_field_id.ttype,
                'write_field_relation': button.change_field_id.relation,
                'is_record_write': True,
                'last_button_id': button.id,
                'last_notification_id': button.notification_id})
            lang = self.sender_id.partner_id.lang
            text = button.change_field_id.with_context(
                lang=lang).field_description
            return self.send_message_for_update_field(
                field=button.change_field_id,
                text=f"{text}:")
        for action in button.fields_lines:
            _logger.info(f'action.value: {action.value}')
            if action.evaluation_type == 'value':
                try:
                    record.env.user = self.env.user
                    if action.value == 'True':
                        res = record.with_context(uid=self.env.uid).sudo(
                        ).write({action.update_field_id.name: True})
                    elif action.value == 'False':
                        res = record.with_context(uid=self.env.uid).sudo(
                        ).write({action.update_field_id.name: False})
                    else:
                        res = record.with_context(uid=self.env.uid).sudo(
                        ).write({action.update_field_id.name: action.value})
                except Exception as e:
                    _logger.info(f'e: {e}')
                    res = False
                _logger.info(f'res: {res}')
            if action.evaluation_type == 'equation':
                # get eval context
                eval_context = self._get_eval_context()
                eval_context['record'] = record
                eval_context['model'] = button.model_id.model
                eval_context['self'] = self
                eval_context['env'] = self.env
                expr = safe_eval(action.value, eval_context)
                if not expr and not isinstance(expr, bool):
                    return False
                try:
                    res = record.sudo().write(
                        {action.update_field_id.name: expr})
                except Exception as e:
                    _logger.info(f'e: {e}')
                    res = False
                if getattr(record, action.update_field_id.name) == expr:
                    res = True
        return res

    def render_template(self, obj, rec, text):
        render_message = self.env['sms.template']._render_template(
            template_src=text,
            model=obj.model, res_ids=[rec.id], add_context={
                'lang': self.sender_id.partner_id.lang})
        _logger.info(f'render_message: {render_message}')
        clean = re.compile('<.*?>')
        text = re.sub(r'<br.*?>', '\n', render_message[rec.id])
        text = re.sub(clean, '', text)
        _logger.info(f'text: {text}')
        return text

    # pylint: disable=R0914,W0621
    def send_keyboard_with_buttons(
            self, kw_notification, text, button=False, json=False, bot=False):
        _logger.info('in def send_keyboard_with_buttons')
        record_set = self.env[kw_notification.model_id.model].sudo().search([])
        # check if answer has personal field
        _logger.info(f'user: {self.env.user.name}')
        if button and button.send_notification_type == 'field_search':
            record = False
            if json and button:
                id_record = json.get('id_record')
                record = self.env[button.model_id.model].sudo().browse(
                    id_record)
            self.sudo().write({
                'button_res_id': record.id if record else 0,
                'button_model': record._name if record else '',
                'is_searching_record': True,
                'last_button_id': button.id,
                'last_notification_id': button.notification_id.id})
            lang = self.sender_id.partner_id.lang
            text = button.search_field_id.with_context(
                lang=lang).field_description
            return self.send_message(text=f"{text}:")
        if self.dialog_id.execute_sudo:
            check_personal_field = self.env[
                'chatbot.dialog.answer'].sudo().search(
                [('notification_id', '=', kw_notification.id),
                 ('is_personal_data', '=', True),
                 ('name', '=', text)], limit=1)
            check_extra_domain = self.env[
                'chatbot.dialog.answer'].sudo().search(
                [('notification_id', '=', kw_notification.id),
                 ('name', '=', text),
                 ('is_used_new_domain', '=', True)], limit=1)
        else:
            check_personal_field = self.env['chatbot.dialog.answer'].search(
                [('notification_id', '=', kw_notification.id),
                 ('is_personal_data', '=', True),
                 ('name', '=', text)], limit=1)
            check_extra_domain = self.env['chatbot.dialog.answer'].search(
                [('notification_id', '=', kw_notification.id),
                 ('name', '=', text),
                 ('is_used_new_domain', '=', True)], limit=1)
        if check_personal_field:
            if check_personal_field.model_field_id.relation == \
                    'res.users':
                extra_domain = [(check_personal_field.model_field_id.name, '=',
                                 self.sender_id.user_id.id)]
            elif check_personal_field.model_field_id.relation == \
                    'hr.employee':
                partner_id = self.sender_id.partner_id
                _logger.info(f'Conversation partner: {partner_id}')
                employee_id = self.env['hr.employee'].sudo().search([
                    ('work_contact_id', '=', partner_id.id)], limit=1)
                _logger.info(f'Employee: {employee_id}')
                extra_domain = \
                    [(check_personal_field.model_field_id.name, '=',
                      employee_id.id)]
                _logger.info(f'Domain: {extra_domain}')
            elif check_personal_field.model_field_id.relation == \
                    'res.partner':
                extra_domain = \
                    [(check_personal_field.model_field_id.name, '=',
                      self.sender_id.partner_id.id)]
            elif kw_notification.model_id.model == 'res.partner':
                extra_domain = [('id', '=', self.sender_id.partner_id.id)]
            else:
                extra_domain = []
        if self.dialog_id.execute_sudo:
            self_sudo = kw_notification.sudo()
        else:
            self_sudo = kw_notification
            # self_sudo.env.su = False
        if check_extra_domain:
            if check_extra_domain.extra_domain:
                if check_extra_domain.is_used_new_domain:
                    domain = safe_eval(
                        check_extra_domain.extra_domain,
                        self._get_eval_context())
                    record_set = \
                        self.env[kw_notification.model_id.model].search(
                            []).filtered_domain(domain)
        elif self_sudo.filter_domain:
            domain = safe_eval(
                self_sudo.filter_domain, self._get_eval_context())
            record_set = \
                self.env[kw_notification.model_id.model].search(
                    []).filtered_domain(domain)
        else:
            record_set = \
                self.env[kw_notification.model_id.model].search([])
        if button:
            if button.use_parent_record:
                if json:
                    record_data = json.get('id_record')
                    search_field = button.child_field_id.name
                    if button.search_type == 'children':
                        record_set = \
                            self.env[kw_notification.model_id.model].search([
                                (search_field, '=', record_data)])
                    if button.search_type == 'parent':
                        record = self.env[button.model_id.model].sudo().browse(
                            record_data)
                        record_set = getattr(record, search_field)
                else:
                    record_set = \
                        self.env[kw_notification.model_id.model].search(
                            [(button.child_field_id.name, '=',
                              button.id_record)])
        if check_personal_field:
            record_set = record_set.filtered_domain(extra_domain)
        return self.notification_message_send(
            record_set, kw_notification, bot)

    def filtered_notification_record(self, record_set, kw_notification):
        if kw_notification.filtered_fields_ids:
            for f in kw_notification.filtered_fields_ids.sorted('sequence'):
                if f.filtered_type == 'conversation':
                    model_activity = self.model_activity_ids.filtered(
                        lambda x: x.res_model == f.field_id.relation)
                    if model_activity:
                        record_set = record_set.filtered(
                            lambda x: model_activity.res_id in getattr(
                                x, f.field_id.name).ids)
                elif f.filtered_type == 'own_model':
                    model_activity = self.model_activity_ids.filtered(
                        lambda x: x.res_model == f.model_id.model)
                    if model_activity:
                        record_set = record_set.filtered(
                            lambda x: x.id == model_activity.res_id)
                else:
                    if f.partner_field_id:
                        p_field_id = getattr(
                            self.partner_id, f.partner_field_id.name)
                        if p_field_id:
                            record_set = record_set.filtered(
                                lambda x: p_field_id[0].id in getattr(
                                    x, f.field_id.name).ids)
        if kw_notification.is_days_filter and record_set:
            domain = [('id', 'in', record_set.ids)]
            if kw_notification.filter_field_id.ttype != 'integer' and \
                    kw_notification.value_type == 'day':
                filtered_value = datetime.today() + relativedelta(
                    days=kw_notification.filter_value)
            if kw_notification.value_type == 'weekday':
                day_of_week = datetime.now().weekday() + 1
                filtered_value = day_of_week + kw_notification.filter_value
            filter_field = kw_notification.filter_field_id.name
            if kw_notification.filter_field_id.ttype == 'datetime' and \
                    kw_notification.filter_type == 'eq':
                domain.append(
                    (filter_field, '>=', datetime.combine(
                        filtered_value, time(0, 0, 0))))
                domain.append(
                    (filter_field, '<=', datetime.combine(
                        filtered_value, time(23, 59, 59))))
            elif kw_notification.filter_type == 'eq':
                domain.append((
                    filter_field, '=', filtered_value))
            elif kw_notification.filter_type == 'not_eq':
                domain.append((
                    filter_field, '!=', filtered_value))
            elif kw_notification.filter_type == 'gt':
                domain.append((
                    filter_field, '>', filtered_value))
            elif kw_notification.filter_type == 'gte':
                domain.append((
                    filter_field, '>=', filtered_value))
            elif kw_notification.filter_type == 'lt':
                domain.append((
                    filter_field, '<', filtered_value))
            elif kw_notification.filter_type == 'lte':
                domain.append((
                    filter_field, '<=', filtered_value))
            record_set = record_set.sudo().search(domain)
        if kw_notification.is_unique_by_field and record_set:
            ids = []
            field_name = kw_notification.unique_filter_field_id.name
            for unique_value in record_set.mapped(field_name):
                if kw_notification.unique_filter_field_id.ttype in \
                        ['many2one', 'many2many', 'one2many']:
                    ids.append(record_set.sudo().search([
                        (field_name, 'in', unique_value.ids)], limit=1).id)
                else:
                    ids.append(record_set.sudo().search([
                        (field_name, '=', unique_value)], limit=1).id)
            record_set = record_set.sudo().search([('id', 'in', ids)])
        return record_set

    def notification_message_send(self, record_set, kw_notification, bot):
        self_sudo = kw_notification.sudo()
        record_set = self.filtered_notification_record(
            record_set=record_set, kw_notification=kw_notification)
        if len(record_set) > 100:
            return self.send_message(
                text='Many records. Create the correct notification')
        if kw_notification.sorted_field_id:
            record_set = record_set.sorted(
                kw_notification.sorted_field_id.name)
        for record in record_set:
            # add button
            markup, buttons = None, []
            markup = types.InlineKeyboardMarkup()
            for bt in kw_notification.telegram_button_ids:
                callback_data = ast.literal_eval(bt.callback_data.replace(
                    "'", '"'))
                callback_data['id_record'] = record.id
                callback_data['id_conversation'] = self.id
                btn = types.InlineKeyboardButton(
                    text=_(bt.name), callback_data=str(callback_data), )
                markup.add(btn)
            markup.add(*buttons)
            self_sudo.notification_message_send(
                record, reply_markup=markup,
                buttons=buttons, conversation_ids=self,
                **{'sender_user': self.sender_id.user_id, 'bot': bot})
        if not record_set:
            return self.send_message(text=kw_notification.message_not_found)
        return True

    def _get_eval_context(self):
        if self.sender_id.user_id:
            self.env.user = self.sender_id.user_id
        return {
            'datetime': tools.safe_eval.datetime,
            'time': tools.safe_eval.time,
            'sender_user': self.sender_id.user_id,
            'sender_partner': self.sender_id.partner_id,
            'conversation': self,
            'env': self.env,
            'context': self.env.context,
            'float_compare': float_compare,
            'log': _logger.info,
            'UserError': UserError,
            'Command': Command, }

    # pylint: disable=R1710
    def telegram_next_step(self, step, bot, message, **kwargs):
        if kwargs.get('redirect'):
            next_step = kwargs.get('redirect')
        else:
            next_step = step.go_to_step_id
        next_step = next_step.sorted(key=lambda r: r.sequence)
        for obj in next_step:
            telegram_response = obj.telegram_get_response(
                conversation=self, bot=bot, message=message)

            if isinstance(telegram_response, dict):
                if telegram_response.get('redirect'):
                    r_step = telegram_response.get('redirect')
                    self.write({
                        'is_telegram_send': True,
                        'last_step_id': obj.id, })
                    self.telegram_next_step(
                        r_step, bot, message, **{'redirect': r_step})
                    return False
            elif telegram_response:
                if self.input_step_id or obj.step_type == 'forward_operator':
                    break
                self.write({
                    'is_telegram_send': True,
                    'last_step_id': obj.id, })
                if obj.step_type not in ['text', 'request_notification', 'create_lead']:
                    break
            else:
                # pylint: disable=R1705
                if obj.step_type == 'text':
                    self.write({
                        'is_telegram_send': True,
                        'last_step_id': obj.id, })
                    self.telegram_next_step(obj, bot, message)
                    return
                if obj.step_type == 'update_contact_field':
                    self.write({
                        'is_telegram_send': True,
                        'last_step_id': obj.id, })
                    return
            self.telegram_next_step(obj, bot, message)
        return True

    def telegram_does_not_found(self):
        if not self.wired_conversation_id and \
                not self.chat_id.is_consultant_chat and \
                not self.operator_live_id:
            return super(Conversation, self).telegram_does_not_found()
        return False

    def telegram_out_message(self, text=False):
        if not self.wired_conversation_id and not self.operator_live_id:
            res = super(Conversation, self).telegram_out_message(text=text)
            return res
        return False
