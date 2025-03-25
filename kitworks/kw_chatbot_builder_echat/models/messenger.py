import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Messenger(models.Model):
    _inherit = 'kw.chatbot.messenger'

    echat_msg_war = fields.Text(
        readonly=True, string='Warning',
        default='It is not possible to build a dialogue for '
                '"E-Chat" using buttons')
