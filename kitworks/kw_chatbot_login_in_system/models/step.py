import logging

from odoo import models, fields
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    step_type = fields.Selection(
        selection_add=[('login_in_system', 'Login in system')],
        ondelete={'login_in_system': 'set default'})
    msg_after_login = fields.Text(
        default='You login in system',
        translate=True,
        string='Message after login in system')
    msg_after_unsuccessful_login = fields.Text(
        default='You login in system unsuccessfully',
        translate=True,
        string='Message after unsuccessful login in system')
    go_to_step_unsuccessful_login = fields.Many2one(
        comodel_name='kw.chatbot.step',
        string='Go to step after unsuccessful login in system')

    # pylint: disable=R1705
    def telegram_get_response(self, conversation, bot, message):
        if self.step_type == 'login_in_system':
            self.ensure_one()
            if self.triggering_answer_domain:
                domain = safe_eval(self.triggering_answer_domain)
                # check in sender_id.partner_id in domain
                check_partner = self.env['res.partner'].sudo().search(
                    domain)
                if conversation.sender_id.partner_id in check_partner:
                    _logger.info(f'Partner {conversation.sender_id.partner_id}'
                                 f' in domain {domain}')
                else:
                    _logger.info(f'Partner {conversation.sender_id.partner_id}'
                                 f' not in domain {domain}')
                    return {
                        'redirect': self.triggering_answer_redirect_step_id}
            # Get user for sender
            text = self.with_context(
                lang=conversation.sender_id.partner_id.lang).text
            conversation.send_message(text=text)
            if conversation.sender_id:
                if conversation.sender_id.user_id:
                    self.env.user = conversation.sender_id.user_id
                    text = self.with_context(
                        lang=conversation.sender_id.partner_id.lang
                    ).msg_after_login
                    conversation.send_message(text=text)
                    step = self.go_to_step_id
                    return {'redirect': step}
                else:
                    text = \
                        self.with_context(
                            lang=conversation.sender_id.partner_id.lang
                        ).msg_after_unsuccessful_login
                    conversation.send_message(text=text)
                    step = self.go_to_step_unsuccessful_login
                    return {'redirect': step}
            return True
        return super(Step, self).telegram_get_response(
            conversation, bot, message)
