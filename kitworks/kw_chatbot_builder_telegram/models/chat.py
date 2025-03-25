import logging

from telebot import types

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    tg_command_ids = fields.One2many(
        comodel_name='kw.chatbot.telegram.command',
        inverse_name='chat_id')

    def telegram_update_command(self):
        commands = []
        for command_id in self.tg_command_ids:
            command = types.BotCommand(command_id.command, command_id.name)
            commands.append(command)
        if commands:
            bot = self.telegram_get_telegram_bot()
            bot.set_my_commands(commands)

    def telegram_update_hook_address(self):
        self.telegram_update_command()
        return super().telegram_update_hook_address()

    def search_dialog(self):
        if self.provider == 'telegram':
            dialog_ids = self.dialog_ids
            dialog_ids = dialog_ids.search([
                ('company_id', '=', self.env.company.id)])
            if dialog_ids:
                return dialog_ids.ids
            return dialog_ids
        return super().search_dialog()
