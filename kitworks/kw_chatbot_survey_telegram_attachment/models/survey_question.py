import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    kw_telegram_file_error_message = fields.Char(
        string='Telegram Error Message',
        default="You should send file for this question")
