
from odoo import models


class ServerActions(models.Model):
    _inherit = 'ir.actions.server'

    def _run_action_sms_multi(self, eval_context=None):
        if not self.sms_template_id or self._is_recompute():
            return False

        records = eval_context.get('records') or eval_context.get('record')
        if not records:
            return False

        composer = self.env['sms.composer'].with_context(
            default_res_model=records._name,
            default_res_ids=records.ids,
            default_composition_mode='mass',
            default_template_id=self.sms_template_id.id,
        ).create({})
        sms_template = self.sms_template_id
        if sms_template and sms_template.kw_turbosms_sms_or_viber != 'sms':
            composer.kw_turbosms_sms_or_viber = \
                sms_template.kw_turbosms_sms_or_viber
            composer.kw_turbosms_is_transactional = \
                sms_template.kw_turbosms_is_transactional
            composer.kw_turbosms_ttl = sms_template.kw_turbosms_ttl
            composer.kw_turbosms_image_url = sms_template.kw_turbosms_image_url
            composer.kw_turbosms_caption = sms_template.kw_turbosms_caption
            composer.kw_turbosms_action = sms_template.kw_turbosms_action
            composer.kw_turbosms_file_id = sms_template.kw_turbosms_file_id
            composer.kw_turbosms_is_count_clicks = \
                sms_template.kw_turbosms_is_count_clicks
            composer.body = self.env['sms.template']._render_template(
                sms_template.kw_body_viber_sms, records._name, records.ids)[
                records.ids[0]]
        composer.action_send_sms()
        return False
