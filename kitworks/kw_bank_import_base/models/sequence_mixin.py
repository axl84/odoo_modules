from odoo import models


class SequenceMixin(models.AbstractModel):

    _name = 'sequence.mixin'
    _inherit = 'sequence.mixin'

    def _constrains_date_sequence(self):
        return False
