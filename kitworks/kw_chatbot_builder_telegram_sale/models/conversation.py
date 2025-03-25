import logging
import ast
import base64

from telebot import types

from odoo.exceptions import UserError

from odoo.tools.safe_eval import safe_eval

from odoo import models, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    # pylint: disable=R0912,R0911
    def telegram_get_response(self, bot, message):
        text = self.telegram_get_message_data(message)
        if text == '/start':
            self.last_step_id.operation_sale = 'standard'
        # step_alias = self.env['kw.chatbot.step.alias'].sudo().search([
        #     ('name', '=', text), ])
        # trig_step = self.env['kw.chatbot.step'].sudo().search([
        #     ('alias_ids', 'in', step_alias.ids),
        #     ('dialog_id', '=', self.dialog_id.id)])
        # if trig_step:
        #     if trig_step.select_flow == 'sale':
        #         self.last_step_id = trig_step
        #         self.last_step_id.telegram_get_response(self, bot, message)
        #         self.write({
        #             'input_step_id': False,
        #             'is_telegram_send': True,
        #             'last_step_id': trig_step.id,
        #         })
        # if trig_step.select_flow == 'sale':
        #     return self.sale_start(bot, message)
        if text == '/sale':
            self.last_step_id.operation_sale = 'standard'
            return self.sale_start(bot, message)
        if self.last_step_id.operation_sale == 'input_quantity':
            self.last_step_id.operation_sale = 'standard'
            self.sale_input_quantity(bot, message, text)
            return True
        if self.last_step_id.operation_sale == 'input_shipping_address':
            self.last_step_id.operation_sale = 'standard'
            return self.sale_input_shipping_address(bot, message, text)

        if isinstance(message, types.CallbackQuery):
            # get callback data
            try:
                res = ast.literal_eval(message.data)
            except SyntaxError:
                res = {}
            try:
                res['id_chat'] = message.message.chat.id
            except TypeError:
                _logger.info('TypeError: %s', message)
                # get button
            if not isinstance(res, int):
                if res.get('id_button'):
                    button = self.env['kw.chatbot.step.telegram.button'].search([
                        ('id', '=', res.get('id_button')),
                    ])
                    if button.state == 'sale':
                        self.telegram_get_response_sale(bot,
                                                        res,
                                                        button,
                                                        **{'type_sale': 'choose_category'})
                        return True
                elif res.get('type_sale'):
                    # pylint: disable=R1705
                    if res.get('type_sale') == 'choose_product':
                        return self.sale_choose_product(bot, res)
                    elif res.get('type_sale') == 'choose_quantity':
                        return self.sale_choose_quantity(bot, res)
                    elif res.get('type_sale') == 'choose_category':
                        res['chat'] = {'id': message.message.chat.id}
                        return self.sale_start(bot, res)
                    elif res.get('type_sale') == 'show_cart':
                        return self.sale_show_cart(bot, res)
                    elif res.get('type_sale') == 'confirm_order':
                        if not self.last_step_id.not_use_delivery and not res.get('skip_confirm_button'):
                            return self.sale_send_select_delivery(bot, res)
                        return self.sale_confirm_order(bot, res)
                    elif res.get('type_sale') == 'remove_from_cart':
                        return self.sale_remove_from_cart(bot, res)
                    elif res.get('type_sale') == 'send_message':
                        msg = self.last_step_id.button_name_enter_quantity
                        self.last_step_id.operation_sale = 'input_quantity'
                        return self.send_message(msg)
                    elif res.get('type_sale') == 'choose_product_without_category':
                        return self.sale_start(bot, message)
                    elif res.get('type_sale') == 'choose_delivery':
                        return self.sale_choose_delivery(bot, res)
                    else:
                        _logger.info('Type sale not found')
                else:
                    _logger.info('Button not found')
        return super().telegram_get_response(bot, message)

    # pylint: disable=R1710
    def sale_send_select_delivery(self, bot, res):
        if not self.last_step_id.not_use_delivery:
            # send msg for choose delivery method
            step = self.last_step_id
            msg = step.with_context(
                lang=self.sender_id.partner_id.lang
            ).message_select_delivery
            if not msg:
                return self.send_message(_('No template message for delivery'))
            # add button for choose delivery method
            markup, buttons = None, []
            markup = types.InlineKeyboardMarkup()
            for delivery in self.env['delivery.carrier'].search([]):
                callback_data = {
                    'type_sale': 'choose_delivery',
                    'delivery_id': delivery.id,
                }
                text = delivery.with_context(
                    lang=self.sender_id.partner_id.lang).name
                btn = types.InlineKeyboardButton(
                    text=text,
                    callback_data=str(callback_data), )
                buttons.append(btn)
            markup.add(*buttons)
            return bot.send_message(res.get('id_chat'),
                                    msg, reply_markup=markup)

    def sale_start(self, bot, message):
        # get msg for start sale and send it
        # get step for start sale
        step = self.last_step_id
        self.write({'last_step_id': step.id})
        if step.not_use_category:
            button = {
                'type_sale': 'choose_category',
            }
            self.telegram_get_response_sale(bot,
                                            message,
                                            button,
                                            **{'type_sale': 'choose_category'})
            return True
        if not step:
            raise UserError(_('No step for start sale'))
        # get msg for start sale
        msg = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).template_message_category
        if not msg:
            return self.send_message(_('No template message for start sale'))
        # send msg with buttons
        # add button
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        for bt in step.buttons_category_ids:
            callback_data = ast.literal_eval(bt.callback_data.replace(
                "'", '"'))
            text = bt.with_context(
                lang=self.sender_id.partner_id.lang).name
            btn = types.InlineKeyboardButton(
                text=text, callback_data=str(callback_data), )
            markup.add(btn)
        markup.add(*buttons)
        if isinstance(message, types.CallbackQuery):
            try:
                user_id = message.from_user.id
            except Exception as e:
                _logger.info(e)
        else:
            user_id = message.get('chat').get('id')
        bot.send_message(user_id, msg, reply_markup=markup)
        return True

    def sale_input_shipping_address(self, bot, message, text):
        # get order
        order = self.get_order()
        step = self.last_step_id
        if not order:
            return self.send_message(text=_('No order'))
        # in note add shipping address
        order.note = text
        # confirm order
        order.sudo().action_confirm()
        # send msg
        msg = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).button_name_after_confirm_order
        # add button for back to category
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        if step.not_use_category:
            markup.add(self.get_button_for_back_to_product(step))
        else:
            markup.add(self.get_button_for_back_to_category(step))
        markup.add(*buttons)
        if isinstance(message, dict):
            _id = message.get('chat').get('id')
        else:
            _id = message.message.chat.id
        bot.send_message(_id, msg, reply_markup=markup)
        # get base url
        if not step.not_use_payment_url:
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url')
            # from order get payment link and send it
            payment_link = order.get_portal_url()
            payment_link = base_url + payment_link
            # add button for payment link
            markup, buttons = None, []
            markup = types.InlineKeyboardMarkup()
            text = step.with_context(
                lang=self.sender_id.partner_id.lang
            ).button_name_payment_url
            btn_payment = types.InlineKeyboardButton(
                text=text, url=payment_link)
            markup.add(btn_payment)
            markup.add(*buttons)
            msg = step.with_context(
                lang=self.sender_id.partner_id.lang
            ).message_payment_url
            bot.send_message(_id, msg, reply_markup=markup)
        self.last_step_id.operation_sale = 'standard'
        if step.go_to_step_id:
            self.telegram_next_step(step, bot, message)
        return True

    def sale_input_quantity(self, bot, message, text):
        # get order
        order = self.get_order()
        if not order:
            return self.send_message(text=_('No order'))
        # get last product
        last_product = self.last_step_id.product_id
        self.last_step_id.product_id = False
        if not last_product:
            return self.send_message(text=_('No product'))
        # get quantity from text
        try:
            quantity = int(text)
        except ValueError:
            self.last_step_id.product_id = last_product
            self.last_step_id.operation_sale = 'input_quantity'
            return self.send_message(
                text=_('Quantity must be integer. Please try again'))
        # if product in order
        if last_product in order.order_line.mapped('product_id'):
            # get order line
            order_line = order.order_line.filtered(
                lambda x: x.product_id == last_product)
            # update quantity
            quantity += order_line.product_uom_qty
            order_line.write({'product_uom_qty': quantity})
        else:
            # create order line
            order_line = order.order_line.create({
                'product_id': last_product.id,
                'product_uom_qty': quantity,
                'order_id': order.id,
            })
        # get msg for add product to cart
        msg = self.last_step_id.with_context(
            lang=self.sender_id.partner_id.lang
        ).notification_add_to_card
        # add button for back to category
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        if self.last_step_id.not_use_category:
            markup.add(self.get_button_for_back_to_product(self.last_step_id))
        else:
            markup.add(self.get_button_for_back_to_category(self.last_step_id))
        markup.add(self.get_button_for_show_cart(self.last_step_id))
        markup.add(*buttons)
        bot.send_message(message.get('chat').get('id'),
                         msg, reply_markup=markup)
        return True

    def sale_remove_from_cart(self, bot, res):
        # remove product from cart
        # get order
        order = self.get_order()
        if not order:
            return self.send_message(text=_('No order'))
        # clear order lines
        order.order_line.unlink()
        # get msg for remove from cart
        step = self.last_step_id
        msg = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).notification_after_clear_cart
        if not msg:
            return self.send_message(text=_('No template message for remove from cart'))
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        if step.not_use_category:
            markup.add(self.get_button_for_back_to_product(step))
        else:
            markup.add(self.get_button_for_back_to_category(step))
        markup.add(*buttons)
        bot.send_message(res.get('id_chat'), msg, reply_markup=markup)
        return True

    # pylint: disable=R1710,R0914
    def telegram_get_response_sale(self, bot, res, button, **kwargs):
        # if button.type_sale == 'choose_category'
        # get all products for this category
        # and send it with buttons
        if kwargs['type_sale'] == 'choose_category':
            # get step for start sale
            if self.last_step_id.select_flow != 'sale':
                step = self.env['kw.chatbot.step'].sudo().search([
                    ('dialog_id', '=', self.dialog_id.id),
                    ('select_flow', '=', 'sale'),
                ], limit=1)
            else:
                step = self.last_step_id
            # get products for this category
            if step.not_use_category:
                domain_category = []
            else:
                domain_category = [('categ_id', '=', button.category_id.id)]
            if step.filter_product_domain:
                domain = safe_eval(
                    step.filter_product_domain, self._get_eval_context())
                domain_category += domain
            products = self.env['product.product'].search(domain_category)

            if not products:
                return self.send_message(
                    text=_('No products for this category'))
            # for each product send msg with buttons for add to cart
            for product in products:
                # get msg for product
                msg = step.message_product_name
                render_msg = self.render_template(
                    step.model_product_id, product, msg)
                if not msg:
                    return self.send_message(
                        text=_('No template message for product'))
                # add button
                markup, buttons = None, []
                markup = types.InlineKeyboardMarkup()
                callback_data = {
                    'type_sale': 'choose_product',
                    'product_id': product.id,
                }
                text = step.with_context(
                    lang=self.sender_id.partner_id.lang
                ).button_name_add_to_cart
                btn = types.InlineKeyboardButton(
                    text=text,
                    callback_data=str(callback_data), )
                markup.add(btn)

                if not step.not_use_category:
                    markup.add(self.get_button_for_back_to_category(step))
                markup.add(*buttons)
                # if step.use_img_product and product.image_1920:
                #     # get imege product
                #     bot.send_photo(
                #         self.telegram_id, base64.b64decode(product.image_1920),
                #         caption=render_msg, reply_markup=markup)
                if step.not_use_category:
                    if step.use_img_product and product.image_1920:
                        # get imege product
                        bot.send_photo(
                            self.telegram_id, base64.b64decode(product.image_1920),
                            caption=render_msg, reply_markup=markup)
                    else:
                        self.send_message(text=render_msg, reply_markup=markup)
                else:
                    if step.use_img_product and product.image_1920:
                        # get imege product
                        bot.send_photo(
                            self.telegram_id, base64.b64decode(product.image_1920),
                            caption=render_msg, reply_markup=markup)
                    else:
                        bot.send_message(res.get('id_chat'),
                                         render_msg, reply_markup=markup)

            return True

    def sale_choose_delivery(self, bot, res):
        step = self.last_step_id
        # get order and delivery
        order = self.get_order()
        delivery = self.env['delivery.carrier'].browse(res['delivery_id'])
        if not order:
            return self.send_message(text=_('Cart is empty'))
        if not delivery:
            return self.send_message(text=_('No delivery'))
        # get product delivery and add it to order
        product_delivery = delivery.product_id
        if not product_delivery:
            return self.send_message(text=_('No product for delivery'))
        if product_delivery in order.order_line.mapped('product_id'):
            order_line = order.order_line.filtered(
                lambda x: x.product_id == product_delivery)
            order_line.write({'product_uom_qty': 1})
        else:
            order.order_line.create({
                'product_id': product_delivery.id,
                'product_uom_qty': 1,
                'order_id': order.id,
            })
        # # get msg for choose delivery method
        # msg = self.last_step_id.with_context(
        #     lang=self.sender_id.partner_id.lang
        # ).message_select_delivery
        # if not msg:
        #     return self.send_message(text=_('No template message for delivery'))
        # # send msg
        # bot.send_message(res.get('id_chat'), msg)
        # # send new cart
        # self.sale_show_cart(bot, res, **{'skip_confirm_button': True})
        # return True
        # send msg for input shipping address
        msg = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).message_input_data_shipping
        self.last_step_id.operation_sale = 'input_shipping_address'
        bot.send_message(res.get('id_chat'), msg)
        return True

    def sale_confirm_order(self, bot, res):
        # get order
        order = self.get_order()
        step = self.last_step_id
        if step.tag_ids:
            order.tag_ids = [(6, 0, step.tag_ids.ids)]
        if not order:
            return self.send_message(text=_('Cart is empty'))
        # send msg for input shipping address
        msg = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).message_input_data_shipping
        self.last_step_id.operation_sale = 'input_shipping_address'
        bot.send_message(res.get('id_chat'), msg)
        return True

    def sale_show_cart(self, bot, res, **kwargs):
        step = self.last_step_id
        # get notification for cart
        msg = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).notification_cart_id
        if not msg:
            return self.send_message(text=_('No notification for cart'))
        # get order
        order = self.get_order()
        if not order:
            return self.send_message(text=_('Cart is empty'))
        # add button for back to category
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        if self.last_step_id.not_use_category:
            markup.add(self.get_button_for_back_to_product(step))
        else:
            markup.add(self.get_button_for_back_to_category(step))
        # add button for confirm order
        if kwargs.get('skip_confirm_button'):
            callback_data = {
                'type_sale': 'confirm_order',
                'skip_confirm_button': True,
            }
        else:
            callback_data = {
                'type_sale': 'confirm_order',
            }
        text = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).message_confirm_order
        btn_confirm = types.InlineKeyboardButton(
            text=text,
            callback_data=str(callback_data), )
        markup.add(btn_confirm)
        # add button for clear cart
        callback_data = {
            'type_sale': 'remove_from_cart',
        }
        text = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).clear_cart_name_button
        btn_clear = types.InlineKeyboardButton(
            text=text,
            callback_data=str(callback_data), )
        markup.add(btn_clear)
        markup.add(*buttons)
        msg.notification_message_send(
            order, conversation_ids=self, reply_markup=markup,
            buttons=buttons, **{'sender_user': self.sender_id.user_id})
        return True

    # def sale_back_to_product(self, bot, res):
    #     button = {
    #         'type_sale': 'choose_category',
    #     }
    #     self.telegram_get_response_sale(bot,
    #                                     message,
    #                                     button,
    #                                     **{'type_sale': 'choose_category'})
    #     return True

    def sale_choose_product(self, bot, res):
        # get product

        product = self.env['product.product'].search(
            [('id', '=', res.get('product_id'))])
        if not product:
            return self.send_message(text=_('Product not found'))
        # get step for start sale
        step = self.last_step_id
        # get msg for product
        msg = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).message_quantity
        render_msg = self.render_template(step.model_product_id, product, msg)
        if not msg:
            return self.send_message(text=_('No template message for product'))
        # add button
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        list_btn = []
        for count in range(1, 6):
            callback_data = {
                'type_sale': 'choose_quantity',
                'pr_id': product.id,
                'q': count,
            }
            btn = types.InlineKeyboardButton(
                text=_(count), callback_data=str(callback_data), )
            list_btn.append(btn)
            if len(list_btn) > 2:
                markup.add(*list_btn)
                list_btn = []
            if count == 5:
                markup.add(*list_btn)
            # markup.add(btn)
        # add button for input quantity
        callback_data = {
            'type_sale': 'send_message',
        }
        text = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).button_name_enter_quantity
        btn_q = types.InlineKeyboardButton(
            text=text, callback_data=str(callback_data), )
        markup.add(btn_q)
        self.last_step_id.product_id = product.id
        markup.add(*buttons)
        bot.send_message(res.get('id_chat'), render_msg, reply_markup=markup)
        return True

    def sale_choose_quantity(self, bot, res):
        # get product
        product = self.env['product.product'].search(
            [('id', '=', res.get('pr_id'))])
        # get sale order
        sale_order = self.get_order()
        step = self.last_step_id
        if step.tag_ids:
            sale_order.tag_ids = [(6, 0, step.tag_ids.ids)]
        msg = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).notification_add_to_card
        if not msg:
            return self.send_message(text=_('No template message for add to cart'))
        # replace variables
        # msg = msg.replace('{product_name}', product.name)
        # msg = msg.replace('{product_q}', str(res.get('q')))
        # add product to sale order
        # if product in sale order
        if product in sale_order.order_line.mapped('product_id'):
            # get line
            # flake8: noqa
            line = sale_order.order_line.filtered(lambda r: r.product_id == product)
            # update quantity
            line.product_uom_qty += res.get('q')

        else:
            # create new line
            self.env['sale.order.line'].sudo().create({
                'order_id': sale_order.id,
                'product_id': product.id,
                'product_uom_qty': res.get('q'),
            })
        # add button for back to category or show cart
        markup, buttons = None, []
        markup = types.InlineKeyboardMarkup()
        if self.last_step_id.not_use_category:
            markup.add(self.get_button_for_back_to_product(step))
        else:
            markup.add(self.get_button_for_back_to_category(step))
        markup.add(self.get_button_for_show_cart(step))
        markup.add(*buttons)
        return bot.send_message(res.get('id_chat'), msg, reply_markup=markup)

    def get_order(self):
        order = self.env['sale.order'].sudo().search([
            ('partner_id', '=', self.sender_id.partner_id.id),
            ('state', '=', 'draft')])
        order.sorted(key=lambda r: r.create_date, reverse=True)
        if not order:
            order = self.env['sale.order'].sudo().create({
                'partner_id': self.sender_id.partner_id.id,
                'state': 'draft',
            })
        return order[0]

    def get_button_for_back_to_category(self, step):
        callback_data = {
            'type_sale': 'choose_category'
        }
        text = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).button_name_back_to_category
        btn_back = types.InlineKeyboardButton(
            text=text,
            callback_data=str(callback_data), )
        return btn_back

    def get_button_for_show_cart(self, step):
        callback_data = {
            'type_sale': 'show_cart'
        }
        text = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).name_button_cart
        btn_cart = types.InlineKeyboardButton(
            text=text, callback_data=str(callback_data), )
        return btn_cart

    def get_button_for_back_to_product(self, step):
        callback_data = {
            'type_sale': 'choose_product_without_category'
        }
        text = step.with_context(
            lang=self.sender_id.partner_id.lang
        ).message_back_to_product
        btn_back = types.InlineKeyboardButton(
            text=text,
            callback_data=str(callback_data), )
        return btn_back
