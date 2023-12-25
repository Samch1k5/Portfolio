from aiogram import Dispatcher, types, Bot, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from products import GenerateProductList
from aiogram.types import ContentType
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
import mysql.connector
import sys
import os
import pandas

with open("Settings/tokens.txt") as tokens:
    content = tokens.readlines()
    token = content[0].strip()[11:]
    payment_token = content[1].strip()[15:]

storage = MemoryStorage()
bot = Bot(token=token)
dp = Dispatcher(bot, storage=storage)

catalogue = []
catalogue_products = {}


def dest_or_no():
    with open("Settings/dest.txt") as dest_file:
        if dest_file.read().strip() == "True":
            dest = True
        else:
            dest = False
    return dest


def chat_id_address():
    with open("Settings/chat_id.txt") as chat_id_file:
        chat_id_address = chat_id_file.read()
        return int(chat_id_address)


def refresh_prod():
    catalogue.clear()
    catalogue_products.clear()
    data = pandas.read_csv("Settings/data.csv", index_col=0, )
    cats = data["Категории"].values
    for cat in cats:
        if cat not in catalogue:
            catalogue.append(cat)
            catalogue_products[cat] = []
            prods = data[data["Категории"] == cat].values
            for prod in prods:
                catalogue_products[cat].append(list(prod))
        else:
            prods = data[data["Категории"] == cat].values
            for prod in prods:
                if list(prod) not in catalogue_products[cat]:
                    catalogue_products[cat].append(list(prod))
    catalog = InlineKeyboardMarkup(row_width=2)
    for cat in catalogue:
        catalog.add(InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}"))
    catalog.add(InlineKeyboardButton(text="Корзина", callback_data="Cart"))
    catalog.add(InlineKeyboardButton(text="Отзывы", callback_data="Review"))
    return catalog


refresh_prod()


def generate_cart_keyboard(prod_list):
    cart_buy = InlineKeyboardMarkup(row_width=2)
    for prod in prod_list:
        cart_buy.add(InlineKeyboardButton(text=prod[1], callback_data=f"DelCart_{prod[1]}"))
    cart_buy.add(InlineKeyboardButton(text="Оформить заказ", callback_data="Cart_Order"),
                 InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))
    return cart_buy


def generate_prod_keyboard(cat):
    prod_dict = {}
    prods = catalogue_products[cat]
    for prod in prods:
        prod_dict[prod[0]] = [prod[2], prod[3], prod[4]]
    keyboard = GenerateProductList(prod_dict)
    keyboard.make_keyboard()
    return keyboard


def generate_list_prod():
    list_prod = {}

    for cat in catalogue:
        list_prod[cat] = ""

    for cat in list_prod.items():
        key = cat[0]
        list_prod[key] = generate_prod_keyboard(key)
    return list_prod


order_again = InlineKeyboardMarkup(row_width=1)
order_again.add(InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))

stars = InlineKeyboardMarkup(row_width=3)
stars.add(InlineKeyboardButton(text="1", callback_data="Star_1"),
          InlineKeyboardButton(text="2", callback_data="Star_2"),
          InlineKeyboardButton(text="3", callback_data="Star_3"),
          InlineKeyboardButton(text="4🌟", callback_data="Star_4"),
          InlineKeyboardButton(text="5🌟🌟", callback_data="Star_5"))
stars.add(InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))

write_review = InlineKeyboardMarkup(row_width=2)
write_review.add(InlineKeyboardButton(text="Да", callback_data="Review_Write"),
                 InlineKeyboardButton(text="В меню", callback_data="Back"))

buy = InlineKeyboardMarkup(row_width=1)
buy.add(InlineKeyboardButton(text="Оплата", callback_data="Buy"))
buy.add(InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))

own_or_dest = InlineKeyboardMarkup(row_width=2)
own_or_dest.add(InlineKeyboardButton(text="Самовывоз", callback_data="Own"),
                InlineKeyboardButton("Доставка", callback_data="Dest"))
own_or_dest.add(InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))

confirm_selection = InlineKeyboardMarkup(row_width=2)
confirm_selection.add(InlineKeyboardButton(text="Купить сейчас", callback_data="ConfirmSelection"),
                      InlineKeyboardButton(text="Добавить в корзину", callback_data="Crt_Add"),
                      InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))

