import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ChatbotSurveyMixin(models.AbstractModel):
    _inherit = 'kw.chatbot.survey.mixin'

    def kw_save_answer(self, conversation, text):
        if conversation.survey_question_id.question_type != 'file':
            return super().kw_save_answer(conversation, text)
        return False
