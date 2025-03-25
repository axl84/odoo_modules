import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    wepster_crm_user_id = fields.Many2one(
        comodel_name='res.users', string='Salesperson')
    wepster_crm_team_id = fields.Many2one(
        comodel_name='crm.team', string='Sales Team')
    wepster_crm_type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')],
        default='opportunity', string='Type')

    # pylint: disable=R1710
    def wepster_create_chat(self):
        messenger_id = self.env['kw.chatbot.messenger'].sudo().search(
            [('name', '=', 'Wepster')], limit=1)
        chat_id = self.search([
            ('name', '=', 'Wepster'),
            ('messenger_id', '=', messenger_id.id)], limit=1)
        if not chat_id:
            dialog_id = self.env['kw.chatbot.dialog'].sudo().search([
                ('bots_type', '=', 'is_consultant_bot')], limit=1)
            chat_id = self.create({
                'name': 'Wepster',
                'dialog_id': dialog_id.id,
                'messenger_id': messenger_id.id})
        return chat_id

    def wepster_process_message(self, message, log):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id, sender=message)
        message = message.get('eventData')
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        log.sudo().write({
            'sender_id': sender.id, 'conversation_id': conversation.id, })
        wepster_message = message.get('message')
        if wepster_message:
            text = wepster_message.get('text')
            m_data = {
                'wepster_id': sender.id,
                'conversation_id': conversation.id,
                'sender_id': sender.id, 'text': text,
                'name': text, }
            conversation.last_activity_datetime = fields.Datetime.now()
            # attach_id = conversation.upload_webster_url_file(text)
            # if attach_id:
            #     m_data.update({'attachment_ids': [(4, attach_id.id)]})
            # else:
            #     conversation.wepster_get_response(message)
            conversation.wepster_get_response(message)
            conversation.chatbot_message_id = \
                self.env['kw.chatbot.message'].sudo().create(m_data)

    def wepster_process_call(self, jsonrequest, log):
        self.ensure_one()
        # _logger.info('facebook_process_call')
        if jsonrequest.get('eventData'):
            self.wepster_process_message(
                message=jsonrequest, log=log)
