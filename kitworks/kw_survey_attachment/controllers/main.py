import base64
from odoo import http
from odoo.http import request
from odoo.addons.survey.controllers import main


class Survey(main.Survey):

    @http.route(["/web/binary/download/<int:file_id>"], type='http',
                auth="public", website=True, sitemap=False)
    # pylint: disable=W0612
    def binary_download(self, file_id=None, **post):
        if file_id:
            file = request.env['ir.attachment'].browse([file_id])
            if file:
                req = request.env['ir.http']
                status, headers, content = req.binary_content(
                    model='ir.attachment', id=file.id,
                    field='datas',
                    filename_field=file.name)
                content_base64 = base64.b64decode(content) if content else ''
                headers.append(('Content-Type', 'application/octet-stream'))
                headers.append(('Content-Length', len(content_base64)))
                headers.append((
                    'Content-Disposition', 'attachment; filename={};'.format(
                        file.name)))
                return request.make_response(content_base64, headers)
        return False
