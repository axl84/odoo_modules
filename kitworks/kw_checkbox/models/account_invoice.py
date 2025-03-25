import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    kw_checkbox_receipt_ids = fields.One2many(
        comodel_name='kw.checkbox.receipt', inverse_name='invoice_id', )
    kw_checkbox_is_receipt = fields.Boolean(
        compute='_compute_kw_checkbox_is_receipt', )

    def _compute_kw_checkbox_is_receipt(self):
        for obj in self:
            obj.kw_checkbox_is_receipt = obj.kw_checkbox_receipt_ids.ids

    # @api.model
    # def create(self, vals_list):
    #     res = super(AccountInvoice, self).create(vals_list)
    #     for i, v in enumerate(vals_list.get('invoice_line_ids', [])):
    #         if v[2].get('kw_checkbox_excise_barcode_ids'):
    #             res.sudo(
    #             ).invoice_line_ids[i].kw_checkbox_excise_barcode_ids \
    #                 = [(6, 0, v[2].get(
    #                     'kw_checkbox_excise_barcode_ids')[0][2])]
    #     return res

    @api.model
    def create(self, vals_list):
        res = super(AccountInvoice, self).create(vals_list)
        for val in vals_list.get('invoice_line_ids', []):
            for invoice_line_id in res.invoice_line_ids:
                if invoice_line_id.product_id.id == val[2].get(
                        'product_id') and val[2].get(
                            'kw_checkbox_excise_barcode_ids'):
                    invoice_line_id.kw_checkbox_excise_barcode_ids = [(
                        6, 0, val[2].get('kw_checkbox_excise_barcode_ids')
                        [0][2])]
        return res


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    kw_checkbox_excise_barcode_ids = fields.Many2many(
        comodel_name='kw.excise.barcode',
        string='Excise Barcode', )

    def kw_checkbox_good(self):
        self.ensure_one()
        return {
            'quantity': self.quantity * 1000,
            'good': {
                'code': self.product_id.id, 'name': self.product_id.name,
                'price': self.price_subtotal * 100}, }
