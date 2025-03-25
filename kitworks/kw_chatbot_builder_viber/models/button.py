# flake8: noqa: E501
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MessageNotificationLineButton(models.Model):
    _name = 'kw.viber.button.notification.line'
    _description = 'Message Notification Line'

    viber_button_id = fields.Many2one(
        comodel_name='kw.chatbot.step.viber.keyboard')
    model_id = fields.Many2one(
        comodel_name='ir.model', required=True, ondelete='cascade',
        related='viber_button_id.model_id', )
    model_name = fields.Char(related='model_id.model', )
    fields_id = fields.Many2one(
        comodel_name='ir.model.fields', ondelete='cascade',
        domain="[('model_id', '=', model_id)]", )
    sub_model = fields.Char(related='fields_id.relation', )
    sub_fields_id = fields.Many2one(
        comodel_name='ir.model.fields', ondelete='cascade',
        domain="[('model_id', '=', model_id)]", )
    text_before = fields.Char(translate=True)
    text_after = fields.Char(translate=True)
    sequence = fields.Integer()
    need_after_before_text_new_line = fields.Boolean(
        default=False, string='New line after text')
    need_after_after_text_new_line = fields.Boolean(
        default=True, string='New line after text')
    part_message = fields.Char(compute='_compute_part_message', )

    @api.onchange('text_before', 'need_after_before_text_new_line',
                  'text_after', 'need_after_after_text_new_line')
    def _compute_text(self):
        for rec in self:
            rec.text_before = rec.text_before.replace('<br/>', '') \
                if rec.text_before else ''
            if rec.need_after_before_text_new_line:
                rec.text_before = '%s<br/>' % rec.text_before
            else:
                rec.text_before = '%s' % rec.text_before.replace(
                    '<br/>', '')
            rec.text_after = rec.text_after.replace(
                '<br/>', '') if rec.text_after else ''
            if rec.need_after_after_text_new_line:
                rec.text_after = '%s<br/>' % rec.text_after
            else:
                rec.text_after = '%s' % rec.text_after.replace(
                    '<br/>', '')

    def _compute_part_message(self):
        for rec in self:
            text_before = rec.text_before or ''
            text_after = rec.text_after or ''
            if rec.fields_id.ttype in ['many2one', 'one2many', 'many2many'] \
                    and rec.sub_fields_id:
                part_message = '%s ${object.%s.%s} %s' % (
                    text_before,
                    rec.fields_id.name,
                    rec.sub_fields_id.name,
                    text_after)
            else:
                if rec.fields_id:
                    part_message = \
                        '%s ${object.%s} %s' % (text_before,
                                                 rec.fields_id.name,
                                                 text_after)
                else:
                    part_message = '%s %s' % (text_before, text_after)
            rec.part_message = part_message


class MessageNotificationLineButtonUn(models.Model):
    _name = 'kw.viber.button.un.notification.line'
    _description = 'Message Notification Line'

    viber_button_id = fields.Many2one(
        comodel_name='kw.chatbot.step.viber.keyboard')
    model_id = fields.Many2one(
        comodel_name='ir.model', required=True, ondelete='cascade',
        related='viber_button_id.model_id', )
    model_name = fields.Char(
        related='model_id.model', )
    fields_id = fields.Many2one(
        comodel_name='ir.model.fields', ondelete='cascade',
        domain="[('model_id', '=', model_id)]", )
    sub_model = fields.Char(related='fields_id.relation', )
    sub_fields_id = fields.Many2one(
        comodel_name='ir.model.fields', ondelete='cascade',
        domain="[('model_id', '=', model_id)]", )
    text_before = fields.Char(translate=True)
    text_after = fields.Char(translate=True)
    sequence = fields.Integer()
    need_after_before_text_new_line = fields.Boolean(
        default=False, string='New line after text')
    need_after_after_text_new_line = fields.Boolean(
        default=True, string='New line after text')
    part_message = fields.Char(compute='_compute_part_message', )

    @api.onchange('text_before', 'need_after_before_text_new_line',
                  'text_after', 'need_after_after_text_new_line')
    def _compute_text(self):
        for rec in self:
            rec.text_before = rec.text_before.replace(
                '<br/>', '') if rec.text_before else ''
            if rec.need_after_before_text_new_line:
                rec.text_before = '%s<br/>' % rec.text_before
            else:
                rec.text_before = '%s' % rec.text_before.replace(
                    '<br/>', '')
            rec.text_after = rec.text_after.replace(
                '<br/>', '') if rec.text_after else ''
            if rec.need_after_after_text_new_line:
                rec.text_after = '%s<br/>' % rec.text_after
            else:
                rec.text_after = '%s' % rec.text_after.replace(
                    '<br/>', '')

    def _compute_part_message(self):
        for rec in self:
            text_before = rec.text_before or ''
            text_after = rec.text_after or ''
            if rec.fields_id.ttype in ['many2one', 'one2many', 'many2many'] \
                    and rec.sub_fields_id:
                part_message = '%s ${object.%s.%s} %s' % (
                    text_before,
                    rec.fields_id.name,
                    rec.sub_fields_id.name,
                    text_after)
            else:
                if rec.fields_id:
                    part_message = \
                        '%s ${object.%s} %s' % (text_before,
                                                 rec.fields_id.name,
                                                 text_after)
                else:
                    part_message = '%s %s' % (text_before, text_after)
            rec.part_message = part_message


