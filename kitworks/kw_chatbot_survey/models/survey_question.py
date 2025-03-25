import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    def get_question_data(self):
        self.ensure_one()
        return {
            'is_page': self.is_page,
            'title': self.title,
            'display_name': self.display_name,
            'question_type': self.question_type,
            'sequence': self.sequence,
            'description': self.description,
            'page_id': self.page_id,
            'question_ids': self.question_ids,
            'suggested_answer_ids': [{
                'id': i.id,
                'question_id': i.question_id,
                'sequence': i.sequence,
                'value': i.value,
                'answer_score': i.answer_score,
            } for i in self.suggested_answer_ids],
        }
