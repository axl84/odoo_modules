import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StatementImportMixin(models.AbstractModel):
    _name = 'kw.finance.statement.import.mixin'
    _description = 'Statement Import Mixin'

    def get_autocreated_tag(self):
        category = self.env['res.partner.category']
        tag = category.search([('name', '=', 'autocreated')], limit=1)
        if tag:
            return tag
        return category.create({'name': 'autocreated'})

    def get_bank(self, bic, name=False):
        res_bank = self.env['res.bank']
        bank = res_bank.search([('bic', '=', bic)], limit=1)
        if bank:
            return bank
        return res_bank.create({'bic': bic, 'name': name or bic})

    def get_partner(self, enterprise_code, partner_name=False,
                    acc_number=False, bic=False, bank_name=False, create=True,
                    use_name_search=True):
        res_partner = self.env['res.partner']

        partner = res_partner.search(
            [('enterprise_code', '=', enterprise_code)], limit=1)

        if not partner and acc_number:
            bank_acc = self.env['res.partner.bank'].search(
                [('acc_number', '=', acc_number)], limit=1)
            if bank_acc:
                partner = res_partner.search(
                    [('id', '=', bank_acc.partner_id.id)], limit=1)

        if not partner and use_name_search and partner_name:
            partner = res_partner.search(
                [('name', '=', partner_name)], limit=1)

        if not partner and create:
            tag = self.get_autocreated_tag()
            partner = res_partner.create({
                'enterprise_code': enterprise_code,
                'name': partner_name,
                'category_id': [(4, tag.id)] if tag else False
            })
            self.get_bank(bic=bic, name=bank_name)
            self.set_bank_acc(partner_id=partner.id, acc=acc_number, bic=bic)

        if partner:
            self.get_bank(bic=bic, name=bank_name)
            self.set_bank_acc(
                partner_id=partner.id, acc=acc_number, bic=bic)
            return partner

        return False

    def get_partner_by_info(self, name=False, phone=False, email=False,
                            create=False, ):
        res_partner = self.env['res.partner']
        if name:
            partner = res_partner.search(
                [('name', '=', name)], limit=1)
            if partner:
                return partner
        if phone:
            partner = res_partner.search(
                ['|', ('phone', '=', phone), ('mobile', '=', phone)], limit=1)
            if partner:
                return partner
        if email:
            partner = res_partner.search(
                [('email', '=', email)], limit=1)
            if partner:
                return partner
        if create and name:
            partner = res_partner.create({
                'name': name, 'phone': phone, 'email': email, })
            return partner
        return False

    # pylint: disable=R1710
    def set_bank_acc(self, partner_id, acc, bic):
        bank_acc = self.env['res.partner.bank'].search(
            [('acc_number', '=', acc)], limit=1)
        if bank_acc:
            if not bank_acc.partner_id:
                bank_acc.partner_id = partner_id
        else:
            return self.env['res.partner.bank'].create({
                'partner_id': partner_id,
                'acc_number': acc,
                'bank_id': self.get_bank(bic=bic).id
            })
