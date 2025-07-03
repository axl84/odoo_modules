"""
Operator activity.
This model stores information about the activity
of operators when working with clients.
"""

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class OperatorActivity(models.Model):
    _name = 'kw.chatbot.operator.activity'
    _description = 'Operator Activity'

    operator_id = fields.Many2one(
        comodel_name='res.partner', )

    chat_id = fields.Many2one(
        comodel_name='kw.chatbot.chat', )

    dialog_id = fields.Many2one(
        comodel_name='kw.chatbot.dialog', )

    conversation_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation', )

    sender_id = fields.Many2one(
        comodel_name='kw.chatbot.sender', )

    date_start = fields.Datetime()

    first_answer_date = fields.Datetime()

    date_end = fields.Datetime()

    duration_chat = fields.Float(
        string='Chat Duration',
        compute='_compute_chat_duration',
        store=True,
        digits=(16, 0), )

    category_id = fields.Many2one(
        comodel_name='kw.chatbot.conversation.category', )

    who_answered_id = fields.Selection([
        ('client', 'Client'),
        ('operator', 'Operator'),
    ], string='Who answered last', )

    is_answer = fields.Boolean(string='Elaborated dialogue', )

    evaluation = fields.Integer(string='Service evaluation',
                                group_operator="avg")

    # fields for pivot

    open_dialogues = fields.Integer(compute='_compute_open_dialogues',
                                    store=True)

    in_standby_mode = fields.Integer(compute='_compute_in_standby_mode',
                                     store=True)

    completed = fields.Integer(compute='_compute_completed',
                               store=True)

    missed = fields.Integer(compute='_compute_missed',
                            store=True)

    average_first_response_time = fields.Float(
        compute='_compute_average_first_response_time',
        digits=(16, 0),
        store=True,
        group_operator="avg")

    average_closing_time = fields.Float(
        compute='_compute_average_closing_time',
        digits=(16, 0),
        store=True,
        group_operator="avg")

    total_dialogs = fields.Integer(default=1, store=True)

    @api.depends('display_name')
    def _compute_display_name(self):
        """
        Set name for element
        """
        for record in self:

            operator_name = record.operator_id.name if record.operator_id \
                else False

            name = _("Operator Activity")

            if operator_name:
                name += f" - {operator_name}"

            record.display_name = name
        return True

    @api.depends('is_answer')
    def _compute_open_dialogues(self):
        for record in self:
            open_dialogues_count = len(record.filtered(lambda x: x.is_answer))
            record.open_dialogues = open_dialogues_count

    # flake8: noqa: E501
    @api.depends('is_answer', 'conversation_id')
    def _compute_in_standby_mode(self):
        for record in self:
            standby_mode_count = 0
            for activity in record:
                if hasattr(activity.conversation_id,
                           'wired_conversation_id') and not activity.is_answer and activity.conversation_id.wired_conversation_id:
                    standby_mode_count += 1
            record.in_standby_mode = standby_mode_count

    @api.depends('is_answer', 'conversation_id.is_closed')
    def _compute_completed(self):
        for record in self:
            completed_count = len(record.filtered(
                lambda x: x.is_answer and x.conversation_id.is_closed))
            record.completed = completed_count

    # flake8: noqa: E501
    @api.depends('is_answer', 'conversation_id')
    def _compute_missed(self):
        for record in self:
            missed_count = 0
            for activity in record:
                if hasattr(activity.conversation_id,
                           'wired_conversation_id') and not activity.is_answer and not activity.conversation_id.wired_conversation_id:
                    missed_count += 1
            record.missed = missed_count

    # flake8: noqa: E501
    @api.depends('is_answer', 'first_answer_date', 'date_start')
    def _compute_average_first_response_time(self):
        for record in self:
            dialogs_with_answer = record.filtered(lambda x: x.is_answer)
            dialogs_with_valid_times = dialogs_with_answer.filtered(lambda x: x.first_answer_date and x.date_start)
            if dialogs_with_valid_times:
                total_response_time_seconds = sum((dialog.first_answer_date - dialog.date_start).total_seconds() for dialog in dialogs_with_valid_times)
                record.average_first_response_time = total_response_time_seconds / 60 / len(dialogs_with_valid_times)
            else:
                record.average_first_response_time = 0.0

    # flake8: noqa: E501
    @api.depends('is_answer', 'conversation_id.is_closed', 'duration_chat')
    def _compute_average_closing_time(self):
        for record in self:
            dialogs_with_answer_closed = record.filtered(lambda x: x.is_answer and x.conversation_id.is_closed and x.duration_chat)
            if dialogs_with_answer_closed:
                total_closing_time_minutes = sum(dialog.duration_chat for dialog in dialogs_with_answer_closed)
                record.average_closing_time = total_closing_time_minutes / len(dialogs_with_answer_closed)
            else:
                record.average_closing_time = 0.0

    @api.depends('date_start', 'date_end')
    def _compute_chat_duration(self):
        for activity in self:
            if activity.date_start and activity.date_end:
                start_datetime = fields.Datetime.from_string(
                    activity.date_start)
                end_datetime = fields.Datetime.from_string(activity.date_end)
                duration = (end_datetime - start_datetime).total_seconds() / 60

                # If the dialog ends very quickly
                if duration < 1:
                    activity.duration_chat = 1.0
                else:
                    activity.duration_chat = duration

            else:
                activity.duration_chat = 0.0
