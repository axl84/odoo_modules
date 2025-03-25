import logging

from odoo import models, fields, api
from odoo.osv.expression import AND, OR

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    kw_phone_cleaned = fields.Char()

    kw_mobile_cleaned = fields.Char()

    kw_phone_number_name = fields.Char(
        compute='_compute_kw_phone_number_name', store=True, index=True,
        compute_sudo=True, )
    kw_phone_number_display = fields.Char(
        compute='_compute_kw_phone_number_name', compute_sudo=True,
        search='_search_kw_phone_number_display', )

    def _search_kw_phone_number_display(self, operator, value):
        if operator == 'like':
            operator = 'ilike'
        kw_cleanup_string = self.env['kw.clean.up.mixin'].kw_cleanup_string
        return [('kw_phone_number_name', operator, kw_cleanup_string(value))]

    @api.model
    def create(self, vals):
        kw_clean_digit_only = self.env['kw.clean.up.mixin'].kw_clean_digit_only
        if 'phone' in vals:
            vals['kw_phone_cleaned'] = kw_clean_digit_only(vals['phone'])
        if 'mobile' in vals:
            vals['kw_mobile_cleaned'] = kw_clean_digit_only(vals['mobile'])
        return super().create(vals)

    def write(self, vals):
        kw_clean_digit_only = self.env['kw.clean.up.mixin'].kw_clean_digit_only
        if 'phone' in vals:
            vals['kw_phone_cleaned'] = kw_clean_digit_only(vals['phone'])
        if 'mobile' in vals:
            vals['kw_mobile_cleaned'] = kw_clean_digit_only(vals['mobile'])
        return super().write(vals)

    def format_kw_phone_number_name(self):
        self.ensure_one()
        kw_cleanup_string = self.env['kw.clean.up.mixin'].kw_cleanup_string
        self.kw_phone_number_name = '{}{}{}{}{}'.format(
            kw_cleanup_string(self.phone),
            kw_cleanup_string(self.mobile),
            kw_cleanup_string(self.name),
            kw_cleanup_string(self.email),
            kw_cleanup_string(
                self.parent_id.name if self.parent_id else ''))

        name = '{}'.format(self.name)
        if self.parent_id:
            name = '{}, {}'.format(self.parent_id.name, name)
        if self.mobile:
            name += ' {}'.format(self.mobile)
        if self.phone:
            name += ' {}'.format(self.phone)
        self.kw_phone_number_display = name.strip()

    @api.depends('phone', 'mobile', 'name', 'email', 'parent_id',
                 'parent_id.name', )
    def _compute_kw_phone_number_name(self):
        for obj in self:
            obj.format_kw_phone_number_name()

    # pylint: disable=R1710,W0222
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not isinstance(limit, int):
            limit = 100
        args = [] if not args else args.copy()
        result = super().name_search(
            name=name, args=args, operator=operator, limit=limit)
        if result and len(result) >= limit:
            return result
        ids = [x[0] for x in result] if result else []
        kw_cleanup_string = self.env['kw.clean.up.mixin'].kw_cleanup_string
        name = kw_cleanup_string(name)
        if args:
            args = AND([
                args,
                OR([
                    [('id', 'in', ids)],
                    [('kw_phone_number_name', 'ilike', name)]
                ])
            ])
        else:
            args = [
                '|', ('id', 'in', ids),
                ('kw_phone_number_name', 'ilike', name)]
        result = self.env['res.partner'].search(args, limit=limit)
        return [(x.id, x.kw_phone_number_display or x.name) for x in result]