cart_or_menu = InlineKeyboardMarkup(row_width=2)
cart_or_menu.add(InlineKeyboardButton(text="Перейти к корзине", callback_data="Cart"),
                 InlineKeyboardButton(text="В меню", callback_data="Back"))

own_confirm = InlineKeyboardMarkup(row_width=2)
own_confirm.add(InlineKeyboardButton(text="Понял, продолжаем", callback_data="Own"),
                InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))

buy_cart = InlineKeyboardMarkup(row_width=2)
buy_cart.add(InlineKeyboardButton(text="Оплата", callback_data="BuyCart"),
             InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))

user_sessions = {}
global total
global total_dest
total = 0
total_dest = 0


class UserAddress(StatesGroup):
    address = State()
    destination = State()


class Review(StatesGroup):
    text = State()


@dp.message_handler(commands=['start', 'order'])
async def prods(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["info"].clear()
    else:
        user_sessions[user_id] = {"info": [],
                                  "cart": []}
    user_sessions[user_id]["dest"] = False
    user_sessions[user_id]["payment_able"] = False
    await bot.send_photo(message.chat.id, caption="Здравствуйте, "
                                                  "этот бот предназначен для заказов товаров, "
                                                  "снизу представлены каталоги товаров",
                         photo=open("Photos/Start_photo.png", "rb"),
                         reply_markup=refresh_prod())


@dp.callback_query_handler(text="Back")
async def back(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["info"].clear()
    else:
        user_sessions[user_id] = {"info": [],
                                  "cart": []}
    user_sessions[user_id]["dest"] = False
    user_sessions[user_id]["payment_able"] = False
    await bot.send_photo(call.message.chat.id, caption="Здравствуйте, "
                                                       "этот бот предназначен для заказов товаров, "
                                                       "снизу представлены каталоги товаров",
                         photo=open("Photos/Start_photo.png", "rb"),
                         reply_markup=refresh_prod())


@dp.callback_query_handler(text_contains="DelCart")
async def bought(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    for prod in user_sessions[user_id]["cart"]:
        if prod[1] == call.data.split('_')[1]:
            del user_sessions[user_id]["cart"][user_sessions[user_id]["cart"].index(prod)]
    if len(user_sessions[user_id]["cart"]) != 0:
        msg = "Вот ваша корзина(При нажатии на товар он удалится из корзины):\n\n"
        for prod in user_sessions[user_id]['cart']:
            msg += f"{prod[1]} - {str(prod[2])}₽\n"
        await bot.send_message(call.message.chat.id,
                               text=msg,
                               reply_markup=generate_cart_keyboard(user_sessions[user_id]["cart"]))
    else:
        await bot.send_message(call.message.chat.id,
                               "Упс, кажется ваша корзина пуста!",
                               reply_markup=refresh_prod())


@dp.callback_query_handler(text="BuyCart")
async def bought(call: types.CallbackQuery):
    global total
    global total_dest
    user_id = call.from_user.id
    price = types.LabeledPrice(label="Оплата заказа", amount=int(total) * 100)
    await bot.send_invoice(chat_id=call.message.chat.id,
                           title="Оплата заказа",
                           description="Оплата заказа",
                           provider_token=payment_token,
                           currency="rub",
                           prices=[price],
                           start_parameter="buy_product",
                           payload="Оплачивание заказа")
    user_sessions[user_id]["payment_able"] = True


@dp.callback_query_handler(text="Buy")
async def bought(call: types.CallbackQuery):
    user_id = call.from_user.id
    price = types.LabeledPrice(label="Оплата товара", amount=int(user_sessions[user_id]["info"][2]) * 100)
    await bot.send_invoice(chat_id=call.message.chat.id,
                           title="Оплата товара",
                           description="Оплата выбранного товара",
                           provider_token=payment_token,
                           currency="rub",
                           prices=[price],
                           start_parameter="buy_product",
                           payload="Оплачивание товара")
    user_sessions[user_id]["payment_able"] = True


@dp.pre_checkout_query_handler()
async def pre_checkout_query(pre_q: types.PreCheckoutQuery):
    user_id = pre_q.from_user.id
    if user_sessions[user_id]["payment_able"] == True:
        await bot.answer_pre_checkout_query(pre_q.id, ok=True)
        user_sessions[user_id]["payment_able"] = False
    else:
        pass


@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    global total
    global total_dest
    if int(total) == 0 and int(total_dest) == 0:
        if user_sessions[user_id]["dest"] == True:
            await bot.send_photo(message.chat.id, caption=f"Ваш заказ упакован и отправлен нашей команде!\n\n"
                                                          f"Каталог: {user_sessions[user_id]['info'][0]}\n"
                                                          f"Товар: {user_sessions[user_id]['info'][1]}\n"
                                                          f"Цена: {user_sessions[user_id]['info'][2]}₽\n"
                                                          f"Адрес: {user_sessions[user_id]['info'][4]}\n\n"
                                                          f"Ваш заказ придет в соответствии с очередью и "
                                                          f"работой нашей команды, ",
                                 photo=open("Photos/Box.png", 'rb'), reply_markup=order_again)

            await bot.send_photo(chat_id_address(), caption=f"НОВЫЙ ЗАКАЗ!!!\n\n"
                                                            f"Каталог: {user_sessions[user_id]['info'][0]}\n"
                                                            f"Товар: {user_sessions[user_id]['info'][1]}\n"
                                                            f"Цена: {user_sessions[user_id]['info'][2]}₽\n"
                                                            f"Адрес: {user_sessions[user_id]['info'][4]}\n\n"
                                                            f"Доставка: включена", photo=open("Photos/Box.png", "rb"))
        else:
            await bot.send_photo(message.chat.id, caption=f"Ваш заказ упакован и отправлен нашей команде!\n\n"
                                                          f"Каталог: {user_sessions[user_id]['info'][0]}\n"
                                                          f"Товар: {user_sessions[user_id]['info'][1]}\n"
                                                          f"Цена: {user_sessions[user_id]['info'][2]}₽\n\n"
                                                          f"Ваш заказ придет в соответствии с очередью и "
                                                          f"работой нашей команды, ",
                                 photo=open("Photos/Box.png", 'rb'), reply_markup=order_again)

            await bot.send_photo(chat_id_address(), caption=f"НОВЫЙ ЗАКАЗ!!!\n\n"
                                                            f"Каталог: {user_sessions[user_id]['info'][0]}\n"
                                                            f"Товар: {user_sessions[user_id]['info'][1]}\n"
                                                            f"Цена: {user_sessions[user_id]['info'][2]}₽\n\n"
                                                            f"Доставка: не включена",
                                 photo=open("Photos/Box.png", "rb"))
    else:
        msg_client = "Ваш заказ упакован и отправлен нашей команде!\n\nСписок товаров:\n\n"
        msg_author = "НОВЫЙ ЗАКАЗ!!!\n\nСписок товаров:\n\n"
        for prod in user_sessions[user_id]["cart"]:
            msg_client += f"{prod[1]}\n"
            msg_author += f"{prod[1]}\n"
        if user_sessions[user_id]["dest"] == True:
            msg_author += f"\nАдрес: {user_sessions[user_id]['info'][0]}"
            msg_client += f"\nАдрес: {user_sessions[user_id]['info'][0]}"
            await bot.send_photo(message.chat.id, caption=f"{msg_client}\n\n"
                                                          f"Ваш заказ придет в соответствии с очередью и "
                                                          f"работой нашей команды, ",
                                 photo=open("Photos/Box.png", 'rb'), reply_markup=order_again)

            await bot.send_photo(chat_id_address(), caption=f"{msg_author}\n\n"
                                                            f"Доставка: включена",
                                 photo=open("Photos/Box.png", "rb"))
        else:
            await bot.send_photo(message.chat.id, caption=f"{msg_client}\n\n"
                                                          f"Ваш заказ придет в соответствии с очередью и "
                                                          f"работой нашей команды, ",
                                 photo=open("Photos/Box.png", 'rb'), reply_markup=order_again)

            await bot.send_photo(chat_id_address(), caption=f"{msg_author}\n\n"
                                                            f"Доставка: не включена",
                                 photo=open("Photos/Box.png", "rb"))
        total = 0
        total_dest = 0
        user_sessions[user_id]["cart"].clear()
        user_sessions[user_id]["payment_able"] = False


@dp.callback_query_handler(text="Own")
async def own(call: types.CallbackQuery):
    global total
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    if total != 0:
        await bot.send_photo(call.message.chat.id, caption=f"Вы готовы оплатить ваш заказ за "
                                                           f"{total}₽?", reply_markup=buy_cart,
                             photo=open("Photos/Get_Ready_To_Pay.png", "rb"))
    else:
        await bot.send_photo(call.message.chat.id, caption=f"Вы готовы оплатить {user_sessions[user_id]['info'][1]} за "
                                                           f"{user_sessions[user_id]['info'][2]}₽?", reply_markup=buy,
                             photo=open("Photos/Get_Ready_To_Pay.png", "rb"))


@dp.callback_query_handler(text="Dest")
async def dest(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    await bot.send_photo(call.message.chat.id, caption="Напишите свой адрес, он будет перенаправлен команде",
                         photo=open("Photos/Address.png", "rb"))
    await UserAddress.address.set()


@dp.callback_query_handler(text_startswith=['cat_'])
async def catalog(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    await bot.send_photo(call.message.chat.id, caption=f"Каталог: {call.data.split('_')[1]}",
                         reply_markup=generate_list_prod()[call.data.split("_")[1]].keyboard,
                         photo=open("Photos/Catalogue.png", "rb"))


@dp.callback_query_handler(text_startswith=['Prod_'])
async def prod(call: types.CallbackQuery):
    global product
    global cat
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    product = call.data.split("_")[1]
    cat = call.message["caption"][9:]
    class_prod = generate_list_prod()[cat]
    for prod_pair in class_prod.products:
        if product in prod_pair:
            description = prod_pair[3]
    await bot.send_message(call.message.chat.id,
                           text=f"Описание и характеристики:\n\n{description}",
                           reply_markup=confirm_selection)


@dp.callback_query_handler(text="ConfirmSelection")
async def confirm_buying(call: types.CallbackQuery):
    global product
    global cat
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    if len(user_sessions[user_id]['info']) == 0:
        class_prod = generate_list_prod()[cat]
        for prod_pair in class_prod.products:
            if product in prod_pair:
                cost = prod_pair[1]
                cost_dest = prod_pair[2]
                break
        user_sessions[user_id]['info'].append(cat)
        user_sessions[user_id]['info'].append(product)
        user_sessions[user_id]['info'].append(cost)
        user_sessions[user_id]['info'].append(cost_dest)
    elif len(user_sessions[user_id]['info']) >= 4:
        user_sessions[user_id]['info'].pop()
    if dest_or_no():
        await bot.send_photo(call.message.chat.id, caption="Самовывоз или доставка?",
                             reply_markup=own_or_dest,
                             photo=open("Photos/Own_Or_Dest.png", "rb"))
    else:
        await bot.send_photo(call.message.chat.id, caption="Учтите что у магазина нет доставки, только самовывоз",
                             reply_markup=own_confirm,
                             photo=open("Photos/Own_Or_Dest.png", "rb"))


@dp.callback_query_handler(text="Crt_Add")
async def confirm_buying(call: types.CallbackQuery):
    global product
    global cat
    total = []
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    class_prod = generate_list_prod()[cat]
    for prod_pair in class_prod.products:
        if product in prod_pair:
            cost = prod_pair[1]
            cost_dest = prod_pair[2]
            break
    total.append(cat)
    total.append(product)
    total.append(cost)
    total.append(cost_dest)
    user_sessions[user_id]['cart'].append(total)
    await bot.send_message(call.message.chat.id, text="Товар добавлен в корзину!", reply_markup=cart_or_menu)


@dp.callback_query_handler(text="Cart_Order")
async def cart(call: types.CallbackQuery):
    user_id = call.from_user.id
    global total
    global total_dest
    user_sessions[user_id]["payment_able"] = False
    total = 0
    total_dest = 0
    for prod in user_sessions[user_id]['cart']:
        total += prod[2]
        total_dest += prod[3]
    if dest_or_no():
        await bot.send_photo(call.message.chat.id, caption="Самовывоз или доставка?",
                             reply_markup=own_or_dest,
                             photo=open("Photos/Own_Or_Dest.png", "rb"))
    else:
        await bot.send_photo(call.message.chat.id, caption="Учтите что у магазина нет доставки, только самовывоз",
                             reply_markup=own_confirm,
                             photo=open("Photos/Own_Or_Dest.png", "rb"))


@dp.callback_query_handler(text="Cart")
async def cart(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    msg = "Вот ваша корзина(При нажатии на товар он удалится из корзины):\n\n"
    if len(user_sessions[user_id]["cart"]) != 0:
        for prod in user_sessions[user_id]['cart']:
            msg += f"{prod[1]} - {str(prod[2])}₽\n"
        await bot.send_message(call.message.chat.id,
                               text=msg,
                               reply_markup=generate_cart_keyboard(user_sessions[user_id]["cart"]))
    else:
        await bot.send_message(call.message.chat.id,
                               "Упс, кажется ваша корзина пуста!",
                               reply_markup=refresh_prod())


@dp.callback_query_handler(text="Review_Write")
async def write_review_own(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    await bot.send_photo(call.message.chat.id, caption="Напишите ваш отзыв, он будет добавлен к верху всех отзывов",
                         photo=open("Photos/Review_Write.png", "rb"))
    await Review.text.set()


@dp.callback_query_handler(text="Review")
async def reviews(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    with open("Reviews.txt", encoding='utf-8') as review:
        content = review.readlines()
        content.reverse()
    total_reviews = 0
    msg = ""
    for review in content:
        total_reviews += 1
        msg += f"{review.strip()}\n"
        if total_reviews == 5:
            break
    await bot.send_photo(call.message.chat.id, caption=msg, photo=open("Photos/Review_Show.png", "rb"))
    await bot.send_message(call.message.chat.id, text="Это только последние 5 отзывов людей этого магазина\n"
                                                      "Хотите написать свой отзыв?",
                           reply_markup=write_review)


@dp.callback_query_handler(text_startswith=['Star_'])
async def process_star_click(call: types.CallbackQuery):
    global review
    user_id = call.from_user.id
    user_sessions[user_id]["payment_able"] = False
    star_number = int(call.data.split('_')[1])
    if star_number == 5:
        word = "звезд"
    elif star_number == 1:
        word = "звезда"
    else:
        word = "звезды"
    with open("Reviews.txt", mode="a", encoding="utf-8") as reviews:
        reviews.write(f"{call.from_user.first_name}: {star_number} {word}, {review}\n")
    await bot.send_message(call.message.chat.id, "Ваш отзыв был добавлен к списку отзывов!", reply_markup=order_again)


@dp.message_handler(state=Review.text)
async def star(message: types.Message, state: FSMContext):
    global review
    user_id = message.from_user.id
    user_sessions[user_id]["payment_able"] = False
    review = message.text
    await bot.send_message(message.chat.id, "Сколько звезд вы хотите поставить данному магазину?", reply_markup=stars)
    await state.finish()


@dp.message_handler(state=UserAddress.address)
async def get_address_and_pay(message: types.Message, state: FSMContext):
    global address
    global total
    global total_dest
    user_id = message.from_user.id
    user_sessions[user_id]["payment_able"] = False
    address = message.text
    user_sessions[user_id]['info'].append(address)
    if total != 0 and total_dest != 0:
        total += total_dest
        await bot.send_photo(message.chat.id,
                             caption=f"Вы готовы оплатить ваш заказ за "
                                     f"{total}₽?(С учетом доставки + "
                                     f"{total_dest}₽)\n"
                                     f"Товар придет на указанный адрес",
                             reply_markup=buy_cart,
                             photo=open("Photos/Get_Ready_To_Pay.png", "rb"))
    else:
        await bot.send_photo(message.chat.id,
                             caption=f"Вы готовы оплатить {user_sessions[user_id]['info'][1]} за "
                                     f"{user_sessions[user_id]['info'][2]}₽?(С учетом доставки + "
                                     f"{user_sessions[user_id]['info'][3]}₽)\n"
                                     f"Товар придет в место указанное в вашем адресе",
                             reply_markup=buy,
                             photo=open("Photos/Get_Ready_To_Pay.png", "rb"))
    user_sessions[user_id]["dest"] = True
    await state.finish()


executor.start_polling(dp, skip_updates=False)
