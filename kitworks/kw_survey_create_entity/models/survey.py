import logging

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

SURVEY_FIELD_DOMAINS = {
    'text_box': ['html', 'text', ],
    'char_box': ['char', 'email', ],
    'numerical_box': ['integer', 'float', 'monetary', ],
    'date': ['date', 'datetime', ],
    'datetime': ['datetime', ],
    'simple_choice': ['many2one', 'selection', 'boolean', ],
    'multiple_choice': ['many2many', ],
    'file': ['binary', ],
    'matrix': []
}


class Survey(models.Model):
    _inherit = 'survey.survey'

    kw_is_entity_creator = fields.Boolean(
        string='Create entity', )
    kw_entity_model_id = fields.Many2one(
        comodel_name='ir.model', string='Entity model', )


class SurveyLabel(models.Model):
    _inherit = 'survey.question.answer'

    kw_survey_answer_value = fields.Char()


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    kw_is_entity_creator = fields.Boolean(
        string='Create entity', related='survey_id.kw_is_entity_creator', )
    kw_entity_model_id = fields.Many2one(
        comodel_name='ir.model', string='Entity model',
        related='survey_id.kw_entity_model_id', )
    kw_entity_model_name = fields.Char(
        related='kw_entity_field_id.relation', )
    kw_entity_field_ids = fields.Many2many(
        comodel_name='ir.model.fields', invisible=True,
        compute='_compute_kw_entity_field_ids', )
    kw_entity_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Entity field',
        domain='[(\'id\',\'in\',kw_entity_field_ids)]')
    kw_is_entity_attachment = fields.Boolean(
        string='Add to attachments', )
    kw_is_filter_domain = fields.Boolean(
        compute_sudo=True, compute='_compute_filter_domain')
    kw_filter_domain = fields.Char(string='Domain')

    def _compute_filter_domain(self):
        for obj in self:
            obj.kw_is_filter_domain = False
            if obj.kw_entity_field_id.ttype in ['many2one', 'many2many']:
                obj.kw_is_filter_domain = True

    @api.onchange('question_type', )
    def _compute_kw_entity_field_ids(self):
        for obj in self:
            if not obj.kw_entity_model_id:
                obj.kw_entity_field_ids = [(6, 0, [])]
                continue
            ids = self.env['ir.model.fields'].sudo().search([
                ('model_id', '=', obj.kw_entity_model_id.id),
                ('ttype', 'in', SURVEY_FIELD_DOMAINS[obj.question_type]),
            ]).ids
            obj.kw_entity_field_ids = [(6, 0, ids)]

    @api.onchange('kw_entity_field_id', 'kw_filter_domain', )
    def reload_value_suggested(self):
        self.ensure_one()
        domain = []
        if self.kw_filter_domain:
            domain = safe_eval(self.kw_filter_domain)
        if self.kw_entity_field_id and self.question_type in \
                ['simple_choice', 'multiple_choice'] and \
                self.kw_entity_field_id.ttype \
                in SURVEY_FIELD_DOMAINS[self.question_type]:
            value = [(5, )]
            if self.kw_entity_field_id.ttype == 'boolean':
                value.append([0, 0, {
                    'value': 'True', 'kw_survey_answer_value': 1}])
                value.append([0, 0, {
                    'value': 'False', 'kw_survey_answer_value': 0}])
            elif self.kw_entity_field_id.ttype == 'many2one':
                model_name = self.kw_entity_field_id.relation
                for x in self.env[model_name].search(domain):
                    value.append([0, 0, {
                        'value': x.name, 'kw_survey_answer_value': x.id}])
            elif self.kw_entity_field_id.ttype == 'selection':
                selection = self.env[self.kw_entity_model_id.model]._fields[
                    self.kw_entity_field_id.name].selection
                if callable(selection):
                    selection = selection(self)
                if selection:
                    for x in selection:
                        value.append([0, 0, {
                            'value': x[1], 'kw_survey_answer_value': x[0]}])
            elif self.kw_entity_field_id.ttype == 'many2many':
                model_name = self.kw_entity_model_id.model
                for x in self.env[model_name].search(domain):
                    value.append([0, 0, {
                        'value': x.name, 'kw_survey_answer_value': x.id}])
            self.suggested_answer_ids = value
