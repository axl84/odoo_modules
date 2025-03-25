import logging
import werkzeug

from odoo import http, tools
from odoo.http import request

_logger = logging.getLogger(__name__)


class LivechatBotController(http.Controller):

    @http.route('/im_livechat_bot/handle/call', type='json', auth='public')
    def livechat_handle_call(self, **kwargs):
        _logger.info('livechat_handle_call')
        if kwargs:
            channel = request.env['discuss.channel'].sudo().search([
                ('uuid', '=', kwargs.get('uuid'))], limit=1)
            res_partner_bot = channel.channel_partner_ids.filtered(
                lambda x: x.is_livechat_bot)
            if res_partner_bot:
                chat = request.env['kw.chatbot.chat'].sudo().search([
                    ('odoo_livechat_res_partner_id', '=', res_partner_bot.id)
                ], limit=1)
                if not chat:
                    # _logger.info('Wrong chat connection')
                    return 'Invalid url'
                # _logger.info([i.name for i in channel.channel_partner_ids])
                chat.odoo_livechat_process_call(channel, kwargs)
        return None

    @http.route('/im_livechat_bot/load_templates', type='json',
                auth='none', cors="*")
    def load_bot_templates(self, **kwargs):
        _logger.info('load_bot_templates')
        templates = [
            'mail/static/src/xml/abstract_thread_window.xml',
            'mail/static/src/xml/discuss.xml',
            'mail/static/src/xml/thread.xml',
            'kw_chatbot/static/src/xml/thread.xml',
            'im_livechat/static/src/xml/im_livechat.xml',
        ]
        return [tools.file_open(tmpl, 'rb').read() for tmpl in templates]


class LinkTracker(http.Controller):

    @http.route('/chatbot/<string:code>', type='http',
                auth='public', website=True)
    def chatbot_full_url_redirect(self, code, **post):
        country_code = request.session.geoip and (request.session.geoip.get(
            'country_code') or False)
        request.env['link.tracker.click'].sudo().add_click(
            code,
            ip=request.httprequest.remote_addr,
            country_code=country_code
        )
        redirect_url = request.env['link.tracker'].get_url_from_code(code)
        # _logger.info(redirect_url)
        return werkzeug.utils.redirect(redirect_url or '', 301)
