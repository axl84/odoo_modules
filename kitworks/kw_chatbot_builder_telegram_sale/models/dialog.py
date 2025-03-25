import logging
from odoo import models, fields
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    buttons_category_ids = fields.Many2many(
        'kw.chatbot.step.telegram.button',
        compute='_compute_buttons_category_ids', )

    def _compute_buttons_category_ids(self):
        # for each category, create a button with type = 'sale'
        # and type_sale = 'choose_category'
        # and name = category.name
        # step 1 - get all categories
        if not self.model_category_id:
            return
        model = self.env[self.model_category_id.model]
        domain = []
        if self.filter_category_domain:
            domain = safe_eval(self.filter_category_domain)
        categories = model.search(domain)
        # step 2 - create buttons
        buttons = self.env['kw.chatbot.step.telegram.button']
        for category in categories:
            button = self.env['kw.chatbot.step.telegram.button'].search([
                ('state', '=', 'sale'),
                ('type_sale', '=', 'choose_category'),
                ('name', '=', category.name),
                ('category_id', '=', category.id),
            ])
            if button:
                buttons |= button
                continue
            button = self.env['kw.chatbot.step.telegram.button'].create({
                'state': 'sale',
                'type_sale': 'choose_category',
                'name': category.name,
                'category_id': category.id,
            })
            buttons |= button
        self.buttons_category_ids = buttons

    def telegram_get_response(self, conversation, bot, message):
        if self.select_flow == 'sale':
            return conversation.sale_start(bot, message)
        return super().telegram_get_response(conversation, bot, message)
