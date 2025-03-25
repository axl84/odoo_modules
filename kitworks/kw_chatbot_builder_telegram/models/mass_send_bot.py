import ast
import logging
from odoo import models, fields
from telebot import types

_logger = logging.getLogger(__name__)


class Mailing(models.Model):
    _inherit = 'kw.chatbot.mass.send.bot'

    telegram_button_ids = fields.Many2many(
        comodel_name='kw.chatbot.step.telegram.button',
    )
    file_id = fields.Binary(
        string='File',
        help='File to send',
    )
    file_name = fields.Char()
    sms_template_id = fields.Many2one(
        comodel_name='sms.template', )

    def action_send(self):
        for obj in self:
            if obj.kw_filter_domain:
                res_partner_ids = \
                    self.env['res.partner'].search(ast.literal_eval(
                        (obj.kw_filter_domain))).ids
            else:
                res_partner_ids = self.env['res.partner'].search([]).ids
            for con in obj.dialog_id.conversations_ids:
                text = obj.sms_template_id.body if obj.sms_template_id \
                    else obj.text
                if con.partner_id.id in res_partner_ids:
                    # add button
                    markup, buttons = None, []
                    markup = types.InlineKeyboardMarkup()
                    for button in obj.telegram_button_ids:
                        callback_data = \
                            ast.literal_eval(button.callback_data.replace(
                                "'", '"'))
                        btn = types.InlineKeyboardButton(
                            text=button.name,
                            callback_data=str(callback_data), )
                        markup.add(btn)
                    markup.add(*buttons)
                    if obj.file_id:
                        # create attachment
                        attachment = self.env['ir.attachment'].create({
                            'name': obj.file_name.replace(' ', '_'),
                            'datas': obj.file_id,
                            'res_model': 'kw.chatbot.conversation',
                            'res_id': con.id,
                            'type': 'binary',
                        })
                        con.send_file(attachment,
                                      **{'not_create_log': True,
                                         'reply_markup': markup,
                                         'buttons': buttons,
                                         'text': text})
                    else:
                        con.send_message(text,
                                         reply_markup=markup,
                                         buttons=buttons)
                    # except Exception as e:
                    #     _logger.debug(e)
                else:
                    _logger.debug('Partner not in filter domain')
