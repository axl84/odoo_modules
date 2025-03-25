# flake8: noqa: E501
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    # pylint: disable=R1702,R0911,R0912
    def kw_prepare_entity_data(self):
        data = super().kw_prepare_entity_data()
        if self.kw_conversation_id:
            button = self.kw_conversation_id.tg_button_for_survey
            model = self.kw_conversation_id.button_model
            if model:
                bt_record = self.env[model].sudo().search([
                    ('id', '=', self.kw_conversation_id.button_res_id)])
            if button and button.related_fields_id and bt_record:
                data[button.related_fields_id.relation_field] = bt_record.id
        return data
