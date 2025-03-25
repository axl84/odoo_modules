import logging
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class CheckboxOfflineMode(models.TransientModel):
    _name = 'kw.checkbox.offline.mode.wizard'
    _description = 'Offline Mode Wizard'

    pos_config_id = fields.Many2one(
        comodel_name='pos.config', readonly=True, )
    kw_checkbox_cash_register_ids = fields.Many2many(
        comodel_name='kw.checkbox.cash.register',
        string='Cash register', readonly=True, )

    @api.model
    def default_get(self, vals):
        res = super().default_get(vals)
        active_id = self.env.context.get('active_id')
        res['pos_config_id'] = active_id
        res['kw_checkbox_cash_register_ids'] = self.env['pos.config'].search(
            [('id', '=', active_id)]).kw_checkbox_cash_register_ids
        for cash_register in self.env['pos.config'].search(
                [('id', '=', active_id)]).kw_checkbox_cash_register_ids:
            cash_register.count_offline_codes = \
                len(self.env['kw.checkbox.offline.code'].search(
                    [('cash_register_id', '=', cash_register.id)]).ids)
        return res

    def check_count_of_codes(self):
        self.ensure_one()
        for cash_register in self.kw_checkbox_cash_register_ids:
            if cash_register.count_offline_codes == 0:
                raise exceptions.ValidationError(
                    _('You do not have offline code, please get it'))
        self.pos_config_id.go_offline()
