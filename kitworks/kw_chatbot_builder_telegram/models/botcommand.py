from odoo import models, fields, api


class TelegramCommand(models.Model):
    _name = 'kw.chatbot.telegram.command'

    name = fields.Char(
        string='Description', required=True, )
    command = fields.Char(
        required=True, )
    chat_id = fields.Many2one(
        comodel_name='kw.chatbot.chat')
    dialog_id = fields.Many2one(
        related='chat_id.dialog_id', )
    step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    dialog_answer_id = fields.Many2one(
        comodel_name='chatbot.dialog.answer', )

    def add_step_alias(self):
        self.ensure_one()
        alias_id = self.env['kw.chatbot.step.alias'].sudo().search([
            ('name', '=', f"/{self.command}"),
            ('step_id', '=', self.step_id.id), ])
        if not alias_id:
            alias_id = self.env['kw.chatbot.step.alias'].sudo().create({
                'name': f"/{self.command}",
                'step_id': self.step_id.id, })
        alias_id.dialog_answer_id = self.dialog_answer_id.id \
            if self.dialog_answer_id else False
        return alias_id

    @api.model
    def create(self, vals_list):
        result = super().create(vals_list)
        for obj in result:
            if obj.step_id:
                obj.add_step_alias()
        return result

    def write(self, vals_list):
        result = super().write(vals_list)
        for obj in self:
            if obj.step_id:
                obj.add_step_alias()
        return result

    def unlink(self):
        for obj in self:
            if obj.step_id:
                alias_ids = self.env['kw.chatbot.step.alias'].sudo().search([
                    ('name', '=', f"/{obj.command}"),
                    ('step_id', '=', obj.step_id.id), ])
                for alias_id in alias_ids:
                    alias_id.unlink()
        return super(TelegramCommand, self).unlink()
