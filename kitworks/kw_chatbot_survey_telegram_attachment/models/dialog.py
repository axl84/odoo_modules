import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Dialog(models.Model):
    _inherit = 'kw.chatbot.dialog'


class Step(models.Model):
    _inherit = 'kw.chatbot.step'
