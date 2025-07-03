from odoo import models, fields, api


class StatisticsWizardSetCategory(models.TransientModel):
    _name = 'statistics.wizard.set.category'
    _description = 'Statistics Wizard: Set Category'

    operator_id = fields.Many2one(
        comodel_name='res.partner',
        readonly=True,
    )

    chat_id = fields.Many2one(
        comodel_name='kw.chatbot.chat',
        readonly=True,
    )

    dialog_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog',
        readonly=True,
    )

    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation',
        readonly=True,
    )

    sender_id = fields.Many2one(
        comodel_name='kw.chatbot.sender',
        readonly=True,
    )

    date_start = fields.Datetime(
        readonly=True,
    )

    date_end = fields.Datetime(
        readonly=True,
    )

    category_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation.category',
    )

    is_not_elements = fields.Boolean(default=False)

    @api.model
    def default_get(self, values):
        """
        Get values for current wizard
        """
        res = super(StatisticsWizardSetCategory, self).default_get(values)

        current_user = self.env.user

        latest_record = self.env['kw.chatbot.operator.activity'].search([
            ('category_id', '=', False),
            ('operator_id', '=', current_user.partner_id.id)
        ], limit=1, order='date_start desc')

        if latest_record:
            res.update({
                'operator_id': latest_record.operator_id.id,
                'chat_id': latest_record.chat_id.id,
                'dialog_id': latest_record.dialog_id.id,
                'conversation_id': latest_record.conversation_id.id,
                'sender_id': latest_record.sender_id.id,
                'date_start': latest_record.date_start,
                'date_end': latest_record.date_end,
            })
        else:
            res.update({
                'is_not_elements': True
            })

        return res

    def action_set_category(self):
        """
        Set selected category for current operator activity record
        """
        self.ensure_one()
        if self.category_id:
            # Update the selected activity record with the chosen category
            activity_record = self.env['kw.chatbot.operator.activity'].search([
                ('operator_id', '=', self.operator_id.id),
                ('chat_id', '=', self.chat_id.id),
                ('dialog_id', '=', self.dialog_id.id),
                ('conversation_id', '=', self.conversation_id.id),
                ('sender_id', '=', self.sender_id.id),
                ('date_start', '=', self.date_start),
                ('date_end', '=', self.date_end),
            ], limit=1)

            if activity_record:
                activity_record.category_id = self.category_id
        return {'type': 'ir.actions.act_window_close'}
