from odoo import http
from odoo.http import request


class RepairReport(http.Controller):
    @http.route('/checkbox/report/<string:action>/<int:record_id>',
                type='http', auth="public", website=True)
    def repair_report(self, action, record_id):
        pdf, _ = request.env['ir.actions.report'].sudo(
        )._render_qweb_pdf(action, [record_id])
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf))
        ]
        return request.make_response(pdf, headers=headers)
