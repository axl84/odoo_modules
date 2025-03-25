import logging
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Dialog(models.Model):
    _inherit = 'kw.chatbot.dialog'


class Step(models.Model):
    _name = "kw.chatbot.step"
    _inherit = [
        'kw.chatbot.step',
        'kw.chatbot.survey.mixin']

    select_flow = fields.Selection(
        selection_add=[('survey', 'Survey')], ondelete={'survey': 'cascade'}, )
    is_quiz = fields.Boolean(
        compute_sudo=True,
        compute='_compute_quiz_name')

    def _compute_quiz_name(self):
        for obj in self:
            if obj.select_flow == 'survey':
                obj.is_quiz = True
                for alias_id in obj.alias_ids:
                    if alias_id.name == '/start_quiz':
                        alias_id.name = f'/start_quiz_{obj.id}'
            else:
                obj.is_quiz = False

    @api.onchange('select_flow')
    def onchange_select_flow(self):
        for obj in self:
            obj._compute_quiz_name()

    @api.onchange('survey_id')
    def onchange_survey_id(self):
        for obj in self:
            step_alias = self.env['kw.chatbot.step.alias']
            obj.alias_ids = [(6, 0, step_alias)]
            if obj.survey_id:
                if obj and obj.dialog_id:
                    step_alias = step_alias.create({
                        'name': '/start_quiz',
                        'step_id': obj.id,
                        'dialog_id': obj.dialog_id.id, })
            if step_alias:
                obj.alias_ids = [(6, 0, step_alias.ids)]

    @api.constrains('survey_id')
    def check_survey_questions(self):
        question_ids = self.survey_id.question_ids.filtered(
            lambda x: x.question_type in ['multiple_choice', 'matrix'])
        if question_ids:
            raise exceptions.ValidationError(
                _('We can not use survey with question type'
                  ' "multiple_choice" and "matrix"'))
