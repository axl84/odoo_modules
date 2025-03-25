import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    step_alias_ids = env['kw.chatbot.step.alias'].search([
        ('name', '=', '/start_quiz')])
    for step_alias_id in step_alias_ids:
        if step_alias_id.step_id:
            step_alias_id.sudo().write({
                'name': f'/start_quiz_{step_alias_id.step_id.id}'})
