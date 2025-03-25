import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ViberImageButton(models.Model):
    _name = 'kw.chatbot.viber.image.button'
    _description = 'Viber Image Button'

    name = fields.Char(required=True, )
    is_used = fields.Boolean(default=True, )
    media_type = fields.Selection([('picture', 'picture'), ('gif', 'gif')],
                                  default='picture', )
    image_scale_type = fields.Selection(
        [('fit', 'fit'), ('crop', 'crop'), ('fill', 'fill')],
        default='fill', string='Image Scale', )
    media_image = fields.Image()
