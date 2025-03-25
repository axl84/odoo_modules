import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

INPUTS = ['free_input_single', 'question_name',
          'question_email', 'update_contact_field']


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    instagram_button_ids = fields.One2many(
        comodel_name='kw.chatbot.step.instagram.button',
        inverse_name='step_id', )

    @api.onchange('answer_ids')
    def _compute_answer_instagram(self):
        for obj in self:
            obj.instagram_button_ids = False
            for ans in obj.answer_ids:
                obj.instagram_button_ids = [(0, 0, {'name': ans.name})]

    def instagram_button_start(self):
        self.ensure_one()
        # _logger.info('instagram_return_to_start')
        return {"type": "postback",
                "title": 'Повернутись в Меню',
                "payload": '/start'}

    def odoo_livechat_close_wired_conversation(
            self, conversation, channel, message):
        if conversation.wired_conversation_id:
            consult_conv = conversation.wired_conversation_id
            if consult_conv.chat_id.messenger_id.provider == 'instagram':
                m = [{"type": "postback",
                      "title": _('Restart?'),
                      "payload": '/start'}]
                bot2 = \
                    consult_conv.chat_id.instagram_get_instagram_bot()
                res2 = bot2.send_button_message(
                    consult_conv.sender_id.instagram_id,
                    _('The consultation is over'), m)
                conversation.telegram_create_log(name='OUT', body=res2)
        return super().odoo_livechat_close_wired_conversation(
            conversation, channel, message)

    def instagram_get_response(self, conversation, bot, message):
        self.ensure_one()

        _logger.info(self.step_type)

        if conversation.dialog_id:
            if self.step_type in INPUTS:
                conversation.send_message(text=self.text)
                conversation.input_step_id = self.id
                conversation.last_step_id = self.id
                return True
        if self.step_type == 'create_lead':
            self.create_lead(conversation)
        markup = []
        if self.instagram_button_ids:
            for k in self.instagram_button_ids:
                markup.append(k.get_instagram_button_markup())
        if self.step_type == 'forward_operator':
            if not self.is_not_send_send_text:
                conversation.send_message(text=self.text, markup=markup)
            self.operator_forward(conversation, message)
            return True
        conversation.send_message(text=self.text, markup=markup)
        if conversation.dialog_id:
            if self.step_type == 'text':
                return False
        return True

    def instagram_get_communicate(self, conversation, bot, message):
        self.ensure_one()
        # _logger.info('instagram_get_communicate')
        res_partner_ids = self.env['res.partner'].search([
            ('kw_is_consultant', '=', True),
            ('im_status', '=', 'online'),
            ('kw_is_available_consultant', '=', True)])
        if not res_partner_ids:
            conversation.send_message(
                text=_('There are currently no active consultants'))
            return True
        markup = []
        for partner in res_partner_ids:
            btn = {"type": "postback",
                   "title": partner.name,
                   "payload": f'/begin_consultation {partner.id}'}
            markup.append(btn)
        markup.append(self.instagram_button_start())
        conversation.send_message(text=_('Choose a consultant'),
                                  markup=markup)
        return True

    def instagram_start_consultation(
            self, conversation, bot, message):
        # _logger.info('instagram_start_consultation')
        self.ensure_one()
        text = conversation.instagram_get_message_data(message)
        consultant_conversation, consultant = \
            self.get_consultant_conversation_from_text(text)
        if consultant_conversation:
            m = [self.get_odoo_livechat_button(
                name=_('Close the consultation'),
                callback_data='/close_wired_conversation')]
            consultant_conversation.send_message(
                text=_('Open consultation with the user'
                       ' (for others you offline)'), markup=m)
            conversation.sudo(
            ).wired_conversation_id = consultant_conversation.id
            consultant_conversation.sudo(
            ).wired_conversation_id = conversation.id
            self.get_offline_sender_mode(consultant_conversation)
        conversation.send_message(
            text=_(f'Consultant {consultant.name} joined,'
                   f' and will answer your question soon.'),
            markup=[{"type": "postback",
                     "title": _('Close the consultation'),
                     "payload": '/close_wired_conversation'}])
        return True

    def instagram_close_wired_conversation(
            self, conversation, bot, message):
        # _logger.info('instagram_close_wired_conversation')
        self.ensure_one()
        if conversation.wired_conversation_id:
            consult_conv = conversation.wired_conversation_id
            m = [self.get_odoo_livechat_button(
                _('Restart?'), '/start')]
            consult_conv.send_message(text=_('The consultation is over'),
                                      markup=m)
            self.close_wired_conversation(conversation)
            conversation.send_message(
                text=_('The consultation is over'),
                markup=[{"type": "postback",
                         "title": _('Restart?'),
                         "payload": '/start'}])
        return True


class StepInstagramButton(models.Model):
    _name = 'kw.chatbot.step.instagram.button'
    _description = 'Step instagram button'

    name = fields.Char(
        required=True, string='Code', )
    active = fields.Boolean(
        default=True, )
    step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    callback_data = fields.Char()

    url = fields.Char()

    def get_instagram_button_markup(self):
        self.ensure_one()
        return {
            "type": "postback",
            "title": self.name,
            "payload": self.callback_data}