class StepViberKeyboard(models.Model):
    _name = 'kw.chatbot.step.viber.keyboard'
    _inherit = 'kw.chatbot.step.viber.keyboard'

    DEFAULT_PYTHON_CODE = """# Available variables:
    #  - env: Odoo Environment on which the action is triggered
    #  - model: Odoo Model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - float_compare: Odoo function to compare floats based on specific precisions
    #  - log: log(message, level='info'): logging function to record debug information in ir.logging table
    #  - UserError: Warning Exception to use with raise
    #  - Command: x2Many commands namespace
    #  - sender_user: Viber user who sent the message
    #  - sender_partner: Viber user's partner
    # To return an action, assign: action = {...}\n\n\n\n"""

    notification_id = fields.Many2one(
        comodel_name='kw.chatbot.notification', invisible=True, )
    notification_model_name = fields.Char(
        related='notification_id.model_id.model')
    sequence = fields.Integer(
        default=1, )
    callback_data = fields.Char(compute='_compute_callback_data', )
    state = fields.Selection(
        [('code', 'Execute Python Code'),
         ('object_create', 'Create a new Record	'),
         ('object_write', 'Update a Record'),
         ('email', 'Send Email	'),
         ('followers', 'Add Followers'),
         ('next_activity', 'Create Next Activity'),
         ('sms', 'Send SMS Text Message	'),
         ('send_notification', 'Send Notification'),
         ('forward_step', 'Forward Step'),],
        default='object_write', required=True, copy=True,
        help="Type of server action. The following values are available:\n"
             "- 'Execute Python Code': a block of python code that will be executed\n"
             "- 'Create': create a new record with new values\n"
             "- 'Update a Record': update the values of a record\n"
             "- 'Execute several actions': define an action that triggers several other server actions\n"
             "- 'Send Email': automatically send an email (Discuss)\n"
             "- 'Add Followers': add followers to a record (Discuss)\n"
             "- 'Create Next Activity': create an activity (Discuss)")
    successful_text_line_id = fields.One2many(
        comodel_name='kw.viber.button.notification.line',
        inverse_name='viber_button_id', string='Text Line', )
    successful_notification = fields.Text(
        required=True, compute='_compute_ready_message', )
    unsuccessful_text_line_id = fields.One2many(
        comodel_name='kw.viber.button.un.notification.line',
        inverse_name='viber_button_id', string='Text Line', )
    unsuccessful_notification = fields.Text(
        required=True, compute='_compute_unready_message', )
    model_id = fields.Many2one(
        comodel_name='ir.model', string='Model', )
    model_name = fields.Char(
        related='model_id.model', )
    code = fields.Text(
        string='Python Code', groups='base.group_system',
        default=DEFAULT_PYTHON_CODE,
        help="Write Python code that the action will execute. "
             "Some variables are available for use; help about python "
             "expression is given in the help tab.")
    fields_lines = fields.One2many(
        comodel_name='ir.actions.server',
        inverse_name='viber_button_id')
    target_model_id = fields.Many2one(
        comodel_name='ir.model', string='Target Model',
        help="Model for record creation / update. Set this field only "
             "to specify a different model than the base model.")
    target_model_name = fields.Char(
        related='target_model_id.model', string='Target Model Name',
        readonly=True)
    link_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        help="Provide the field used to link the newly created record "
             "on the record used by the server action.")

    partner_ids = fields.Many2many(
        comodel_name='res.partner', string='Add Followers')
    template_id = fields.Many2one(
        comodel_name='mail.template', string='Email Template',
        ondelete='set null', domain="[('model_id', '=', model_id)]",)

    # Next Activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity',
        domain="['|', ('res_model', '=', False), "
               "('res_model', '=', model_name)]",
        ondelete='restrict')
    activity_summary = fields.Char('Summary')
    activity_note = fields.Html('Note')
    activity_date_deadline_range = fields.Integer(string='Due Date In')
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')
    activity_user_type = fields.Selection(selection=[
        ('specific', 'Specific User'),
        ('generic', 'Generic User From Record')], default="specific",
        help="Use 'Specific User' to always assign the same user on the "
             "next activity. Use 'Generic User From Record' to specify the "
             "field name of the user to choose on the record.")
    activity_user_id = fields.Many2one(
        comodel_name='res.users', string='Responsible')
    activity_user_field_name = fields.Char(
        string='User field name',
        help="Technical name of the user on the record",
        default="user_id")
    # SMS
    sms_template_id = fields.Many2one(
        comodel_name='sms.template',
        string='SMS Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]", )
    sms_mass_keep_log = fields.Boolean('Log as Note', default=True)

    # send notification
    notification_for_send = fields.Many2one(
        comodel_name='kw.chatbot.notification', )
    uns_notification_for_send = fields.Many2one(
        comodel_name='kw.chatbot.notification', )
    use_parent_record = fields.Boolean(
        default=False, )
    model_notification_id = fields.Many2one(
        comodel_name='ir.model', string='Child Model',
        compute='_compute_model_notification_id', )
    model_notification_name = fields.Char()
    child_field_id = fields.Many2one(
        comodel_name='ir.model.fields', )
    child_field_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        compute_sudo=True, compute='_compute_child_field')
    search_type = fields.Selection(selection=[
        ('children', 'In Children'),
        ('parent', 'In Parent'), ], default='children')

    forward_step_id = fields.Many2one(
        comodel_name='kw.chatbot.step', )
    send_last = fields.Boolean(deafult=False)

    @api.onchange('search_type')
    def _compute_child_field(self):
        for obj in self:
            field_ids = self.env['ir.model.fields']
            if obj.model_id and obj.model_notification_id:
                if obj.search_type == 'children':
                    field_ids = self.env['ir.model.fields'].search([
                        ('relation', '=', obj.model_id.model),
                        ('model_id', '=', obj.model_notification_id.id)])
                if obj.search_type == 'parent':
                    field_ids = self.env['ir.model.fields'].search([
                        ('model_id', '=', obj.model_id.id),
                        ('relation', '=', obj.model_notification_id.model)])
            obj.child_field_ids = [(6, 0, field_ids.ids)]

    @api.onchange('notification_for_send')
    def _compute_model_notification_id(self):
        for rec in self:
            notif = rec.notification_for_send
            if rec.notification_for_send:
                rec.model_notification_id = notif.model_id
                rec.model_notification_name = notif.model_id.model
            else:
                rec.model_notification_id = False
                rec.model_notification_name = False

    @api.onchange('unsuccessful_text_line_id')
    def _compute_unready_message(self):
        for rec in self:
            rec.unsuccessful_notification = rec._get_message_un_designer()

    @api.onchange('successful_text_line_id')
    def _compute_ready_message(self):
        for rec in self:
            rec.successful_notification = rec._get_message_designer()

    def _get_message_designer(self):
        self.ensure_one()
        message = ''
        for line in self.successful_text_line_id.sorted(
                key=lambda r: r.sequence):
            message += line.part_message if line.part_message else ' '
        return message

    def _get_message_un_designer(self):
        self.ensure_one()
        message = ''
        for line in self.unsuccessful_text_line_id.sorted(
                key=lambda r: r.sequence):
            message += line.part_message if line.part_message else ' '
        return message

    def _compute_callback_data(self):
        for rec in self:
            rec.callback_data = {'id_button': rec.id}


class IrServerObjectLines(models.Model):
    _inherit = 'ir.actions.server'

    viber_button_id = fields.Many2one(
        comodel_name='kw.chatbot.step.viber.keyboard')
