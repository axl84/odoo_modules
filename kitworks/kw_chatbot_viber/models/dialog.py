from ast import literal_eval
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Step(models.Model):
    _inherit = 'kw.chatbot.step'

    viber_keyboard_ids = fields.One2many(
        comodel_name='kw.chatbot.step.viber.keyboard',
        inverse_name='step_id', )

    @api.onchange('answer_ids')
    def _compute_answer_viber(self):
        for obj in self:

            # To avoid duplication of buttons
            if not isinstance(obj.id, int):
                continue

            obj.viber_keyboard_ids = False
            ids = []
            for ans in obj.answer_ids.sorted('sequence'):
                if not ans.name:
                    continue
                keyboard = self.env[
                    'kw.chatbot.step.viber.keyboard'].sudo().create({
                        'name': ans.name,
                        'step_id': self.id,
                        'action_body': ans.name, })
                keyboard.name = ans.name
                languages = self.env['res.lang'].search(
                    [('active', '=', 'true')])
                for lang in languages.mapped('code'):
                    lang_answer = ans.with_context(lang=lang).name
                    if lang_answer:
                        keyboard.with_context(lang=lang).name = lang_answer
                ids.append(keyboard.id)
            obj.viber_keyboard_ids = [(6, 0, ids)]

    def viber_get_base_url(self):
        self.ensure_one()
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return burl

    def viber_button_keyboard_values(self, name, action_body, columns=6,
                                     rows=1, button_type='keyboard'):
        self.ensure_one()
        def_setting = self.env['kw.chatbot.default.viber.buttons'].search([
            ('is_used', '=', True),
            ('button_type', '=', button_type)], limit=1)
        res = {"Columns": columns,
               "Rows": rows,
               "Silent": True,
               "ActionType": "reply",
               "ActionBody": str({'text': name,
                                  'action_body': action_body}),
               "Text": name, }
        if def_setting:
            res = def_setting[0].get_default_setting_value(res, columns, rows)
        image_button = self.env['kw.chatbot.viber.image.button'].search([
            ('name', '=', name)], limit=1)
        if image_button and button_type == 'keyboard':
            res["Image"] = \
                '{}/api/viber/image/kw.chatbot.viber.image.button/{}/' \
                'media_image'.format(
                    self.viber_get_base_url(), image_button.id)
            res["BgMediaType"] = image_button.media_type
            res["ImageScaleType"] = image_button.image_scale_type
            res["Text"] = None
        return res

    def viber_button_start(self, col=6, row=1):
        self.ensure_one()
        return self.viber_button_keyboard_values('Меню', '/start', col, row)

    def get_viber_keyboard_markup(self, text, buttons, action_body=None):
        self.ensure_one()
        if not action_body and not buttons:
            action_body = '/start'
        def_setting = self.env['kw.chatbot.default.viber.buttons'].search([
            ('is_used', '=', True)], limit=1)
        if text and action_body:
            tx = self.viber_button_keyboard_values(
                name=text, action_body=action_body, columns=6, rows=1)
            buttons.insert(0, tx)
        return {"Type": "keyboard",
                "BgColor":
                    def_setting[0].bg_color if def_setting else "#c8c8c8",
                "DefaultHeight": False,
                "Buttons": buttons}

    def get_viber_rich_media(self, text, buttons, bgr=False):
        self.ensure_one()
        if text:
            buttons.insert(0, self.viber_button_keyboard_values(
                text, '/start', 6, 1, button_type='rich_media'))
        def_setting = self.env['kw.chatbot.default.viber.buttons'].search([
            ('is_used', '=', True)], limit=1)
        return {"Type": "rich_media",
                "BgColor":
                    def_setting[0].bg_color if def_setting else "#d9d9d9",
                "ButtonsGroupColumns": 6,
                "ButtonsGroupRows": bgr if bgr else len(buttons),
                "Buttons": buttons}

    def viber_get_response(self, conversation, bot, message):
        self.ensure_one()
        # _logger.info('Step viber_get_response')
        text = message.get('text')
        if 'action_body' in text:
            text = literal_eval(text)['action_body']
        if (self.name == text or self.env['kw.chatbot.step.alias'].sudo(
        ).search([('name', '=', text),
                  ('step_id', '=', self.id)], limit=1)):
            keyboard = []
            if self.viber_keyboard_ids:
                buttons = []
                for k in self.viber_keyboard_ids:
                    buttons.append(k.get_keyboard_values())
                keyboard = self.get_viber_keyboard_markup(self.text, buttons)
            conversation.send_message(text=self.text,
                                      keyboard=keyboard)
            return True
        return None


