import logging

from odoo.tools.safe_eval import safe_eval

from odoo import models, fields

_logger = logging.getLogger(__name__)

INPUTS = ['free_input_single', 'question_name',
          'question_email', 'update_contact_field']


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    viber_button_ids = fields.One2many(
        comodel_name='kw.chatbot.step.viber.button',
        inverse_name='step_id', copy=True)

    def _viber_update_contact(self, conversation):
        self.ensure_one()
        but_data = []
        if self.update_contact_field.ttype == 'boolean':
            for but in [True, False]:
                but_data.append(self.viber_button_keyboard_values(
                    name=but, action_body=but))
        if self.update_contact_field.ttype == 'selection':
            s_model = self.env[self.update_contact_field.model]
            s_data = s_model.fields_get(
                allfields=[self.update_contact_field.name])
            for but in s_data[self.update_contact_field.name]['selection']:
                but_data.append(self.viber_button_keyboard_values(
                    name=but[1].capitalize(), action_body=but[0]))
        if self.update_contact_field.ttype in ['many2one', 'many2many']:
            for but in self.env[self.update_contact_field.relation].search([]):
                text = but.with_context(
                    lang=conversation.sender_id.partner_id.lang).name
                but_data.append(self.viber_button_keyboard_values(
                    name=text, action_body=but.id))
        if but_data:
            keyboard = self.get_viber_keyboard_markup(self.text, but_data)
            conversation.send_message(text=self.text, keyboard=keyboard)
            conversation.input_step_id = self.id
            conversation.last_step_id = self.id
            return True
        return False

    # pylint: disable=R0912,R0911
    def viber_get_response(self, conversation, bot, message):
        self.ensure_one()
        _logger.info(self.step_type)
        if conversation.sender_id.partner_id:
            domain = safe_eval(self.triggering_answer_domain) \
                if self.triggering_answer_domain else []
            check_partner = self.env['res.partner'].sudo().search(domain)
            if conversation.sender_id.partner_id not in check_partner:
                step = self.triggering_answer_redirect_step_id
                step.viber_get_response(conversation, bot, message)
                if not conversation.input_step_id:
                    conversation.viber_next_step(step, bot, message)
                return False
        keyboard = []
        if self.viber_keyboard_ids:
            buttons = []
            for k in self.viber_keyboard_ids:
                buttons.append(k.get_keyboard_values())
            keyboard = self.get_viber_keyboard_markup(self.text, buttons)
            conversation.last_step_id = self.id

        # create buttons for step with text type
        if self.viber_button_ids:
            buttons = []
            for k in self.viber_button_ids:
                buttons.append(k.get_keyboard_values())
            keyboard = self.get_viber_keyboard_markup(self.text, buttons)
            conversation.last_step_id = self.id

        if conversation.dialog_id:
            if self.step_type == 'update_contact_field':
                result = self._viber_update_contact(conversation=conversation)
                if result:
                    return True
            if self.step_type in INPUTS:
                conversation.send_message(text=self.text, keyboard=keyboard)
                conversation.input_step_id = self.id
                conversation.last_step_id = self.id
                return True
        if self.step_type == 'create_lead':
            self.create_lead(conversation)
            return True
        if self.step_type == 'forward_operator':
            if not self.is_not_send_send_text:
                conversation.send_message(text=self.text, keyboard=keyboard)
            operator = self.operator_forward(conversation, message)

            # go to step redirect_step_id if the operator is not available
            if not operator and self.redirect_step_id:
                conversation.is_no_reply = True
                step = self.redirect_step_id
                conversation.viber_next_step(
                    step=step, bot=bot, message='', next_step=step)

            return True
        if self.step_type == 'request_notification':
            conversation.send_message(text=self.text)
            conversation.send_message(text=self.text, keyboard=keyboard)
            return False

        # Send message with buttons if set buttons via Viber Buttons Tab
        if self.step_type == 'text' and self.viber_button_ids:
            # send only text
            conversation.send_message(text=self.text)
            # send only buttons
            conversation.send_message(text=self.text, keyboard=keyboard)
            # stop for input
            conversation.input_step_id = self.id
            conversation.last_step_id = self.id
            return True

        conversation.send_message(text=self.text)
        return True


# flake8: noqa: E501
class StepViberButton(models.Model):
    """
    Model for additional buttons with Python code for viber step
    """
    _name = 'kw.chatbot.step.viber.button'
    _description = 'Step Viber button'

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
    #  - sender_user: Telegram user who sent the message
    #  - sender_partner: Telegram user's partner
    # To return an action, assign: action = {...}\n\n\n\n"""

    name = fields.Char(required=True, translate=True, )

    sequence = fields.Integer(default=1, )

    active = fields.Boolean(default=True, )

    step_id = fields.Many2one(comodel_name='kw.chatbot.step', )

    model_id = fields.Many2one(comodel_name='ir.model', string='Model', )

    model_name = fields.Char(related='model_id.model', )

    state = fields.Selection(
        [('code', 'Execute Python Code'),
         ],
        default='code', required=True, copy=True,
        help="Type of server action. The following values are available:\n"
             "- 'Execute Python Code': a block of python code "
             "that will be executed")

    code = fields.Text(string='Python Code', groups='base.group_system',
                       default=DEFAULT_PYTHON_CODE,
                       help="Write Python code that the action will execute. "
                            "Some variables are available for use; help about "
                            "python expression is given in the help tab.")

    # For KeyBoard

    is_location_picker = fields.Boolean(string='Location Picker')

    columns = fields.Selection([('1', '1'), ('2', '2'),
                                ('3', '3'), ('4', '4'),
                                ('5', '5'), ('6', '6')],
                               'Button Horizontal size', default='6')
    rows = fields.Selection(
        [('1', '1'), ('2', '2')], 'Button Vertical size', default='1')

    action_body = fields.Char(string='CallBack text')

    tx_color = fields.Char(string='Text Color', default='#FFFAFA')

    bg_color = fields.Char(string='BackGround Color', default='#1d2327')

    bg_image = fields.Image()

    image_scale_type = fields.Selection(
        [('fit', 'fit'), ('crop', 'crop'), ('fill', 'fill')],
        default='fit', string='Default Image Scale', )

    def get_keyboard_values(self):
        self.ensure_one()
        def_setting = self.env['kw.chatbot.default.viber.buttons'].search([
            ('is_used', '=', True)], limit=1)
        action_type = \
            "reply" if not self.is_location_picker else 'location-picker'

        action_body = {
                    'type': 'run_viber_python',  # this type for custom script
                    'id_button': self.id,  # for search current button
        }

        res = {"Columns": self.columns,
               "Rows": self.rows,
               "Silent": True,
               "ActionType": action_type,
               "ActionBody": str({'text': self.name,
                                  'action_body': str(action_body)}),  # body
               "Text": self.name, }

        if def_setting:
            res = def_setting[0].get_default_setting_value(
                res, self.columns, self.rows)

        if self.tx_color:
            res["Text"] = '<font color="{}">{}</font>'.format(
                self.tx_color, self.name)

        if self.bg_color:
            res["BgColor"] = self.bg_color

        if self.bg_image:
            res["Image"] = \
                '{}/api/viber/image/kw.chatbot.step.viber.keyboard/{}/' \
                'bg_image'.format(self.viber_get_base_url(), self.id)
            res["ImageScaleType"] = self.image_scale_type
            res["Text"] = None

        return res
