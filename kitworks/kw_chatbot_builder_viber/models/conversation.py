import logging
import ast
import re

from odoo import models, tools
from odoo.tools import float_compare
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    # pylint: disable=R0911,R0912,R0915,R0914
    def viber_get_response(self, bot, message):

        if self.dialog_id.bots_type == 'is_consultant_bot':
            if not self.wired_conversation_id:
                self.send_message(
                    text='Press /start to go online or /end to go offline')
        self.is_viber_send = False
        text = message.get('text')
        try:
            text = ast.literal_eval(text)
            if hasattr(text, 'get'):
                if text.get('action_body'):
                    text = text.get('action_body')
                else:
                    text = text.get('text')
        except Exception as e:
            _logger.debug(e)
        action_body_dict = self.viber_str_to_dict(text)
        if isinstance(action_body_dict, dict):
            if action_body_dict.get('type') == 'notification':
                return self.do_viber_action_on_button_click(action_body_dict)

            # run this - if text step have custom viber buttons
            if action_body_dict.get('type') == 'run_viber_python':
                self.do_action_viber_python_click(action_body_dict)

                # clear input step id for next conversation cycle
                self.write({
                    'input_step_id': False, })

                # go to next step after run Python code from button
                self.viber_next_step(self.last_step_id, bot, message)
                return True

        text = str(text)
        trig_step = self.env['kw.chatbot.step']
        step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
            ('name', '=', text), ])
        answer = self.env['chatbot.dialog.answer'].sudo().search([
            ('name', '=', text),
            ('dialog_step_id', '=', self.last_step_id.id)])
        if step_alias:
            trig_step = self.env['kw.chatbot.step'].sudo().search([
                ('alias_ids', 'in', step_alias.ids),
                ('dialog_id', '=', self.dialog_id.id)])
        if not trig_step and not self.wired_conversation_id and not answer:
            if (not self.dialog_id.wait_start_message
                    and not self.input_step_id and text != '/end'):
                text = '/start'
                step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
                    ('name', '=', text), ])
                trig_step = self.env['kw.chatbot.step'].sudo().search([
                    ('alias_ids', 'in', step_alias.ids),
                    ('dialog_id', '=', self.dialog_id.id)])
        if trig_step:
            if trig_step.viber_get_response(
                    conversation=self, bot=bot, message=message):
                self.write({
                    'is_viber_send': True,
                    'last_step_id': trig_step.id, })
                if self.input_step_id:
                    return None

            if self.input_step_id.step_type == 'update_contact_field':
                return True

            # if current step operator - run without next step before end conv
            if trig_step.step_type == "forward_operator":
                return super().viber_get_response(bot, message)

            self.viber_next_step(trig_step, bot, message)
            return True

        if self.input_step_id:
            lang = self.sender_id.partner_id.lang
            text_resp = self.input_step_id.with_context(
                lang=lang).msg_after_update_contact_field
            if self.input_step_id.step_type == 'update_contact_field':
                field = self.input_step_id.update_contact_field.name
                record = self.sender_id.partner_id
                value = text
                ttype = self.input_step_id.update_contact_field.ttype
                f_name = self.input_step_id.update_contact_field.name
                if ttype in ['many2one', 'many2many']:
                    value = int(text)
                if record.write({field: value}):
                    self.send_message(text=text_resp)
                if (f_name in ['phone', 'mobile']
                        and self.input_step_id.merge_by_phone_number):
                    self.merge_contact_by_phone_number(value)
            for add_tag in self.input_step_id.add_contact_tag_ids:
                self.sender_id.partner_id.category_id = [(4, add_tag.id)]
            for del_tag in self.input_step_id.remove_contact_tag_ids:
                self.sender_id.partner_id.category_id = [(3, del_tag.id)]
            self.env['kw.chatbot.input.question'].create({
                'question': self.input_step_id.text,
                'answer': text,
                'conversation_id': self.id, })
            self.write({
                'input_step_id': False,
                'last_step_id': self.input_step_id, })
            self.viber_next_step(self.last_step_id, bot, message)
            return True

        if text == '/end' and self.last_step_id:
            self.viber_next_step(self.last_step_id, bot, message)
            return True

        if answer and not any([answer.refund_step_id, answer.notification_id]):
            self.write({
                'is_viber_send': True,
                'last_step_id': answer.dialog_step_id.id, })
            if self.input_step_id:
                return None
            self.viber_next_step(answer.dialog_step_id, bot, message)
        elif answer.refund_step_id:
            # sequence = answer.refund_step_id.sequence
            step = answer.refund_step_id
            if self.input_step_id:
                return None
            self.write({'last_step_id': step.id})
            if not answer.refund_step_id.viber_get_response(
                    conversation=self, bot=bot, message=message):
                self.write({'last_step_id': step.id})
                return None
            if step.select_flow in ['sale', 'survey'] or self.input_step_id:
                return None

            # if the step to operator is after button -
            # without run next step before end consultation
            if step.step_type == "forward_operator":
                return super().viber_get_response(bot, message)

            self.viber_next_step(step, bot, message)
        elif answer.notification_id:
            self.send_viber_keyboard_with_buttons(
                answer.notification_id, text, bot=bot)
            self.viber_next_step(self.last_step_id, bot, message)
            return True
        return super().viber_get_response(bot, message)

    def save_viber_model_activity(self, res_model, res_id):
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

    def _save_viber_model_activity(
            self, notification_id, res_model, res_id):
        self.ensure_one()
        self.save_viber_model_activity(
            res_model=res_model, res_id=res_id)
        record = self.env[res_model].sudo().search([
            ('id', '=', res_id)], limit=1)
        for obj in notification_id.related_fields_ids:
            related_record = getattr(record, obj.name)
            if related_record:
                self.save_viber_model_activity(
                    res_model=related_record._name, res_id=related_record.id)

    def do_action_viber_python_click(self, json_data):
        """
        Run python script in viber button
        """
        if not json_data:
            return False

        id_button = json_data.get('id_button')

        if not id_button:
            return False

        button = self.env['kw.chatbot.step.viber.button'].sudo().browse(
            id_button)

        if not button:
            return False

        record = False

        if button.state == 'code':
            self.action_code(record=record, button=button)
            _logger.info("[Viber Button] - Run Python Code")

        return True

    def do_viber_action_on_button_click(
            self, json_data, bot=None, message=None):
        button_data = json_data.get('id_button')
        button = self.env['kw.chatbot.step.viber.keyboard'].sudo().browse(
            button_data)
        record_data = json_data.get('id_record')
        if button.notification_id.is_save_button_activity:
            if button.notification_id.model_id and record_data:
                self._save_viber_model_activity(
                    notification_id=button.notification_id,
                    res_model=button.notification_id.model_id.model,
                    res_id=record_data)
        if button.state == 'forward_step':
            return self.viber_next_step(
                self.last_step_id, bot, message,
                **{'next_step': button.forward_step_id})
        if button.state == 'send_notification':
            return self.send_viber_keyboard_with_buttons(
                button.notification_for_send, button.name, button,
                json=json_data, bot=bot)
        record = False
        if button.model_id.model:
            record = self.env[button.notification_model_name].sudo().browse(
                record_data)
        res = False
        if button.state == 'object_write':
            res = self.action_write(button, record)
        if button.state == 'object_create':
            res = self.action_create(button, record)
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
        if res:
            text = button.successful_notification
        else:
            text = button.unsuccessful_notification
        if text and record:
            text = button.notification_id.render_message(
                message=text, record=record)
        else:
            clean = re.compile('<.*?>')
            text = re.sub(clean, '', text)
        self.send_message(text=text)
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

    def action_code(self, button, record):
        eval_context = self._get_eval_context()
        safe_eval(button.code.strip(), eval_context, mode="exec", nocopy=True)
        return eval_context.get('action')

    def _get_eval_context(self):
        if self.sender_id.user_id:
            self.env.user = self.sender_id.user_id

        return_value = {
            'datetime': tools.safe_eval.datetime,
            'time': tools.safe_eval.time,
            'sender_user': self.sender_id.user_id,
            'sender_partner': self.sender_id.partner_id,
            'conversation': self,
            'env': self.env,
            'context': self.env.context,
            'float_compare': float_compare,
            'log': _logger.info,
            'UserError': UserError}

        return return_value

    def action_create(self, button, record):
        eval_context = self._get_eval_context()
        vals = button.fields_lines.eval_value(eval_context=eval_context)
        res = {line.update_field_id.name: vals[line.id]
               for line in button.fields_lines}
        res = self.env[button.target_model_id.model].create(res)
        if button.link_field_id:
            record = self.env[self.model_id.model].browse(
                self._context.get('active_id'))
            if button.link_field_id.ttype in ['one2many', 'many2many']:
                record.write({button.link_field_id.name: res.mapped('id')})
            else:
                record.write({button.link_field_id.name: res.id})
        return res

    def action_write(self, button, record):
        for action in button.fields_lines:
            _logger.info(f'action.value: {action.value}')
            if action.evaluation_type == 'value':
                res = record.sudo().write({
                    action.update_field_id.name: action.value})
                _logger.info(f'res: {res}')
            if action.evaluation_type == 'equation':
                # get eval context
                eval_context = self._get_eval_context()
                eval_context['record'] = record
                eval_context['model'] = button.model_id.model
                eval_context['self'] = self
                eval_context['env'] = self.env
                expr = safe_eval(action.value, eval_context)
                res = record.sudo().write({action.update_field_id.name: expr})
        return res

    def send_viber_keyboard_with_buttons(
            self, kw_notification, text, button=False, json=False, bot=False):
        record_set = self.env[kw_notification.model_id.model].sudo().search([])
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
                employee_id = self.env['hr.employee'].sudo().search([
                    ('user_id', '=', self.sender_id.user_id.id)], limit=1)
                extra_domain = \
                    [(check_personal_field.model_field_id.name, '=',
                      employee_id.id)]
            elif check_personal_field.model_field_id.relation == \
                    'res.partner':
                extra_domain = \
                    [(check_personal_field.model_field_id.name, '=',
                      self.sender_id.partner_id.id)]
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
                # else:
                #     record_set = \
                #         self.env[kw_notification.model_id.model].search(
                #             [(button.child_field_id.name, '=',
                #               button.id_record)])
            if not record_set and button.uns_notification_for_send:
                return self.send_viber_keyboard_with_buttons(
                    button.uns_notification_for_send, button.name,
                    button, bot=bot)
        if check_personal_field:
            record_set = record_set.filtered_domain(extra_domain)
        return self.viber_notification_message_send(
            record_set, kw_notification, bot)

    def send_only_button_notification(self, record_set, kw_notification):
        buttons = []
        for record in record_set:
            button_name = kw_notification.prepare_notification_text(
                record=record)
            for button in kw_notification.viber_button_ids.filtered(
                    lambda x: not x.send_last):
                call_back = {
                    'type': 'notification',
                    'id_record': record.id,
                    'id_button': button.id,
                    'id_conversation': self.id}
                buttons.append(
                    self.last_step_id.viber_button_keyboard_values(
                        name=button_name,
                        action_body=str(call_back)))
        for button in kw_notification.viber_button_ids.filtered(
                lambda x: x.send_last):
            if record_set:
                call_back = {
                    'type': 'notification',
                    'id_record': record_set[0].id,
                    'id_button': button.id,
                    'id_conversation': self.id}
                buttons.append(
                    self.last_step_id.viber_button_keyboard_values(
                        name=button.name,
                        action_body=str(call_back)))
        _logger.info(buttons)
        if buttons:
            self.send_rich_media_buttons_in_batches(buttons)
        if not record_set:
            self.send_message(text=kw_notification.message_not_found)
        return True

    def viber_notification_message_send(
            self, record_set, kw_notification, bot):
        self_sudo = kw_notification.sudo()
        record_set = self.viber_filtered_notification_record(
            record_set=record_set, kw_notification=kw_notification)

        if len(record_set) > 100:
            return self.send_message(
                text='Many records. Create the correct notification')
        if kw_notification.sorted_field_id:
            record_set = record_set.sorted(
                kw_notification.sorted_field_id.name)

        if self_sudo.send_only_button \
                and self_sudo.viber_button_count <= 1:
            return self.send_only_button_notification(
                record_set=record_set, kw_notification=self_sudo)
        for record in record_set:
            _logger.info(record)
            self_sudo.notification_message_send(
                records=record, conversation_ids=self,
                **{'sender_user': self.sender_id.user_id, 'bot': bot})
            buttons, rich_media = [], ''
            for button in kw_notification.viber_button_ids.filtered(
                    lambda x: not x.send_last):
                call_back = {
                    'type': 'notification',
                    'id_record': record.id,
                    'id_button': button.id,
                    'id_conversation': self.id}
                buttons.append(self.last_step_id.viber_button_keyboard_values(
                    name=button.name,
                    action_body=str(call_back)))
                rich_media = self.last_step_id.get_viber_rich_media(
                    text=False, buttons=buttons)
            if rich_media:
                self.send_message(text='rich_media', rich_media=rich_media)
        buttons, rich_media = [], ''
        for button in kw_notification.viber_button_ids.filtered(
                lambda x: x.send_last):
            if record_set:
                call_back = {
                    'type': 'notification',
                    'id_record': record_set[0].id,
                    'id_button': button.id,
                    'id_conversation': self.id}
                buttons.append(
                    self.last_step_id.viber_button_keyboard_values(
                        name=button.name,
                        action_body=str(call_back)))
                rich_media = self.last_step_id.get_viber_rich_media(
                    text=False, buttons=buttons)
        if rich_media:
            self.send_message(text='rich_media', rich_media=rich_media)
        if not record_set:
            self.send_message(text=kw_notification.message_not_found)
        return True

    def viber_filtered_notification_record(self, record_set, kw_notification):
        if kw_notification.notification_filtered_fields_ids:
            for f in kw_notification.notification_filtered_fields_ids.sorted(
                    'sequence'):
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
        return record_set

    def viber_out_message(self, text=False):
        self.ensure_one()
        if not self.wired_conversation_id and not self.operator_live_id:
            return super(Conversation, self).viber_out_message(text)
        return None

    # pylint: disable=R1710
    def viber_next_step(self, step, bot, message, next_step=None):
        if not next_step:
            next_step = step.go_to_step_id
        for obj in next_step:
            if obj.viber_get_response(
                    conversation=self, bot=bot, message=message):
                if self.input_step_id or obj.step_type == 'forward_operator':
                    self.write({
                        'is_viber_send': True,
                        'last_step_id': obj.id, })
                    break
                elif obj.step_type == 'request_notification':
                    return False
                else:
                    self.viber_next_step(obj, bot, message)

    def viber_does_not_found(self):
        if not self.wired_conversation_id and \
                not self.chat_id.is_consultant_chat and \
                not self.operator_live_id:
            return super(Conversation, self).viber_does_not_found()
        return None
