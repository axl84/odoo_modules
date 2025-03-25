import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    survey_id = fields.Many2one(
        comodel_name='survey.survey', string='Survey', ondelete='cascade', )
    question_and_page_ids = fields.Many2many(
        comodel_name='survey.question', string='Sections and Questions', )
    survey_question_id = fields.Many2one(
        comodel_name='survey.question', string='Sections Question', )
    user_input_id = fields.Many2one(
        comodel_name='survey.user_input', string='User Input', )
    is_quiz_start = fields.Boolean()
    survey_search_value = fields.Char()

    def get_survey_record(self):
        self.ensure_one()
        if self.user_input_id:
            return self.env[self.user_input_id.kw_entity_model].sudo().search(
                [('id', '=', self.user_input_id.kw_entity_res_id)], limit=1)
        return False

    def close_quiz(self):
        self.ensure_one()
        self.sudo().write({
            'is_quiz_start': False,
            'survey_question_id': False,
            'question_and_page_ids': [(6, 0, [])],
            'user_input_id': False,
            'tg_button_for_survey': False,
            'survey_id': False, })
