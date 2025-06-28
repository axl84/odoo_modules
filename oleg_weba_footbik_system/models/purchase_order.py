import logging
from datetime import date

from odoo import models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        res = super().button_confirm()

        for rec in self:
            if rec.order_line:  # If there are products
                try:
                    rec.action_create_invoice()
                    rec.invoice_ids[0].invoice_date = date.today()
                    rec.invoice_ids[0].action_post()
                except UserError as e:
                    _logger.error(
                        msg=f"Invoice was not created from purchase.order: {rec.id}."
                            f"Error: {e}")

        return res
