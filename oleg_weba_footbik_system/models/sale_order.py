import logging

from odoo import models, fields
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_agreement = fields.Boolean(string="Is Agreement")

    def action_confirm(self):
        res = super().action_confirm()

        for rec in self:
            if rec.order_line:  # If there are products
                try:
                    self.env["sale.advance.payment.inv"].with_context({
                        "active_model": "sale.order",
                        "active_ids": [rec.id],
                        "active_id": rec.id,
                        # "default_journal_id": self.company_data['default_journal_sale'].id,
                    }).create({
                        "advance_payment_method": "delivered",
                    }).create_invoices()

                    rec.invoice_ids[0].action_post()
                except UserError as e:
                    _logger.error(
                        msg=f"Invoice was not created from sale.order: {rec.id}."
                            f"Error: {e}")

        return res
