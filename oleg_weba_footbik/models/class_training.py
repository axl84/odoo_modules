from pytz import timezone

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class ClassTraining(models.Model):
    _name = "class.training"
    _description = "Class Training"
    _inherit = "mail.thread"

    def _compute_display_name(self):
        for rec in self:
            # К началу тренировки (по UTC) + время текущего часового пояса пользователя
            difference_time = self._get_timezone_difference_time()
            start_training = rec.start_training + timedelta(hours=difference_time)
            rec.display_name = f"{rec.class_group_id.name}, {rec.name}, {start_training}"

    class_group_id = fields.Many2one(
        comodel_name="class.group", string="Class Group", ondelete="cascade")
    name = fields.Char(string="Name")

    state = fields.Selection(
        selection=[
            ("planed", _("Planed")),
            ("completed", _("Completed")),
        ],
        string="State",
        default="planed",
        index=True
    )
    color = fields.Char(string="Color")
    city = fields.Char(string="City")
    company_id = fields.Many2one(comodel_name="res.company", string="Club")
    location_id = fields.Many2one(comodel_name="class.location", string="Location")
    trainer_id = fields.Many2one(
        comodel_name="hr.employee", string="Trainer", index=True)
    class_program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)

    date_training = fields.Date(string="Date training")
    time_training = fields.Float(string="Time training")
    start_training = fields.Datetime(
        string="Start training", compute="_compute_start_training", store=True)

    @api.depends("date_training", "time_training")
    def _compute_start_training(self):
        for rec in self:
            start_training = False
            if rec.date_training and rec.time_training:
                hours = int(rec.time_training)
                minutes = int((rec.time_training - hours) * 60)

                difference_time = self._get_timezone_difference_time()

                # Комбинируем дату и время, прибавляя к 00:00 дату начала тренировки +
                # отнимая разницу часового пояса для того что бы фронтенд подставил свою
                # иначе будет на 2 или 3 часа больше
                start_training = datetime.combine(
                    rec.date_training, datetime.min.time()
                ) + timedelta(hours=hours - difference_time, minutes=minutes)

            rec.start_training = start_training

    def _get_timezone_difference_time(self):
        # Получаем часовой пояс пользователя (по умолчанию UTC)
        tz = timezone(self.env.user.tz or "UTC")
        # Получаем разницу времени (+2 или +3 часа)
        return int(
            datetime.now(tz).utcoffset().total_seconds() / 3600)

    duration_training = fields.Float(string="Duration training")
    end_training = fields.Datetime(
        string="End training", compute="_compute_end_training", store=True)

    @api.depends("start_training", "duration_training")
    def _compute_end_training(self):
        for rec in self:
            end_training = False
            if rec.start_training and rec.duration_training:
                hours = int(rec.duration_training)
                minutes = int((rec.duration_training - hours) * 60)

                end_training = rec.start_training + timedelta(
                    hours=hours, minutes=minutes)

            rec.end_training = end_training

    children_ids = fields.One2many(
        comodel_name="class.attendance", inverse_name="class_training_id",
        string="Children")

    def completed_training(self):
        self.state = "completed"
        attendances = self.env["class.attendance"].search([
            ("class_training_id", "=", self.id)])
        attendances.write({"state": "completed"})

        # For testing
        # if self.state == "completed":
        #     self.state = "planed"
        #     attendances = self.env["class.attendance"].search([
        #         ("class_training_id", "=", self.id)])
        #     attendances.write({"state": "planed"})
        #
        # else:
        #     self.state = "completed"
        #     attendances = self.env["class.attendance"].search([
        #         ("class_training_id", "=", self.id)])
        #     attendances.write({"state": "completed"})

    # Метод добавления ученика на пробное занятие (проверка на возможность
    # группы принимать учеников на пробные занятия происходит до вызова метода,
    # вместимость группы не учитывается)
    def add_child_trial_training(self, child_id):  # child_id - res.partner id
        attendance_id = self.env["class.attendance"].sudo().create({
            "class_training_id": self.id,
            "child_id": child_id,
            "start_training": self.start_training,
            "end_training": self.end_training,
            "company_id": self.company_id.id,
            "color": self.color,
            "duration_training": self.duration_training,

            "trial_training": True,
        }).id
        self.children_ids = [(4, attendance_id)]
