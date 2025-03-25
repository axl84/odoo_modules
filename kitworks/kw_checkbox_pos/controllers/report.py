import base64
from odoo import http
from odoo.http import request


class CheckboxQR(http.Controller):
    @http.route('/checkbox/QR/<int:record_id>',
                type='http', auth="public", website=True)
    def qr_report(self, record_id):
        record_id = request.env['pos.order'].sudo().browse([record_id])
        raw_png = base64.b64decode(record_id.checkbox_qr or b'')
        return request.make_response(
            raw_png, headers=[('Content-Type', 'image/png')])
