import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    kw_is_entity_creator = fields.Boolean(
        string='Create entity', related='survey_id.kw_is_entity_creator', )
    kw_entity_model_id = fields.Many2one(
        comodel_name='ir.model', string='Entity model',
        related='survey_id.kw_entity_model_id', )
    kw_entity_model = fields.Char(
        string='Model Name', related='survey_id.kw_entity_model_id.model')
    kw_entity_res_id = fields.Many2oneReference(
        string='Record ID', model_field='kw_entity_model', )
    kw_entity_reference = fields.Char(
        string='Reference', compute='_compute_kw_entity_reference',
        readonly=True, store=False, )

    @api.depends('kw_entity_model', 'kw_entity_res_id')
    def _compute_kw_entity_reference(self):
        for obj in self:
            obj.kw_entity_reference = '%s,%s' % (
                obj.kw_entity_model, obj.kw_entity_res_id)

    # pylint: disable=R0912
    def kw_prepare_entity_data(self):
        self.ensure_one()
        data = {}
        lines = self.user_input_line_ids.filtered(
            lambda x: x.question_id.kw_entity_field_id)
        for line in lines:
            field_id = line.question_id.kw_entity_field_id
            if data.get(field_id.name):
                continue
            if line.answer_type == 'text_box':
                data[field_id.name] = line.value_text_box
            elif line.answer_type == 'char_box':
                data[field_id.name] = line.value_char_box
            elif line.answer_type == 'numerical_box':
                data[field_id.name] = line.value_numerical_box
            elif line.answer_type == 'date':
                data[field_id.name] = line.value_date
            elif line.answer_type == 'datetime':
                data[field_id.name] = line.value_datetime
            elif line.answer_type == 'suggestion':
                if field_id.ttype == 'many2one':
                    record = self.env[field_id.relation].search([], )
                    value_id = record.filtered(
                        lambda x: x.name == line.suggested_answer_id.value)
                    data[field_id.name] = value_id[0].id
                elif field_id.ttype == 'selection':
                    selection_ids = field_id.selection_ids.filtered(
                        lambda x: x.name == line.suggested_answer_id.value)
                    if selection_ids:
                        data[field_id.name] = selection_ids[0].value
                else:
                    data[field_id.name] = line.suggested_answer_id.value
            elif line.answer_type == 'file':
                if not line.question_id.kw_is_entity_attachment:
                    for value_file in line.value_file_ids:
                        data[field_id.name] = value_file.datas
        return data

    def _mark_done(self):
        result = super()._mark_done()
        for obj in self:
            if not obj.kw_is_entity_creator:
                continue
            obj = obj.sudo()
            data = obj.kw_prepare_entity_data()
            if isinstance(data, dict) and data.get('create_uid'):
                entity = self.env[obj.kw_entity_model_id.model].sudo(
                ).with_user(data.get('create_uid')).create(data)
            else:
                entity = self.env[obj.kw_entity_model_id.model].sudo().create(
                    data)
            lines = obj.user_input_line_ids.filtered(
                lambda x: x.question_id.kw_is_entity_attachment)
            for line in lines:
                for value_file in line.value_file_ids:
                    value_file.copy({
                        'res_model': line.question_id.kw_entity_model_id.model,
                        'res_id': entity.id, })
            obj.kw_entity_res_id = entity.id
        return result


class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    kw_answer_display = fields.Char(
        string='Answer', compute='_compute_kw_answer_display', )

    def get_kw_answer_display(self):
        self.ensure_one()
        result = ''
        if self.answer_type == 'text_box':
            result = self.value_text_box[:100]
        elif self.answer_type == 'char_box':
            result = self.value_char_box
        elif self.answer_type == 'numerical_box':
            result = '{}'.format(self.value_numerical_box)
        elif self.answer_type == 'date':
            result = '{}'.format(self.value_date.strftime('%Y-%m-%d'))
        elif self.answer_type == 'datetime':
            result = \
                '{}'.format(self.value_datetime.strftime('%Y-%m-%d %H:%M'))
        elif self.answer_type == 'suggestion':
            result = '{}'.format(self.suggested_answer_id.value)
        elif self.answer_type == 'file':
            result = self.filename
        return result

    def _compute_kw_answer_display(self):
        for obj in self:
            obj.kw_answer_display = obj.get_kw_answer_display()
