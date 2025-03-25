import logging

from odoo import models, api, _

_logger = logging.getLogger(__name__)


class LinkTracker(models.Model):
    _inherit = 'link.tracker'

    @api.model
    def get_url_from_code(self, code):
        code_rec = self.env['link.tracker.code'].sudo().search(
            [('code', '=', code)])

        if not code_rec:
            return super(LinkTracker, self).get_url_from_code(code)

        if not hasattr(code_rec.link_id, 'messenger_id'):
            return super(LinkTracker, self).get_url_from_code(code)

        if code_rec.link_id.messenger_id.provider != 'telegram':
            return super(LinkTracker, self).get_url_from_code(code)
        res = code_rec.link_id.url + '?start={}'.format(
            code_rec.link_id.id)
        return res

    def action_visit_page(self):
        if self.messenger_id.provider != 'telegram':
            return super(LinkTracker, self).action_visit_page()
        return {
            'name': _("Visit Webpage"),
            'type': 'ir.actions.act_url',
            'url': self.url + '?start={}'.format(
                self.id),
            'target': 'new',
        }
