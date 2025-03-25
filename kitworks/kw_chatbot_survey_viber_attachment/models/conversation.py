import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    def viber_pre_response(self, bot, message):
        self.ensure_one()
        if self.is_quiz_start and self.survey_question_id and \
                self.survey_question_id.question_type == 'file':
            self.is_viber_send = True
            if not self.chatbot_message_id.attachment_ids:
                text = self.survey_question_id.kw_viber_file_error_message \
                    if self.survey_question_id.kw_viber_file_error_message \
                    else _('You should send file for this question')
                self.send_message(text=text)
                return True
            if self.user_input_id and self.chatbot_message_id.attachment_ids:
                user_input_id = self.sudo().user_input_id
                if not user_input_id.kw_conversation_id:
                    user_input_id.kw_conversation_id = self.id
                attachment_ids = self.chatbot_message_id.attachment_ids
                self.env['survey.user_input.line'].create({
                    'user_input_id': self.user_input_id.id,
                    'answer_type': self.survey_question_id.question_type,
                    'value_file_ids': [(6, 0, attachment_ids.ids)],
                    'question_id': self.survey_question_id.id, })
                values = {'values': False}
                self.sudo().user_input_id._save_lines(
                    question=self.survey_question_id,
                    answer=values,
                    comment='{}'.format(self.survey_question_id.id))
                if not self.question_and_page_ids and self.is_quiz_start:
                    self.sudo().user_input_id._mark_done()
                    self.last_step_id.end_quiz(
                        conversation=self, bot=bot, message=message,
                        step_id=self.last_step_id.go_to_step_id)
                    return True
        return super().viber_pre_response(bot, message)