class SetDefaultViberButtons(models.Model):
    _name = 'kw.chatbot.default.viber.buttons'
    _description = 'Default viber buttons customization'

    name = fields.Char(required=True, )
    is_used = fields.Boolean()
    button_type = fields.Selection(
        [('keyboard', 'Keyboard'), ('rich_media', 'Rich Media')],
        default='keyboard', required=True, )
    text_valign = fields.Selection(
        [('top', 'Top'), ('middle', 'Middle'), ('bottom', 'Bottom')],
        default='middle', required=True, )
    text_halign = fields.Selection(
        [('left', 'Left'), ('center', 'Center'), ('right', 'Right')],
        default='center', required=True, )
    text_size = fields.Selection(
        [('small', 'small'), ('regular', 'regular'), ('large', 'large')],
        default='regular', string='Default Text Size', required=True, )
    text_opacity = fields.Integer(help='Text Opticai setting 0 100')
    bg_color = fields.Char(string='Default BackGround Color',
                           default='#1d2327', required=True, )
    bg_btn_color = fields.Char(string='Default Button BackGround Color',
                               default='#1d2327', required=True, )
    tx_color = fields.Char(string='Default Text Color',
                           default='#FFFAFA', required=True, )
    bg_media_type = fields.Selection([('picture', 'picture'), ('gif', 'gif')],
                                     default='picture',
                                     string='Default Media Type', )
    media_scale_type = fields.Selection(
        [('fit', 'fit'), ('crop', 'crop'), ('fill', 'fill')],
        default='fit', string='Default Media Scale', )
    bg_media = fields.Char(string='Default Media URL')
    image = fields.Char(string='Default Image URL')
    image_scale_type = fields.Selection(
        [('fit', 'fit'), ('crop', 'crop'), ('fill', 'fill')],
        default='fit', string='Default Image Scale', )
    # Media Images
    bg_media_image = fields.Image()
    # Rich Media Images
    viber_image_6_1 = fields.Image()
    viber_image_6_2 = fields.Image()
    viber_image_6_3 = fields.Image()
    viber_image_6_4 = fields.Image()
    viber_image_6_5 = fields.Image()
    viber_image_6_6 = fields.Image()

    def viber_get_base_url(self):
        self.ensure_one()
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return burl

    def viber_get_media(self, columns=6, rows=1):
        self.ensure_one()
        columns, rows = int(columns), int(rows)
        if columns != 6:
            rows = int((6 / columns) * rows)
        image_url = self.bg_media
        if self.bg_media_image:
            image_url = '{}/api/viber/' \
                        'image/kw.chatbot.default.viber.buttons/{}/' \
                        'bg_media_image'.format(self.viber_get_base_url(),
                                                self.id)
        if getattr(self, f'viber_image_6_{rows}'):
            image_url = '{}/api/viber/' \
                        'image/kw.chatbot.default.viber.buttons/{}/' \
                        'viber_image_6_{}'.format(self.viber_get_base_url(),
                                                  self.id, rows)
        return image_url

    def get_default_setting_value(self, value, columns, rows):
        self.ensure_one()
        value["TextHAlign"] = self.text_halign
        value["BgColor"] = self.bg_btn_color
        if self.bg_media_type:
            value["BgMediaType"] = self.bg_media_type
            value["BgMedia"] = self.viber_get_media(columns, rows)
            value["BgMediaScaleType"] = self.media_scale_type
        if self.image:
            value["Image"] = self.image
            value["ImageScaleType"] = self.image_scale_type
        value["TextSize"] = self.text_size
        value["Text"] = '<font color="{}">{}</font>'.format(
            self.tx_color, value["Text"])
        value["TextVAlign"] = self.text_valign
        return value


class StepViberKeyboard(models.Model):
    _name = 'kw.chatbot.step.viber.keyboard'
    _description = 'Step viber Keyboard'

    name = fields.Char(required=True, help='Free text. Valid and allowed HTML'
                                           ' tags Max 250 characters.')
    columns = fields.Selection([('1', '1'), ('2', '2'),
                                ('3', '3'), ('4', '4'),
                                ('5', '5'), ('6', '6')],
                               'Button Horizontal size', default='6')
    rows = fields.Selection(
        [('1', '1'), ('2', '2')], 'Button Vertical size', default='1')
    action_body = fields.Char(string='CallBack text')
    is_location_picker = fields.Boolean(string='Location Picer')
    bg_color = fields.Char(string='BackGround Color', default='#1d2327')
    tx_color = fields.Char(string='Text Color', default='#FFFAFA')
    active = fields.Boolean(default=True, )
    step_id = fields.Many2one(comodel_name='kw.chatbot.step', )
    image = fields.Char(string='Default Image URL')
    image_scale_type = fields.Selection(
        [('fit', 'fit'), ('crop', 'crop'), ('fill', 'fill')],
        default='fit', string='Default Image Scale', )
    bg_image = fields.Image()

    def viber_get_base_url(self):
        self.ensure_one()
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return burl

    def get_keyboard_values(self):
        self.ensure_one()
        def_setting = self.env['kw.chatbot.default.viber.buttons'].search([
            ('is_used', '=', True)], limit=1)
        action_type = \
            "reply" if not self.is_location_picker else 'location-picker'
        res = {"Columns": self.columns,
               "Rows": self.rows,
               "Silent": True,
               "ActionType": action_type,
               "ActionBody": str({'text': self.name,
                                  'action_body': self.action_body}),
               "Text": self.name, }
        if def_setting:
            res = def_setting[0].get_default_setting_value(
                res, self.columns, self.rows)
        if self.tx_color:
            res["Text"] = '<font color="{}">{}</font>'.format(
                self.tx_color, self.name)
        if self.bg_color:
            res["BgColor"] = self.bg_color
        if self.bg_image:
            res["Image"] = \
                '{}/api/viber/image/kw.chatbot.step.viber.keyboard/{}/' \
                'bg_image'.format(self.viber_get_base_url(), self.id)
            res["ImageScaleType"] = self.image_scale_type
            res["Text"] = None
        return res


class ChatbotDialogAnswer(models.Model):
    _inherit = 'chatbot.dialog.answer'

    @api.model
    def create(self, vals_list):
        result = super(ChatbotDialogAnswer, self).create(vals_list)
        for obj in result:
            if obj.dialog_step_id:
                obj.dialog_step_id._compute_answer_viber()
        return result

    def write(self, vals):
        result = super(ChatbotDialogAnswer, self).write(vals)
        for obj in self:
            if vals.get('name') or vals.get('sequence') and obj.dialog_step_id:
                obj.dialog_step_id._compute_answer_viber()
        return result

    def unlink(self):
        dialog_step_id = self.dialog_step_id
        result = super(ChatbotDialogAnswer, self).unlink()
        if dialog_step_id:
            dialog_step_id._compute_answer_viber()
        return result
