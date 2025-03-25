import re
from odoo import models, fields, _

from telebot import types


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'

    sms_template_id = fields.Many2one(
        comodel_name='sms.template',
        string='Template message',
    )

    def send_to_telegram(self):
        self.ensure_one()
        text = 'Your payment link'
        if self.sms_template_id:
            text = self.sms_template_id._render_template(
                template_src=self.sms_template_id.body,
                model='sale.order',
                res_ids=[self.res_id], )
            clean = re.compile('<.*?>')
            text1 = \
                re.sub(r'<br.*?>', '\n', text[
                    self.res_id])
            text2 = re.sub(clean, '', text1)
            text = text2
        # get sale order
        sale_order = self.env['sale.order'].browse(self.res_id)
        # get telegram user from partner_id
        telegram_user = sale_order.partner_id.sender_ids[0]
        # send message with url and buttons
        # add button for payment link
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        btn_payment = types.InlineKeyboardButton(
            text=_('Url payment link'), url=self.link)
        markup.add(btn_payment)
        markup.add(*buttons)
        telegram_user.conversation_ids[0].send_message(
            text=text,
            reply_markup=markup,
            buttons=buttons,
        )
