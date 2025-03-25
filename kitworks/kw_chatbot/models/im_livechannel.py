import logging
from odoo import models

_logger = logging.getLogger(__name__)


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _get_available_users(self):
        self.ensure_one()
        res = super(ImLivechatChannel, self)._get_available_users()
        if not res and len(self.user_ids.ids) == 1:
            res = self.user_ids.filtered(
                lambda user: user.partner_id.is_livechat_bot)
        return res
