import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    question_type = fields.Selection(
        selection_add=[('file', 'Upload File')])
    upload_multiple_file = fields.Boolean()

    # pylint: disable=R1705
    def validate_question(self, answer, comment=None):
        if self.constr_mandatory and self.question_type == 'file':
            if 'values' in answer and len(answer.get('values')) > 0:
                return {}
            else:
                return {self.id: self.constr_error_msg}
        return super(SurveyQuestion, self).validate_question(answer)


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    # pylint: disable=R1710
    def _save_lines(
            self, question, answer, comment=None, overwrite_existing=True):
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)])
        if question.question_type != 'file':
            return super(SurveyUserInput, self)._save_lines(
                question, answer, comment, overwrite_existing)
        self._save_line_files(question, old_answers, answer)

    def _save_line_files(self, question, old_answers, answers):
        vals = {
            'user_input_id': self.id, 'question_id': question.id,
            'skipped': False, 'answer_type': question.question_type, }
        if answers and answers.get('values') \
                and answers.get('is_answer_update'):
            value_file_lines = [(0, 0, {
                'name': answer.get('file_name'), 'datas': answer.get('data'),
                'type': 'binary', }) for answer in answers.get('values')]
            vals.update({'value_file_ids': value_file_lines})
            if old_answers:
                old_answers.unlink()
            old_answers.create(vals)
        else:
            vals.update({'answer_type': None, 'skipped': True})
        return old_answers


class SurveyUserInputLine(models.Model):
    _inherit = "survey.user_input.line"

    value_upload_file = fields.Char(
        string='Upload Multiple File')
    answer_type = fields.Selection(
        selection_add=[('file', 'Upload file')])
    value_file_ids = fields.Many2many(
        comodel_name='ir.attachment', string='Survey file', readonly=True,)
    filename = fields.Char(
        compute='_compute_filename', )

    @api.depends('value_file_ids')
    def _compute_filename(self):
        for obj in self:
            if not obj.value_file_ids:
                obj.filename = ''
                continue
            filename = ', '.join(
                ['{}'.format(x.name) for x in obj.value_file_ids])
            obj.filename = filename

    @api.constrains('skipped', 'answer_type')
    def _check_answer_type_skipped(self):
        for line in self:
            if line.answer_type != 'file':
                return super(
                    SurveyUserInputLine, line)._check_answer_type_skipped()
        return None
