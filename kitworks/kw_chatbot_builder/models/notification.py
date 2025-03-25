# flake8: noqa: E501
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Notification(models.Model):
    _inherit = 'kw.chatbot.notification'

    is_save_button_activity = fields.Boolean(
        default=False, string='Save Button Activity')
