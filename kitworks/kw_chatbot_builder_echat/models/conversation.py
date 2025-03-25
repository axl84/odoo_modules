import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    def echat_update_contact(self, text, text_resp):
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

    # pylint: disable=R0911,R0912
    def echat_get_response(self, jsonrequest):
        if self.dialog_id.bots_type == 'is_consultant_bot':
            return super().echat_get_response(jsonrequest)

        text = jsonrequest['message']['text']

        # self.is_echat_send = False

        step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
            ('name', '=', text), ])
        trig_step = self.env['kw.chatbot.step'].sudo().search([
            ('alias_ids', 'in', step_alias.ids),
            ('dialog_id', '=', self.dialog_id.id)])
        if not trig_step and not self.wired_conversation_id:
            if not self.dialog_id.wait_start_message and text != '/end':
                _logger.info('я не знайшов стартового '
                             'кроку і змінюю на /start')
                trig_step = self.env['kw.chatbot.step'].sudo().search([
                    ('dialog_id', '=', self.dialog_id.id)]).sorted(
                    key=lambda r: r.sequence)[0]

        if self.input_step_id:
            lang = self.sender_id.partner_id.lang
            text_resp = self.input_step_id.with_context(
                lang=lang).msg_after_update_contact_field
            if self.input_step_id.step_type == 'update_contact_field':

                self.echat_update_contact(text=text, text_resp=text_resp)

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
            self.echat_next_step(self.last_step_id, text)
            return True

        if trig_step:
            _logger.info('33 conv')
            if trig_step.echat_get_response(
                    conversation=self, message=text):
                self.write({
                    'is_echat_send': True,
                    'last_step_id': trig_step.id, })
                if self.input_step_id:
                    _logger.info('40 conv')
                    return None

            # if current step operator - run without next step before end conv
            if trig_step.step_type == "forward_operator":
                return super().echat_get_response(jsonrequest)

            self.echat_next_step(trig_step, text)
            return True

        if text == '/end' and self.last_step_id:
            self.echat_next_step(self.last_step_id, text)
            return True
        res = super().echat_get_response(jsonrequest)
        if not self.is_echat_send:
            self.send_message(
                text=(self.dialog_id.not_found_msg.strip()))
        return res

    def echat_next_step(self, step, text, next_step=None):
        if not next_step:
            next_step = step.go_to_step_id
        _logger.info('next_step %s', next_step.name)
        for obj in next_step:
            if obj.echat_get_response(
                    conversation=self, message=text):
                if self.input_step_id or obj.step_type == 'forward_operator':
                    self.write({'is_echat_send': True,
                                'last_step_id': obj.id, })
                    _logger.info('break')
                    _logger.info(
                        'self.input_step_id %s', self.input_step_id.name
                        if self.input_step_id else None)
                    _logger.info('obj.step_type %s', obj.step_type)
                    break
                elif obj.step_type == 'update_contact_field':
                    self.write({'is_echat_send': True,
                                'last_step_id': obj.id, })
                    break
                else:
                    self.echat_next_step(obj, text)

    def echat_out_message(self, text=False):
        if not self.wired_conversation_id and not self.operator_live_id:
            res = super(Conversation, self).echat_out_message(text=text)
            return res
        return False


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    @api.model
    def create(self, vals_list):
        if vals_list.get('text') == '/end' \
                and vals_list.get('conversation_id'):
            conversation_id = self.env['kw.chatbot.conversation'].search(
                [('id', '=', vals_list.get('conversation_id'))])
            if conversation_id.wired_conversation_id:
                conv_id = conversation_id.wired_conversation_id
                obj = super().create(vals_list)
                if conv_id.chat_id.provider == 'echat' \
                        and conv_id.last_step_id \
                        and conv_id.last_step_id.go_to_step_id:
                    conv_id.echat_next_step(
                        step=conv_id.last_step_id,
                        next_step=conv_id.last_step_id.go_to_step_id,
                        text='')
                return obj
        return super().create(vals_list)
