# flake8: noqa: E501

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

INPUTS = ['free_input_single', 'question_name',
          'question_email', 'update_contact_field']


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    whatsapp_button_ids = fields.One2many(
        comodel_name='kw.chatbot.step.whatsapp.button',
        inverse_name='step_id', )

    def _compute_answer_whatsapp(self):
        for obj in self:
            obj.whatsapp_button_ids = False
            ids = []
            for ans in obj.answer_ids.sorted('sequence'):
                if not ans.name:
                    continue
                keyboard = self.env['kw.chatbot.step.whatsapp.button'].sudo(
                ).create({'step_id': self.id, 'name': ans.name})
                keyboard.name = ans.name
                languages = self.env['res.lang'].search(
                    [('active', '=', 'true')])
                for lang in languages.mapped('code'):
                    lang_answer = ans.with_context(lang=lang).name
                    if lang_answer:
                        keyboard.with_context(lang=lang).name = lang_answer
                ids.append(keyboard.id)
            obj.whatsapp_button_ids = [(6, 0, ids)]


    def whatsapp_get_response(self, conversation, message):
        self.ensure_one()
        _logger.info(self.step_type)

        if conversation.dialog_id:
            if self.step_type in INPUTS:
                conversation.send_message(text=self.text)
                conversation.input_step_id = self.id
                conversation.last_step_id = self.id
                return True
        if self.step_type == 'create_lead':
            self.create_lead(conversation)
            conversation.whatsapp_next_step(self, message)
            return True
        buttons = []
        if self.whatsapp_button_ids:
            for k in self.whatsapp_button_ids:
                buttons.append({'id': k.id, 'title': k.name})
        if self.step_type == 'forward_operator':
            buttons.append({'id': '/end', 'title': '/end'})
            if not self.is_not_send_send_text:
                conversation.send_message(text=self.text, button=buttons)
            _operator = self.operator_forward(conversation, message)

            # go to step redirect_to step_id if the operator is not available
            if not _operator and self.redirect_step_id:
                conversation.is_no_reply = True
                step = self.redirect_step_id
                step.whatsapp_get_response(conversation, message)
                return True

            if not _operator:
                conversation.whatsapp_next_step(self.redirect_step_id, message)
            return True

        conversation.send_message(text=self.text, button=buttons)
        conversation.write({
            'is_whatsapp_send': True,
            'last_step_id': self.id})
        return True


class StepWhatsAppKeyboard(models.Model):
    _name = 'kw.chatbot.step.whatsapp.button'
    _description = 'Step WhatsApp Keyboard'

    name = fields.Char(
        required=True, string='Code', )
    sequence = fields.Integer(default=1, )
    step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    active = fields.Boolean(
        default=True, )
    is_location = fields.Boolean(
        default=False, string='Location Request', )


class ChatbotDialogAnswer(models.Model):
    _inherit = 'chatbot.dialog.answer'

    @api.model
    def create(self, vals_list):
        result = super(ChatbotDialogAnswer, self).create(vals_list)
        for obj in result:
            if obj.dialog_step_id:
                obj.dialog_step_id._compute_answer_whatsapp()
        return result

    def write(self, vals):
        result = super(ChatbotDialogAnswer, self).write(vals)
        for obj in self:
            if vals.get('name') or vals.get('sequence') and obj.dialog_step_id:
                obj.dialog_step_id._compute_answer_whatsapp()
        return result

    def unlink(self):
        dialog_step_id = self.dialog_step_id
        result = super(ChatbotDialogAnswer, self).unlink()
        if dialog_step_id:
            dialog_step_id._compute_answer_whatsapp()
        return result
