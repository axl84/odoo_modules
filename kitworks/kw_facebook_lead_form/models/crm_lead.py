import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    is_facebook_lead_form = fields.Boolean(
        deafult=False)
    kw_facebook_name = fields.Char(
        string='Facebook Name')
    kw_facebook_phone = fields.Char(
        string='Facebook Phone')
    kw_facebook_page = fields.Char()
    kw_facebook_page_id = fields.Many2one(
        comodel_name='kw.facebook.page')

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        for el in result:
            if el.kw_facebook_phone:
                partner_id = el.get_or_create_facebook_partner_id()
                el.write({
                    'phone': el.kw_facebook_phone,
                    'partner_id': partner_id.id, })
            if el.kw_facebook_page:
                fb_page = self.env['kw.facebook.page'].sudo().search(
                    [('id', '=', el.kw_facebook_page)])
                if fb_page:
                    el.write({
                        'name': '{}/{}'.format(
                            fb_page.crm_name_prefix, el.name),
                        'is_facebook_lead_form': True,
                        'kw_facebook_page_id': fb_page.id,
                        "user_id":
                            fb_page.crm_user_id.id
                            if fb_page.crm_user_id else False,
                        "team_id":
                            fb_page.crm_team_id.id
                            if fb_page.crm_team_id else False,
                        "medium_id":
                            fb_page.crm_medium_id.id
                            if fb_page.crm_medium_id else False,
                        "type": fb_page.crm_type,
                        "source_id":
                            fb_page.crm_source_id.id
                            if fb_page.crm_source_id else False, })
        return result

    def get_or_create_facebook_partner_id(self):
        partner_id = self.env['res.partner'].sudo().search([
            ('mobile', '=', self.kw_facebook_phone)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].sudo().create({
                'mobile': self.kw_facebook_phone,
                'name': self.kw_facebook_name
                if self.kw_facebook_name else self.kw_facebook_phone})
        return partner_id
