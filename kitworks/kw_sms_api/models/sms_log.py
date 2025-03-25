import json
import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class SmsLog(models.Model):
    _name = 'kw.sms.log'
    _description = 'kw.sms.log'

    provider_id = fields.Many2one(
        comodel_name='kw.sms.provider', required=True, )
    request_url = fields.Char()

    request = fields.Text()

    response = fields.Text()

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
        for x in ['request', 'response']:
            vals_list[x] = self.try_convert2formatted_json(vals_list.get(x))
        return super().create(vals_list)

    def write(self, vals_list):
        for x in ['request', 'response']:
            if x in vals_list:
                vals_list[x] = self.try_convert2formatted_json(
                    vals_list.get(x))
        return super().write(vals_list)
