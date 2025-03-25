from odoo import models


class SmsTracker(models.Model):
    _inherit = 'sms.tracker'

    SMS_STATE_TO_NOTIFICATION_STATUS = {'canceled': 'canceled',
                                        'process': 'process',
                                        'error': 'exception',
                                        'outgoing': 'ready',
                                        'sent': 'sent',
                                        'pending': 'pending',
                                        'queued': 'queued', }

    def _update_sms_notifications(self, notification_status,
                                  failure_type=False, failure_reason=False):
        """Modifications made compare to original:
                add 'queued' status
        """
        notifications_statuses_to_ignore = {
            'canceled': ['canceled', 'process', 'pending', 'sent'],
            'ready': ['ready', 'process', 'pending', 'sent'],
            'process': ['process', 'pending', 'sent'],
            'pending': ['pending', 'sent'],
            'bounce': ['bounce', 'sent'],
            'sent': ['sent'],
            'exception': ['exception'],
            'queued': ['queued'],
        }[notification_status]
        notifications = self.mail_notification_id.filtered(
            lambda n:
            n.notification_status not in notifications_statuses_to_ignore)
        if notifications:
            notifications.write({'notification_status': notification_status,
                                 'failure_type': failure_type,
                                 'failure_reason': failure_reason, })
            if not self.env.context.get('sms_skip_msg_notification'):
                notifications.mail_message_id.\
                    _notify_message_notification_update()
