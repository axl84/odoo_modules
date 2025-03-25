import ast
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Mailing(models.Model):
    _name = 'kw.chatbot.mass.send.bot'
    _description = 'Mass Send Bot'

    text = fields.Text(required=False, string='Text message')
    dialog_id = fields.Many2one(comodel_name='kw.chatbot.dialog')
    kw_filter_domain = fields.Char(string='Filter Domain',
                                   help='Example: [("id", "in", [1,2,3])]')

    @api.model
    def get_or_create(self, messenger, **kwargs):
        _logger.debug(messenger, kwargs)

    def action_send(self):
        for obj in self:
            if obj.kw_filter_domain:
                res_partner_ids = \
                    self.env['res.partner'].search(ast.literal_eval(
                        (obj.kw_filter_domain))).ids
            else:
                res_partner_ids = self.env['res.partner'].search([]).ids
            for con in obj.dialog_id.conversations_ids:
                if con.partner_id.id in res_partner_ids:
                    try:
                        con.send_message(obj.text)
                    except Exception as e:
                        _logger.debug(e)
                else:
                    _logger.debug('Partner not in filter domain')
