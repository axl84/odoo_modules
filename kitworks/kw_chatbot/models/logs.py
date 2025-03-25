import json
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Log(models.Model):
    _name = 'kw.chatbot.log'
    _description = 'Logs'
    _order = 'create_date DESC'

    name = fields.Char()

    url = fields.Char()

    method = fields.Char()

    headers = fields.Char()

    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger', )
    create_date = fields.Datetime(
        default=fields.Datetime.now)
    body = fields.Text()

    chat_id = fields.Many2one(
        comodel_name='kw.chatbot.chat', )
    dialog_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog', )
    sender_id = fields.Many2one(
        comodel_name='kw.chatbot.sender', )
    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', )

    @staticmethod
    def try_convert2formatted_json(val):
        if isinstance(val, dict):
            try:
                val = json.dumps(val, indent=2, ensure_ascii=False)
            except Exception as e:
                _logger.debug(e)
        elif isinstance(val, str):
            try:
                val = json.dumps(json.loads(val), indent=2, ensure_ascii=False)
            except Exception as e:
                _logger.debug(e)
        return val

    @api.model
    def create(self, vals_list):
        for x in ['body', ]:
            vals_list[x] = self.try_convert2formatted_json(vals_list.get(x))
        return super().create(vals_list)

    def write(self, vals_list):
        for x in ['body', ]:
            if x in vals_list:
                vals_list[x] = self.try_convert2formatted_json(
                    vals_list.get(x))
        return super().write(vals_list)
