import logging
import json

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    excise = fields.Char()
    pack_excise_ids = fields.One2many(
        comodel_name='kw.pos.excise', inverse_name='order_line_id')
    is_excise_product = fields.Boolean(compute='_compute_is_excise_product')

    def _compute_is_excise_product(self):
        for obj in self:
            is_excise_product = False
            product_id = obj.product_id
            if product_id and product_id.is_excise_product:
                is_excise_product = True
            obj.is_excise_product = is_excise_product

    @api.model_create_multi
    def create(self, vals):
        res = super(PosOrderLine, self).create(vals)
        for obj in res:
            if not obj.excise:
                continue
            excises_chr = []
            try:
                json_ready_string = obj.excise.replace("'", '"')
                json_data = json.loads(json_ready_string)
                for exc in json_data:
                    excises_chr.append(
                        (0, 0, {'name': exc.get('lot_name', '')}))
            except json.JSONDecodeError as e:
                _logger.info(e)
            finally:
                obj.pack_excise_ids = excises_chr
        return res

    def get_pack_excise_lines_ref(self, line_ref_id):
        if not line_ref_id:
            return []
        order_line_id = self.browse(line_ref_id)
        if order_line_id:
            return [{'lot_name': ex.name}
                    for ex in order_line_id.pack_excise_ids]
        return []
