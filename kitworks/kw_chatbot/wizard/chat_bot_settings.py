import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

dict_messenger = {'Viber': 'kw_chatbot_builder_viber',
                  'Telegram': 'kw_chatbot_builder_telegram',
                  'Facebook': 'kw_chatbot_builder_facebook',
                  'Umnico': 'kw_chatbot_builder_umnico',
                  'Wepster': 'kw_chatbot_builder_wepster',
                  'HelpCrunch': 'kw_chatbot_builder_helpcrunch',
                  'WhatsApp': 'kw_chatbot_builder_whatsapp'}
RUN_AFTER_PREFIX = 'run_after_'
RUN_BEFORE_PREFIX = 'run_before_'


class SetupChatBotWizard(models.TransientModel):
    _name = 'setup.chat.bot.wizard'
    _description = 'Setup Chat Bot Wizard'
    _steps = [
        ('step_messenger', 'Step 1. Choose Messenger'),
        ('step_add_name_operator', 'Step 2. Add Name Operator'),
        ('step_create_partner', 'Step 3. Create Partner'),
        ('step_company', 'Step 4. Choose Company'),
    ]

    type_dialog = fields.Selection(
        [('is_communication', 'Communication'),
         ('is_consultant', 'Consultant'),
         ('is_communication_and_consultant', 'Communication and Consultant'),
         ], default='is_communication_and_consultant')
    company_ids = fields.Many2many(
        comodel_name='res.company',
        required=False,
        default=lambda self: [(6, 0, [self.env['res.company'].search(
            [], limit=1).id])]
    )
    messenger_ids = fields.Many2many('kw.chatbot.messenger', required=False, )
    is_create_partner = fields.Boolean(default=True, required=False, )
    state = fields.Char(default='step_messenger')
    state_name = fields.Char(compute='_compute_state_index_and_visibility')
    state_index = fields.Integer(compute='_compute_state_index_and_visibility')
    show_previous = fields.Boolean(
        compute='_compute_state_index_and_visibility')
    show_next = fields.Boolean(compute='_compute_state_index_and_visibility')
    show_finish = fields.Boolean(compute='_compute_state_index_and_visibility')
    add_name_operator = fields.Boolean(default=True, required=False, )

    def action_finish(self):
        self.action_create()
        # reload page
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.depends('state')
    def _compute_state_index_and_visibility(self):
        module_obj = self.env['ir.module.module'].search(
            [('name', '=', 'kw_chatbot_builder')], limit=1
        )
        if module_obj and module_obj.state != 'installed':
            module_obj.button_immediate_install()

        for conf in self:
            steps_count = len(self._steps)

            conf.state_name = dict(self._steps).get(conf.state)
            conf.state_index = self._steps.index((conf.state, conf.state_name))
            conf.show_previous = conf.state_index != 0
            conf.show_next = conf.state_index + 1 != steps_count
            conf.show_finish = conf.state_index + 1 == steps_count

    @staticmethod
    def get_form_xml_id():
        raise NotImplementedError

    def get_action_view(self):
        self.ensure_one()
        # view_xml_id = self.get_form_xml_id()
        view = self.env.ref('kw_chatbot.setup_chat_bot_wizard_wizard_menu')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Setup Chat Bot Wizard',
            'view_mode': 'form',
            'view_id': view.id,
            'res_model': self._name,
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def run_step_action(self, prefix):
        if not self.state:
            return False

        try:
            return getattr(self, prefix + self.state)()
        except AttributeError:
            return True

    def action_eraze(self):
        self.ensure_one()
        wizards_to_unlink = self.search([
            ('integration_id', '=', self.integration_id.id),
        ])
        wizards_to_unlink.unlink()

    def action_next_step(self):
        is_before_choose_company = self.state == 'step_create_partner'

        if is_before_choose_company and len(self.env.user.company_ids) == 1:
            self.action_finish()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        if self.run_step_action(RUN_AFTER_PREFIX):
            next_step_index = self.state_index + 1
            if next_step_index < len(self._steps):
                self.state = self._steps[next_step_index][0]
                self.run_step_action(RUN_BEFORE_PREFIX)
            else:
                self.action_finish()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }

        return self.get_action_view()

    # def action_next_step(self):
    #     if self.run_step_action(RUN_AFTER_PREFIX):
    #         self.state = self._steps[self.state_index + 1][0]
    #         self.run_step_action(RUN_BEFORE_PREFIX)

    #     return self.get_action_view()

    def action_previous_step(self):
        self.state = self._steps[self.state_index - 1][0]
        self.run_step_action(RUN_BEFORE_PREFIX)

        return self.get_action_view()

    def action_create(self):
        self.env['kw.chatbot.dialog'].search([]).unlink()
        for messenger in self.messenger_ids:
            messenger_name = messenger.name
            messenger_code = dict_messenger.get(messenger_name)
            module = self.env['ir.module.module'].search(
                [('name', '=', messenger_code)], limit=1)
            if module.state != 'installed':
                module.button_immediate_install()
            for company in self.company_ids:
                self.env['kw.chatbot.dialog'].create({
                    'company_id': company.id,
                    'name': f'Consultant bot {company.name}',
                    'bots_type': 'is_consultant_bot',
                    'is_partner': self.is_create_partner,
                })
                self.env['kw.chatbot.dialog'].create({
                    'company_id': company.id,
                    'name': f'Customer bot {company.name}',
                    'bots_type': 'is_communication_bot',
                    'is_partner': self.is_create_partner,
                    'chatbot_step_ids': [(0, 0, {
                        'text': 'Hello',
                        'alias_ids': [(0, 0, {'name': '/start'})]})],
                })

    def run_before_step_company(self):
        return True

    def run_before_step_messenger(self):
        return True

    def run_before_step_create_partner(self):
        return True

    def run_before_step_add_name_operator(self):
        if not self.messenger_ids:
            raise UserError(_('Please select Messenger'))
        return True

    def run_before_step_finish(self):
        return True
