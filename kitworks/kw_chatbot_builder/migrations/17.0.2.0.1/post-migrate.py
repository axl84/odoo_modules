import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    for obj in env['kw.chatbot.step'].sudo().search([]):
        obj._compute_name()
