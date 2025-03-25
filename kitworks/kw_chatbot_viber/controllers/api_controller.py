import logging

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Binary

_logger = logging.getLogger(__name__)

content_route = [
    '/api/viber/image/<string:model>/<int:id>/<string:field>',
]


class ApiController(http.Controller):

    # pylint: disable=redefined-builtin
    @http.route(route=content_route, methods=['GET'],
                type='http', auth='public')
    def content_viber_image(self, id=None, model='ir.attachment',
                            field='datas', **kw):
        if model == 'ir.attachment':
            domain = [('id', '=', id)]
        else:
            domain = [('res_id', '=', id), ('res_model', '=', model),
                      ('res_field', '=', field), ]
        attachment = request.env['ir.attachment'].sudo().search(
            domain, limit=1, order='create_date DESC')
        if not attachment:
            _logger.debug('No file or file_error')

        res = Binary._content_image(
            request, id=attachment.id,
            filename=attachment.name, filename_field='name',
            access_token=attachment.generate_access_token()[0])
        return res
