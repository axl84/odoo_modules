import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Mailing(models.Model):
    _name = 'kw.chatbot.message.mailing'
    _description = 'Message Mailing'

    type = fields.Selection(
        default='all', selection=[
            ('all', _('To all')), ('chosen', _('To chosen')), ], )
    text = fields.Text()

    sender_ids = fields.Many2many(
        comodel_name='kw.chatbot.sender', )
    is_sent = fields.Boolean(
        default=False, readonly=True, )
    mailing_log = fields.Text(string='Mailing Logs', readonly=True, )

    messenger_id = fields.Many2one(
        comodel_name='kw.chatbot.messenger', )

    @api.model
    def get_or_create(self, messenger, **kwargs):
        _logger.debug(messenger, kwargs)

    def action_send(self):
        for obj in self:
            if self.type == 'all':
                obj.send_to_all()
            else:
                obj.send_to_chosen()

    def send_to(self, senders):
        for obj in self:
            names = []
            obj.mailing_log = ''
            obj.is_sent = False
            for sender in senders:
                if sender.conversation_ids:
                    s = 0
                    for con in sender.conversation_ids:
                        if con.chat_id.messenger_id == obj.messenger_id:
                            obj.send_conv(sender, s)
                            names.append(str(obj.mailing_log))
                        else:
                            names.append(str(sender.name) + ', ')
            if names:
                obj.mailing_log = "Message doesn't send to: {}".format(names)

    def send_conv(self, sender, s):
        for obj in self:
            try:
                sender.conversation_ids[s].send_message(
                    obj.text)
                obj.is_sent = True
            except Exception:
                sender.conversation_ids[s].unlink()
                sender.unlink()
                obj.mailing_log = sender.name
            s += 1

    def send_to_all(self):
        self.send_to(self.env['kw.chatbot.sender'].search([]))

    def send_to_chosen(self):
        self.send_to(self.sender_ids)
