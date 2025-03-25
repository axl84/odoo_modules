import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = 'res.users'

    is_chatbot_consultant = fields.Boolean()
