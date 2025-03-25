import logging
import re

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    @staticmethod
    def check_single_emoji(message):
        has_text = bool(re.search(r'\w', message))
        emojis = re.findall(r'[^\w\s,.!?)(\`*"]', message)
        if not has_text and len(emojis) == 1:
            return True
        return False

    link_bot = fields.Char()

    helpcrunch_crm_user_id = fields.Many2one(
        comodel_name='res.users', string='Salesperson')
    helpcrunch_crm_team_id = fields.Many2one(
        comodel_name='crm.team', string='Sales Team')
    helpcrunch_crm_type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')],
        default='opportunity', string='Type')

    # @api.depends('messenger_id', 'dialog_id')
    # def _compute_messengers(self):
    #     for obj in self:
    #         if obj.dialog_id \
    #                 and obj.dialog_id.bots_type == 'is_communication_bot':
    #             dialog_ids = obj.search_dialog()
    #             messenger_ids = \
    #                 self.env['kw.chatbot.messenger'].sudo().search(
    #                     [('state', 'in', ['enabled', 'test']),
    #                      ('provider', '!=', 'help_crunch'), ]).mapped('id')
    #             obj.sudo().write({
    #                 'dialog_ids': [(6, 0, dialog_ids)],
    #                 'messenger_ids': [(6, 0, messenger_ids)], })
    #         else:
    #             return super()._compute_messengers()

    # pylint: disable=R1710
    def helpcrunch_create_chat(self):
        messenger_id = self.env['kw.chatbot.messenger'].sudo().search(
            [('name', '=', 'HelpCrunch')], limit=1)
        chat_id = self.search([
            ('name', '=', 'HelpCrunch'),
            ('messenger_id', '=', messenger_id.id)], limit=1)
        if not chat_id:
            dialog_id = self.env['kw.chatbot.dialog'].sudo().search([
                ('bots_type', '=', 'is_consultant_bot')], limit=1)
            chat_id = self.create({
                'name': 'HelpCrunch',
                'dialog_id': dialog_id.id,
                'messenger_id': messenger_id.id})
        return chat_id

    def helpcrunch_process_message(self, message, log):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id, sender=message)
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        log.sudo().write({
            'sender_id': sender.id, 'conversation_id': conversation.id, })
        help_cranch_message = message.get('message')
        if help_cranch_message:
            text = help_cranch_message.get('text')
            m_data = {
                'helpcrunch_id': sender.id,
                'conversation_id': conversation.id,
                'sender_id': sender.id, 'text': text,
                'name': text, }
            conversation.last_activity_datetime = fields.Datetime.now()
            attach_id = conversation.upload_url_image(text)
            if attach_id:
                m_data.update({'attachment_ids': [(4, attach_id.id)]})
            else:
                conversation.helpcrunch_get_response(message)
            conversation.chatbot_message_id = \
                self.env['kw.chatbot.message'].sudo().create(m_data)

    def helpcrunch_process_call(self, jsonrequest, log):
        self.ensure_one()
        # _logger.info('facebook_process_call')
        if jsonrequest.get('eventData'):
            help_crunch_message = jsonrequest.get('eventData').get('message')
            if help_crunch_message:
                text = help_crunch_message.get('text')
                if not self.check_single_emoji(text):
                    self.helpcrunch_process_message(
                        message=jsonrequest.get('eventData'), log=log)
