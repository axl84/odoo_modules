# pylint: skip-file
import datetime
import logging
import re
import traceback
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)

DATE_RANGE_FUNCTION = {
    'minutes': lambda interval: relativedelta(minutes=interval),
    'hour': lambda interval: relativedelta(hours=interval),
    'day': lambda interval: relativedelta(days=interval),
    'month': lambda interval: relativedelta(months=interval),
    False: lambda interval: relativedelta(0),
}

DATE_RANGE_FACTOR = {
    'minutes': 1,
    'hour': 60,
    'day': 24 * 60,
    'month': 30 * 24 * 60,
    False: 0,
}


class Notification(models.Model):
    _name = 'kw.chatbot.notification'
    _description = 'Chatbot Notification'

    name = fields.Char()  # todo: translate=True
    bot_id = fields.Many2one(comodel_name='kw.chatbot.dialog')
    personal_conversation_ids = fields.Many2many(
        comodel_name='kw.chatbot.conversation', )
    conversation_ids = fields.Many2many(
        comodel_name='kw.chatbot.conversation',
        string='All Conversation', compute='_compute_conversation', )
    model_id = fields.Many2one(comodel_name='ir.model')
    model_name = fields.Char(
        compute="_compute_model_name",
        inverse="_inverse_model_name",
        store=True,
    )
    mail_message_model_id = fields.Many2one(
        comodel_name='ir.model')
    trigger_field_ids = fields.Many2many(
        comodel_name='ir.model.fields', string='Trigger Fields')
    trigger = fields.Selection(selection=[
        ('on_create', _('On Creation')), ('on_write', _('On Update')),
        ('on_create_or_write', _('On Creation & Update')),
        ('on_unlink', _('On Deletion')),
        ('on_time', 'Based on Timed Condition'),
        ('on_external_event', _('On External Event'))],
        default='on_external_event')

    trg_date_id = fields.Many2one(
        comodel_name='ir.model.fields', string='Trigger Date',
        domain="[('model_id', '=', model_id), "
               "('ttype', 'in', ('date', 'datetime'))]")
    trg_date_range = fields.Integer(
        string='Delay after trigger date')
    trg_date_range_type = fields.Selection(selection=[
        ('minutes', 'Minutes'),
        ('hour', 'Hours'), ('day', 'Days'),
        ('month', 'Months')],
        string='Delay type', default='hour')
    last_run = fields.Datetime(readonly=True, copy=False)
    trg_date_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string='Use Calendar', )

    include_link = fields.Boolean()
    message = fields.Text()
    filter_pre_domain = fields.Char(string='Domain before update')
    filter_domain = fields.Char(string='Domain after update')
    is_active = fields.Boolean(default=False)
    is_add_url = fields.Boolean(default=False)
    is_personal_conversation = fields.Boolean(default=False)
    CRITICAL_FIELDS = ['model_id', 'is_active', 'trigger', ]

    model_object_field = fields.Many2one(
        comodel_name='ir.model.fields', string="Field", store=True, )
    sub_object = fields.Many2one(
        comodel_name='ir.model', string='Sub-model',
        readonly=True, store=True, )
    sub_model_object_field = fields.Many2one(
        comodel_name='ir.model.fields',
        string='Sub-field', store=True, )
    null_value = fields.Char(
        string='Default Value', store=True, )
    use_image_product = fields.Boolean(
        string='Use Image Product', default=False, )
    copyvalue = fields.Char(
        string='Placeholder Expression', store=True, )
    is_chosen_partner = fields.Boolean(
        default=False, )
    trigger_partner_field_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        compute="_compute_trigger_partner_field",
        string='Partner', )
    trigger_partner_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        string='Partner', )
    children_trigger_partner_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        string='Children Partner', )
    text_line_id = fields.One2many(
        comodel_name='kw.message.notification.line',
        inverse_name='notification_id', string='Text Line', )
    type_message = fields.Selection(selection=[
        ('message_raw', _('Raw Message')),
        ('message_designer', _('Construct Message')),
    ], default='message_raw', )
    message_designer = fields.Char(compute='_compute_ready_message', )
    line_message_need_serial_number = fields.Boolean(
        default=False, )
    children_trigger_partner_field_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        compute="_compute_children_trigger_partner_field_ids", )
    RANGE_FIELDS = ['trg_date_range', 'trg_date_range_type']
    is_developer_mode = fields.Boolean()
    developer_url = fields.Char()

    is_file_send = fields.Boolean(
        string='Send File', default=False)
    file_fields_ids = fields.Many2many(
        relation='kw_chatbot_messanger_file_fields_ids_rel',
        comodel_name='ir.model.fields', string='File Fields')
    notification_filtered_fields_ids = fields.One2many(
        comodel_name='kw.chatbot.notification.filtered.fields',
        inverse_name='notification_id')

    def copy_data(self, default=None):
        # copy text_line_id
        if default is None:
            default = {}
        default['text_line_id'] = [
            (0, 0, x.copy_data()[0]) for x in self.text_line_id]
        return super(Notification, self).copy_data(default)

    @api.onchange('text_line_id')
    def _compute_ready_message(self):
        for rec in self:
            if rec.type_message == 'message_raw':
                rec.message_designer = rec.message
            else:
                rec.message_designer = rec._get_message_designer()

    def _get_message_designer(self):
        self.ensure_one()
        message = ''
        for line in self.text_line_id.sorted(key=lambda r: r.sequence):
            message += line.part_message if line.part_message else ' '
        return message

    @api.onchange('trigger')
    def onchange_trigger(self):
        if self.trigger == 'on_time':
            self.trg_date_range_type = 'hour'
        else:
            self.trg_date_id = False

    @api.depends("mail_message_model_id")
    def _compute_children_trigger_partner_field_ids(self):
        for obj in self:
            rel_model = ['res.partner', 'res.users', 'hr.employee']
            ids = self.env['ir.model.fields'].sudo().search([
                ('model_id', '=', self.mail_message_model_id.id)]).filtered(
                lambda r: r.relation in rel_model).ids
            self.write({'children_trigger_partner_field_ids': [(6, 0, ids)]})
            obj.model_name = obj.model_id.model

    @api.depends("model_id")
    def _compute_trigger_partner_field(self):
        for obj in self:
            rel_model = ['res.partner', 'res.users', 'hr.employee']
            ids = self.env['ir.model.fields'].sudo().search([
                ('model_id', '=', self.model_id.id)]).filtered(
                lambda r: r.relation in rel_model).ids
            self.write({'trigger_partner_field_ids': [(6, 0, ids)]})
            obj.model_name = obj.model_id.model

    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def _onchange_dynamic_placeholder(self):
        """ Generate the dynamic placeholder """
        if self.model_object_field:
            if self.model_object_field.ttype in \
                    ['many2one', 'one2many', 'many2many']:
                model = self.env['ir.model']._get(
                    self.model_object_field.relation)
                if model:
                    self.sub_object = model.id
                    sub_field_name = self.sub_model_object_field.name
                    self.copyvalue = self._build_expression(
                        self.model_object_field.name,
                        sub_field_name, self.null_value or False)
            else:
                self.sub_object = False
                self.sub_model_object_field = False
                self.copyvalue = self._build_expression(
                    self.model_object_field.name, False,
                    self.null_value or False)
        else:
            self.sub_object = False
            self.copyvalue = False
            self.sub_model_object_field = False
            self.null_value = False

    def update_dynamic_field(self):
        self.write({
            'model_object_field': False,
            'sub_object': False,
            'sub_model_object_field': False,
            'null_value': False,
            'copyvalue': False, })

    def add_in_message(self):
        if self.copyvalue:
            self.write({'message': "{}\n{}".format(
                self.message, self.copyvalue)})
            self.update_dynamic_field()

    @api.onchange('mail_message_model_id')
    def _onchange_mail_message_model_id(self):
        for odj in self:
            if odj.mail_message_model_id:
                odj.write({'trigger': 'on_create'})

    @api.model
    def _build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
        based on the values provided in the placeholder assistant.

        :param field_name: main field name
        :param sub_field_name: sub field name (M2O)
        :param null_value: default value if the target value is empty
        :return: final placeholder expression """
        expression = ''
        if field_name:
            expression = "{{ object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += " }}"
        return expression

    @api.depends('bot_id')
    def _compute_conversation(self):
        for obj in self:
            if obj.bot_id:
                obj.conversation_ids = \
                    [(6, 0, self.env['kw.chatbot.conversation'].sudo().search(
                        [('dialog_id', '=', obj.bot_id.id)]).mapped('id'))]
            else:
                obj.conversation_ids = False

    @api.depends("model_id")
    def _compute_model_name(self):
        for obj in self:
            obj.model_name = obj.model_id.model

    def _inverse_model_name(self):
        getter = self.env["ir.model"]._get
        for obj in self:
            obj.model_id = getter(obj.model_name)

    @api.model_create_multi
    def create(self, vals_list):
        base_automations = super(Notification, self).create(vals_list)
        self._update_cron()
        self._update_registry()
        return base_automations

    def write(self, vals):
        res = super(Notification, self).write(vals)
        if set(vals).intersection(self.CRITICAL_FIELDS):
            self._update_cron()
            self._update_registry()
        elif set(vals).intersection(self.RANGE_FIELDS):
            self._update_cron()
        return res

    def unlink(self):
        res = super(Notification, self).unlink()
        self._update_registry()
        self._update_cron()
        return res

    def _update_cron(self):
        cron = self.env.ref(
            'kw_chatbot.ir_cron_data_notification_check',
            raise_if_not_found=False)
        if cron:
            actions = self.with_context(active_test=True).search(
                [('trigger', '=', 'on_time')])
            cron.try_write({
                'active': bool(actions),
                'interval_type': 'minutes',
                'interval_number': self._get_cron_interval(actions),
            })

    def _get_cron_interval(self, actions=None):
        def get_delay(rec):
            return rec.trg_date_range * DATE_RANGE_FACTOR[
                rec.trg_date_range_type]

        if actions is None:
            actions = self.with_context(active_test=True).search(
                [('trigger', '=', 'on_time')])
        delay = min(actions.mapped(get_delay), default=0)
        return min(max(1, delay // 10), 4 * 60) if delay else 4 * 60

    def _update_registry(self):
        if self.env.registry.ready and not self.env.context.get('import_file'):
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def _register_hook(self):

        def make_create():
            @api.model_create_multi
            def create(self, vals_list, **kw):
                actions = self.env['kw.chatbot.notification']._get_actions(
                    self, ['on_create', 'on_create_or_write'])
                if not actions:
                    return create.origin(self, vals_list, **kw)
                records = create.origin(
                    self.with_env(actions.env), vals_list, **kw)
                for action in actions.with_context(old_values=None):
                    action = action.sudo()
                    if action.is_active:
                        if action.model_name == 'mail.message' and \
                                action.mail_message_model_id:
                            filter_records = action._filter_post(records)
                            model_name = action.mail_message_model_id.model
                            for rec in filter_records:
                                if rec.model == model_name:
                                    action.notification_message_send(rec)
                        else:
                            filter_records = action._filter_post(records)
                            if filter_records:
                                action.notification_message_send(
                                    filter_records)
                return records.with_env(self.env)
            return create

        def make_external_event():
            pass

        def make_write():
            def write(self, vals, **kw):
                actions = self.env['kw.chatbot.notification']._get_actions(
                    self, ['on_write', 'on_create_or_write'])
                if not (actions and self):
                    return write.origin(self, vals, **kw)
                records = self.with_env(actions.env).filtered('id')
                pre = {
                    action: action._filter_pre(records) for action in actions}
                old_values = {
                    old_vals.pop('id'): old_vals
                    for old_vals in (records.read(list(vals)) if vals else [])
                }
                write.origin(self.with_env(actions.env), vals, **kw)
                for action in actions.with_context(old_values=old_values):
                    action = action.sudo()
                    records, domain_post = action._filter_post_export_domain(
                        pre[action])
                    if action.is_active:
                        if not actions.trigger_field_ids:
                            action.notification_message_send(records)
                        else:
                            for trigger in action.trigger_field_ids:
                                if vals.get(trigger.name):
                                    action.notification_message_send(records)
                return True

            return write

        def make_unlink():
            def unlink(self, **kwargs):
                actions = self.env['kw.chatbot.notification']._get_actions(
                    self, ['on_unlink'])
                records = self.with_env(actions.env)
                for action in actions:
                    action = action.sudo()
                    if action.is_active:
                        records = action._filter_post(records)
                        action.notification_message_send(records)
                return unlink.origin(self, **kwargs)

            return unlink

        patched_models = defaultdict(set)

        def patch(model, name, method):
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = model.env.registry[model._name]
                method.origin = getattr(ModelClass, name)
                setattr(ModelClass, name, method)

        for action_rule in self.with_context({}).search([]):
            Model = self.env.get(action_rule.model_name)

            if Model is None:
                _logger.warning("Action rule with ID %d depends on model %s" %
                                (action_rule.id,
                                 action_rule.model_name))
                continue

            if action_rule.trigger == 'on_create':
                patch(Model, 'create', make_create())

            elif action_rule.trigger == 'on_create_or_write':
                patch(Model, 'create', make_create())
                patch(Model, 'write', make_write())

            elif action_rule.trigger == 'on_write':
                patch(Model, 'write', make_write())

            elif action_rule.trigger == 'on_unlink':
                patch(Model, 'unlink', make_unlink())

            elif action_rule.trigger == 'on_external_event':
                pass

    def _unregister_hook(self):
        NAMES = ['create', 'write', '_compute_field_value',
                 'unlink', '_onchange_methods']
        for Model in self.env.registry.values():
            for name in NAMES:
                try:
                    delattr(Model, name)
                except AttributeError:
                    pass

    def _get_actions(self, records, triggers):
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})
        domain = [(
            'model_name', '=', records._name), ('trigger', 'in', triggers)]
        actions = self.with_context(active_test=True).sudo().search(domain)
        return actions.with_env(self.env)

    def _process(self, records, domain_post=None):
        action_done = self._context['__action_done']
        records_done = action_done.get(self, records.browse())
        records -= records_done
        if not records:
            return

    def _filter_post(self, records):
        return self._filter_post_export_domain(records)[0]

    def _filter_post_export_domain(self, records):
        self_sudo = self.sudo()
        if self_sudo.filter_domain and records:
            _logger.info('domain test create')
            domain = safe_eval.safe_eval(
                self_sudo.filter_domain, self._get_eval_context())
            return records.sudo().filtered_domain(
                domain).with_env(records.env), domain
        else:
            return records, None

    def _get_eval_context(self):
        return {
            'datetime': safe_eval.datetime,
            'dateutil': safe_eval.dateutil,
            'time': safe_eval.time,
            'uid': self.env.uid,
            'user': self.env.user,
            'env': self.env,
        }

    def render_message(self, message, record, **kwargs):
        if kwargs.get('sender_user'):
            add_context = {
                'lang': kwargs.get('sender_user').lang,
                'user': kwargs.get('sender_user')}
        else:
            add_context = {'user': self.env.user, 'lang': self.env.user.lang,
                           'tz': self.env.user.tz}
        render_message = self.env['sms.template']._render_template(
            template_src=message,
            model=self.model_name, res_ids=[record.id],
            add_context=add_context)
        clean = re.compile(r'<(?!/?a(?=>|\s.*>))/?[^>]+?>')
        text = re.sub(r'<br.*?>', '\n', render_message[record.id])
        # from text delete [ and ]
        text = text.replace('[\'', '')
        text = text.replace('\']', '')
        text = text.replace('[', '')
        text = text.replace(']', '')
        text = text.replace('&lt;p&gt;', '')
        text = text.replace('&lt;/p&gt;', '')
        text = text.replace('False', '')
        text = text.replace("href=' ", "href='")
        text = text.replace(" '>", "'>")
        text = re.sub(clean, '', text)
        text = re.sub(r'(?<=\S) +(?=\S)', ' ', text)
        return text

    def prepare_notification_text(self, record, **kwargs):
        message_designer = self.message_designer
        for text_line_id in self.text_line_id:
            if text_line_id.child_notification_id:
                text = ''
                extra_text_for_replace = \
                    text_line_id.child_notification_id.message_designer
                _logger.info('extra_text_for_replace %s',
                             extra_text_for_replace)
                extra_obj = getattr(record, text_line_id.fields_id.name)
                _logger.info('extra_obj %s', extra_obj)
                child_notification = text_line_id.child_notification_id
                extra_obj = child_notification._filter_post(extra_obj)
                template_src = \
                    text_line_id.child_notification_id.message_designer
                count = 0
                for extra_rec in extra_obj:
                    if kwargs.get('sender_user'):
                        add_context = {
                            'lang': kwargs.get('sender_user').lang,
                            'user': kwargs.get('sender_user')}
                    else:
                        add_context = {'lang': self.env.user.lang}
                    count += 1
                    render_extra_text = \
                        self.env['sms.template']._render_template(
                            template_src=template_src,
                            model=extra_rec._name,
                            res_ids=[extra_rec.id], add_context=add_context)
                    clean = re.compile('<.*?>')
                    text1 = \
                        re.sub(r'<br.*?>', '\n', render_extra_text[
                            extra_rec.id])
                    if text_line_id.child_notification_id.line_message_need_serial_number:
                        text1 = '%s. %s' % (count, text1)
                    text1 = re.sub(clean, '', text1)
                    text += text1
                    _logger.info('text %s', text)
                message_designer = self.message_designer.replace(
                    extra_text_for_replace, text)
                _logger.info('message_designer %s', message_designer)
        # render message with language of sender
        return self.render_message(message_designer, record, **kwargs)

    def notification_message_send(
            self, records, conversation_ids=None, **kwargs):
        for obj in self:
            for rec in records:
                text = obj.prepare_notification_text(record=rec)
                if text:
                    if not conversation_ids:
                        conversation_ids = obj.get_conversation(rec)
                    if conversation_ids:
                        if self.bot_id:
                            c_ids = self.bot_id.chatbot_chat_ids.ids
                            conversation_ids = conversation_ids.filtered(
                                lambda x: x.chat_id.id in c_ids)
                        for conversation_id in conversation_ids:
                            obj.send_message(
                                record=rec,
                                text=text,
                                conversation_id=conversation_id,
                                reply_markup=kwargs.get('reply_markup'),
                                bot=kwargs.get('bot'),
                                buttons=kwargs.get('buttons'))

    def add_url(self, text, rec):
        if self.is_add_url:
            burl = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url')
            if self.is_developer_mode:
                burl = self.developer_url.strip()
            url_text = "{}/web#id={}&model={}&view_type=form".format(
                burl, rec.id, rec._name)
            text = '{}\n\nURL: {}'.format(text, url_text)
        return text

    def send_message(self, record, text, conversation_id,
                     **kwargs):
        if not kwargs.get('record_url'):
            text = self.add_url(
                text=text, rec=record, )
        if kwargs.get('bot'):
            if self.use_image_product and record.image_1920:
                _logger.info('Send Foto')
        result = conversation_id.send_message(
            text=text,
            reply_markup=kwargs.get('reply_markup'),
            buttons=kwargs.get('buttons'))
        return result

    def get_conversation(self, record):
        conversation_ids = self.env['kw.chatbot.conversation']
        if self.is_chosen_partner:
            trigg = self.trigger_partner_field_id
            partner_ids = getattr(record, trigg.name)
            if trigg.relation == 'res.users':
                partner_ids = partner_ids.mapped('partner_id')
            if trigg.relation == 'hr.employee':
                partner_ids = partner_ids.mapped('address_id')
            if self.children_trigger_partner_field_id \
                    and record._name == 'mail.message':
                partner = self.mail_message_children_partner(
                    mail_message_id=record)
                partner_ids += partner
            if partner_ids:
                conversation_ids = self.env[
                    'kw.chatbot.conversation'].sudo().search([
                    ('active', '=', True),
                    ('partner_id', 'in', partner_ids.ids), ])
            else:
                _logger.info(
                    'No partner found for notification')
        elif self.is_personal_conversation:
            conversation_ids = self.personal_conversation_ids
        else:
            conversation_ids = self.conversation_ids
        return conversation_ids

    def mail_message_children_partner(self, mail_message_id):
        obj = self.env[mail_message_id.model].browse(mail_message_id.res_id)
        partner_ids = getattr(obj, self.children_trigger_partner_field_id.name)
        if self.children_trigger_partner_field_id.relation == 'res.users':
            partner_ids = partner_ids.mapped('partner_id')
        return partner_ids

    def _filter_pre(self, records):
        self_sudo = self.sudo()
        if self_sudo.filter_pre_domain and records:
            domain = safe_eval.safe_eval(
                self_sudo.filter_pre_domain, self._get_eval_context())
            return records.sudo().filtered_domain(domain).with_env(records.env)
        else:
            return records

    @api.model
    def _check_delay(self, action, record, record_dt):
        if action.trg_date_calendar_id and action.trg_date_range_type == 'day':
            return action.trg_date_calendar_id.plan_days(
                action.trg_date_range,
                fields.Datetime.from_string(record_dt),
                compute_leaves=True, )
        else:
            delay = DATE_RANGE_FUNCTION[action.trg_date_range_type](
                action.trg_date_range)
            return fields.Datetime.from_string(record_dt) + delay

    @api.model
    def _check(self, automatic=False, use_new_cursor=False):
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})
        eval_context = self._get_eval_context()
        for action in self.with_context(active_test=True).search(
                [('trigger', '=', 'on_time')]):
            # flake8: noqa: E501
            last_run = fields.Datetime.from_string(action.last_run) or datetime.datetime.utcfromtimestamp(0)
            domain = []
            context = dict(self._context)
            if action.filter_domain:
                domain = safe_eval.safe_eval(
                    action.filter_domain, eval_context)
            records = self.env[action.model_name].with_context(
                context).search(domain)

            if action.trg_date_id.name == 'date_action_last' \
                    and 'create_date' in records._fields:
                def get_record_dt(record):
                    res = record[action.trg_date_id.name] or record.create_date
                    return res

            else:
                def get_record_dt(record):
                    return record[action.trg_date_id.name]

            now = datetime.datetime.now()
            for record in records:
                record_dt = get_record_dt(record)
                if not record_dt:
                    continue
                action_dt = self._check_delay(action, record, record_dt)
                if last_run <= action_dt < now:
                    try:
                        action.notification_message_send(record)
                    except Exception:
                        _logger.error(traceback.format_exc())

            action.write({'last_run': now.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)})
            if automatic:
                self._cr.commit()


class MessageNotificationLine(models.Model):
    _name = 'kw.message.notification.line'
    _description = 'Message Notification Line'

    notification_id = fields.Many2one('kw.chatbot.notification', )
    child_notification_id = fields.Many2one('kw.chatbot.notification', )
    line_message_need_serial_number = fields.Boolean(
        related='notification_id.line_message_need_serial_number', string='Generate number for message line')
    model_id = fields.Many2one('ir.model', required=True,
                               ondelete='cascade',
                               related='notification_id.model_id', )
    model_name = fields.Char(related='model_id.model', )
    model_notification_id = fields.Many2one('ir.model',
                                            required=True,
                                            ondelete='cascade',
                                            related='notification_id.model_id', )
    model_notification_name = fields.Char(related='model_notification_id.model', )
    fields_id = fields.Many2one('ir.model.fields',
                                ondelete='cascade',
                                )
    sub_model = fields.Char(related='fields_id.relation', )
    sub_fields_id = fields.Many2one('ir.model.fields',
                                    ondelete='cascade',
                                    domain="[('model_id', '=', model_id)]",
                                    )
    text_before = fields.Char(default='', translate=True, )
    text_after = fields.Char(default='', translate=True, )
    sequence = fields.Integer()
    need_after_before_text_new_line = fields.Boolean(default=False, string='New line after text')
    need_after_after_text_new_line = fields.Boolean(default=True, string='New line after text')
    part_message = fields.Char(compute='_compute_part_message', )

    @api.onchange('text_before', 'need_after_before_text_new_line', 'text_after', 'need_after_after_text_new_line')
    def _compute_text(self):
        for rec in self:
            rec.text_before = rec.text_before.replace('<br/>', '') if rec.text_before else ''
            if rec.need_after_before_text_new_line:
                rec.text_before = '%s<br/>' % rec.text_before
            else:
                rec.text_before = '%s' % rec.text_before.replace('<br/>', '')
            rec.text_after = rec.text_after.replace('<br/>', '') if rec.text_after else ''
            if rec.need_after_after_text_new_line:
                rec.text_after = '%s<br/>' % rec.text_after
            else:
                rec.text_after = '%s' % rec.text_after.replace('<br/>', '')

    # @api.onchange('text_after', 'need_after_after_text_new_line')
    # def _compute_text_after(self):
    #     for rec in self:
    #         rec.text_after = rec.text_after.replace('<br/>', '') if rec.text_after else ''
    #         if rec.need_after_after_text_new_line:
    #             rec.text_after = '%s<br/>' % rec.text_after
    #         else:
    #             rec.text_after = '%s' % rec.text_after.replace('<br/>', '')

    def _compute_part_message(self):
        for rec in self:
            text_before = rec.text_before or ''
            text_after = rec.text_after or ''
            if rec.fields_id.ttype in ['many2one'] \
                    and not rec.child_notification_id and rec.sub_fields_id:
                part_message = '%s {{object.%s.%s}} %s' % (
                    text_before,
                    rec.fields_id.name,
                    rec.sub_fields_id.name,
                    text_after)
            elif rec.fields_id.ttype in ['many2many', 'one2many'] \
                    and not rec.child_notification_id and rec.sub_fields_id:
                part_message = '%s {{object.%s.mapped(\'%s\')}} %s' % (
                    text_before,
                    rec.fields_id.name,
                    rec.sub_fields_id.name,
                    text_after)
            elif rec.fields_id.ttype in ['selection'] \
                    and not rec.child_notification_id:
                # we need to get the selection value from the field
                # example: dict(self._fields['type'].selection).get(self.type)
                part_message = '%s {{dict(object._fields[\'%s\']._description_selection(object.env)).get(object.%s)}} %s' % (
                    text_before,
                    rec.fields_id.name,
                    rec.fields_id.name,
                    text_after)

            elif rec.child_notification_id:
                part_message = '%s %s %s' % (text_before,
                                             rec.child_notification_id.message_designer,
                                             text_after)

            else:
                if rec.fields_id:
                    part_message = \
                        '%s {{object.%s}} %s' % (text_before,
                                                 rec.fields_id.name,
                                                 text_after)
                else:
                    part_message = '%s %s' % (text_before, text_after)
            rec.part_message = part_message
            # if rec.line_message_need_serial_number:
            #     rec.part_message = '%s. %s' % (rec.sequence, rec.part_message)


class NotificationFilteredFields(models.Model):
    _name = 'kw.chatbot.notification.filtered.fields'
    _description = 'Notification Filtered Fields'

    notification_id = fields.Many2one(
        comodel_name='kw.chatbot.notification', )
    sequence = fields.Integer()
    model_id = fields.Many2one(
        comodel_name='ir.model', )
    filtered_type = fields.Selection(
        default='conversation', required=True, selection=[
            ('own_model', 'Own Model'),
            ('contact', 'Contact'),
            ('conversation', 'Conversation Activity')], )
    field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        ondelete='cascade',
        domain="[('model_id', '=', model_id),"
               " ('ttype', 'in', ['many2one', 'many2many'])]")
    partner_field_ids = fields.Many2many(
        comodel_name='ir.model.fields', compute_sudo=True,
        compute='_compute_partner_fields', )
    partner_field_id = fields.Many2one(
        comodel_name='ir.model.fields', )

    @api.onchange('field_id', 'filtered_type')
    def _compute_partner_fields(self):
        for obj in  self:
            if not obj.field_id or obj.filtered_type == 'conversation':
                obj.partner_field_ids = [(6, 0, [])]
                obj.partner_field_id = False
            else:
                model_id = self.env['ir.model'].sudo().search(
                    [('model', '=', 'res.partner')], limit=1)
                field_ids = self.env['ir.model.fields'].sudo().search([
                    ('relation', '=', obj.field_id.relation),
                    ('model_id', '=', model_id.id)])
                obj.partner_field_ids = [(6, 0, field_ids.ids)]
                if not field_ids:
                    obj.partner_field_id = False
