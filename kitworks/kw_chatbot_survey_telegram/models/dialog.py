import logging

from telebot import types
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Dialog(models.Model):
    _inherit = 'kw.chatbot.dialog'


# pylint: disable=lost-exception
class Step(models.Model):
    _name = 'kw.chatbot.step'
    _inherit = ['kw.chatbot.step', 'kw.chatbot.survey.mixin']

    # pylint: disable=R1705
    def telegram_get_response(self, conversation, bot, message):
        self.ensure_one()
        text = conversation.telegram_get_message_data(message)
        if not text:
            return False
        if self.select_flow == 'survey':
            if '/start_quiz' not in text:
                conversation.write({
                    'survey_id': False,
                    'survey_question_id': False,
                    'user_input_id': False,
                    'question_and_page_ids': False,
                    'is_quiz_start': False,
                })
                markup, buttons = None, []
                markup = types.InlineKeyboardMarkup()
                lang = conversation.sender_id.partner_id.lang
                text_start = self.with_context(
                    lang=lang).name_button_start_survey
                text_end = self.with_context(
                    lang=lang).kw_close_quiz_button_name
                btn = types.InlineKeyboardButton(
                    text=text_start,
                    callback_data=f'/start_quiz_{self.id}', )
                markup.add(btn)
                btn = types.InlineKeyboardButton(
                    text=text_end,
                    callback_data='/end_quiz', )
                markup.add(btn)
                markup.add(*buttons)
                text = self.with_context(lang=lang).message_start_survey
                conversation.send_message(
                    text=text,
                    reply_markup=markup, buttons=buttons, )
            else:
                if self.is_survey_send_text:
                    conversation.send_message(
                        text=self.text,
                        reply_markup=types.ReplyKeyboardRemove(), )
                self.start_quiz(
                    conversation=conversation, bot=bot, message=message,
                    step_id=self.go_to_step_id)
            return False
        else:
            return super().telegram_get_response(
                conversation=conversation, bot=bot, message=message)


class StepTelegramButton(models.Model):
    _name = 'kw.chatbot.step.telegram.button'
    _inherit = ['kw.chatbot.step.telegram.button', 'kw.chatbot.survey.mixin']

    state = fields.Selection(
        selection_add=[('survey', 'Survey')],
        ondelete={'survey': 'set default'}, )
    survey_next_step_id = fields.Many2one(
        string="Next Step",
        comodel_name='kw.chatbot.step', )
    survey_next_notification_id = fields.Many2one(
        string="Next Notification",
        comodel_name='kw.chatbot.notification', )
    related_fields_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        compute_sudo=True,
        relation='kw_chatbot_telegram_button_related_fields_rel',
        compute='_compute_related_fields')
    related_fields_id = fields.Many2one(
        comodel_name='ir.model.fields', )

    def _compute_related_fields(self):
        for obj in self:
            obj.related_fields_ids = [(6, 0, [])]
            if obj.model_id:
                model_fields = self.env['ir.model.fields'].search([
                    ('model_id', '=', obj.model_id.id)])
                related_fields = model_fields.filtered(
                    lambda x: x.relation == obj.entity_model_id.model
                    and x.relation_field)
                obj.related_fields_ids = [(6, 0, related_fields.ids)]

    @api.onchange('survey_id', 'model_id')
    def _onchange_related_fields(self):
        for obj in self:
            obj._compute_related_fields()
            obj.related_fields_id = False

    @api.onchange('state')
    def _onchange_state(self):
        res = super()._onchange_state()
        for rec in self:
            if rec.state == 'survey':
                rec.model_id = rec.notification_id.model_id.id
        return res
