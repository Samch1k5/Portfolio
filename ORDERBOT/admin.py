from aiogram import Dispatcher, types, Bot, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from datetime import datetime
import pandas
import sys
import os
import mysql.connector

with open("Settings/tokens.txt", encoding="utf-8-sig") as tokens:
    content = tokens.readlines()
    passw = content[3].strip()[12:]
    token = content[2].strip()[13:]

storage = MemoryStorage()
bot = Bot(token)
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


def refresh_prod():
    catalogue.clear()
    catalogue_products.clear()
    data = pandas.read_csv("Settings/data.csv", index_col=0, encoding="utf-8-sig")
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


refresh_prod()


def add_new_catalog(list_of_catalog):
    print(list_of_catalog)
    cat = list_of_catalog[0]
    description = list_of_catalog[2]
    dest_cost = list_of_catalog[-1]
    list_of_catalog[2] = list_of_catalog[3]
    list_of_catalog[-1] = description
    list_of_catalog[3] = dest_cost
    list_of_catalog[0] = list_of_catalog[1]
    list_of_catalog[1] = cat
    print(list_of_catalog)
    data = pandas.read_csv("Settings/data.csv", index_col=0)
    data.loc[len(data) + 1] = list_of_catalog
    data.to_csv("Settings/data.csv", encoding="utf-8-sig")


def add_products_to_catalog(ready_list):
    data = pandas.read_csv("Settings/data.csv", index_col=0)
    data.loc[len(data)] = ready_list
    data.to_csv("Settings/data.csv", encoding="utf-8-sig")


admin_keyboard = InlineKeyboardMarkup(row_width=2)
admin_keyboard.add(InlineKeyboardButton(text="Настройка каталогов", callback_data="Catalogue"))
admin_keyboard.add(InlineKeyboardButton(text="Поставить себя как адресат заказов", callback_data="Adressat"))
admin_keyboard.add(InlineKeyboardButton(text="Включить/выключить доставку", callback_data="Dest_Control"))

catalogue_decision = InlineKeyboardMarkup(row_width=2)
catalogue_decision.add(InlineKeyboardButton(text="Да", callback_data="Cat_Yes"),
                       InlineKeyboardButton(text="Нет", callback_data="Back"))

add_catalogue = InlineKeyboardMarkup(row_width=2)
add_catalogue.add(InlineKeyboardButton(text="Добавить новый товар", callback_data="Add_Prod"),
                  InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))


delete_cat_decision = InlineKeyboardMarkup(row_width=2)
delete_cat_decision.add(InlineKeyboardButton(text="Да", callback_data="Delete_Cat_Conf"),
                        InlineKeyboardButton(text="Нет", callback_data="Cat_Yes"))

delete_prod_decision = InlineKeyboardMarkup(row_width=2)
delete_prod_decision.add(InlineKeyboardButton(text="Да", callback_data="Delete_Prod_Conf"),
                         InlineKeyboardButton(text="Нет", callback_data="Cat_Yes"))


class Info(StatesGroup):
    password = State()
    catalogue_name = State()
    catalogue_prod = State()
    catalogue_cost = State()
    catalogue_cost_dest = State()
    catalogue_description = State()
    catalogue_cost_without_dest = State()
    name = State()
    cost = State()
    description = State()
    cost_dest = State()
    name_cat = State()
    list_of_prod = []
    edit_prod = []


def bot_chat():
    @dp.message_handler(commands=['start', 'admin'])
    async def bot_run(message: types.Message):
        await bot.send_message(message.chat.id, "Перед началом работы вам нужно ввести пароль")
        await Info.password.set()

    @dp.message_handler(state=Info.password)
    async def password(message: types.Message, state: FSMContext):
        if message.text == passw:
            await bot.send_photo(message.chat.id,
                                 caption="Добро пожаловать в панель управления вашим продажным ботом!\n"
                                         "Режим администрирования включен",
                                 photo=open("Photos/Admin_Open.png", "rb"), reply_markup=admin_keyboard)
            await state.finish()
        else:
            await bot.send_message(message.chat.id, "Неправильный пароль!")
            await state.finish()

    @dp.callback_query_handler(text_contains="Adressat")
    async def new_addr(call: types.CallbackQuery):
        with open("Settings/chat_id.txt", "w") as chat_id_addr:
            chat_id_addr.write(str(call.message.chat.id))
        await bot.send_message(call.message.chat.id, "Готово!\nТеперь все сообщения о заказах будут приходить вам",
                               reply_markup=admin_keyboard)

    @dp.callback_query_handler(text_contains="Catalogue")
    async def cat(call: types.CallbackQuery):
        msg = "На данный момент вы имеете вот такие каталоги:\n\n"
        for cat in catalogue:
            msg += f"{cat}\n"
        msg += "\nХотели бы изменить/добавить каталоги?"
        await bot.send_message(call.message.chat.id, msg, reply_markup=catalogue_decision)

    @dp.callback_query_handler(text_contains="Back")
    async def back(call: types.CallbackQuery):
        await bot.send_photo(call.message.chat.id,
                             caption="Добро пожаловать в панель управления вашим продажным ботом!\n",
                             photo=open("Photos/Admin_Open.png", "rb"), reply_markup=admin_keyboard)

    @dp.callback_query_handler(text_contains="Delete_Cat_Conf")
    async def confirm_cat_delete(call: types.CallbackQuery):
        cat = Info.list_of_prod[0]
        data = pandas.read_csv("Settings/data.csv", index_col=0)
        await bot.send_message(call.message.chat.id, "Хорошо, удаляю")
        i = data.index
        index = data["Категории"] == cat
        result = i[index]
        for ind in result:
            data = data.drop(labels=ind)
        data.to_csv("Settings/data.csv", encoding="utf-8-sig")
        await bot.send_message(call.message.chat.id, "Готово!", reply_markup=admin_keyboard)
        refresh_prod()
        Info.list_of_prod.clear()

    @dp.callback_query_handler(text="Dest_Control")
    async def on_off_dest(call: types.CallbackQuery):
        if dest_or_no():
            content = "False"
            with open("Settings/dest.txt", mode="w") as dest_file:
                dest_file.write(content)
            await bot.send_message(call.message.chat.id, "Доставка: выключена")
        else:
            content = "True"
            with open("Settings/dest.txt", mode="w") as dest_file:
                dest_file.write(content)
            await bot.send_message(call.message.chat.id, "Доставка: включена\n\nНе забудьте "
                                                         "изменить наценку за доставку у товаров с 0 до нужной суммы")

    @dp.callback_query_handler(text_contains="Cat_Yes")
    async def cat_yes(call: types.CallbackQuery):
        catalogue_keyboard = InlineKeyboardMarkup(row_width=1)
        for cat in catalogue:
            catalogue_keyboard.add(InlineKeyboardButton(text=cat, callback_data=f"cat_edit_{cat}"))
        catalogue_keyboard.add(InlineKeyboardButton(text="Добавить новый каталог", callback_data="Add_Cat"))
        catalogue_keyboard.add(InlineKeyboardButton(text="Вернуться в меню", callback_data="Back"))
        await bot.send_photo(call.message.chat.id,
                             caption="Вы можете изменить/добавить каталоги\n",
                             photo=open("Photos/Admin_Open.png", "rb"), reply_markup=catalogue_keyboard)

    @dp.callback_query_handler(text_contains="Edit_Cat_Name")
    async def edit_catalogue_name(call: types.CallbackQuery):
        await bot.send_message(call.message.chat.id, "Напишите новое название каталога")
        await Info.name_cat.set()

    @dp.callback_query_handler(text_contains="Delete_Cat")
    async def delete_catologue(call: types.CallbackQuery):
        await bot.send_message(call.message.chat.id, "Вы уверены что хотите удалить данный каталог\n"
                                                     "!!!Каталог будет удален без возможности возвращения!!!",
                               reply_markup=delete_cat_decision)

    @dp.message_handler(state=Info.name_cat)
    async def name_of_catalogue(message: types.Message, state: FSMContext):  
        cat = Info.list_of_prod[0]
        data = pandas.read_csv("Settings/data.csv", index_col=0)
        i = data.index
        index = data["Категории"] == cat
        result = i[index]
        for ind in result:
            data.at[ind, "Категории"] = message.text
        data.to_csv("Settings/data.csv", encoding="utf-8-sig")
        await bot.send_message(message.chat.id, "Готово!", reply_markup=admin_keyboard)
        await state.finish()
        refresh_prod()
        Info.list_of_prod.clear()

    @dp.callback_query_handler(text_contains="cat_edit_")
    async def edit_cat(call: types.CallbackQuery):
        cat = call.data.split("_")[2]
        prods = InlineKeyboardMarkup(row_width=1)
        for prod in catalogue_products[cat]:
            prods.add(InlineKeyboardButton(text=prod[0], callback_data=f"prod_edit_{prod[0]}"))
        Info.list_of_prod.clear()
        Info.list_of_prod.append(cat)
        prods.add(InlineKeyboardButton(text="Добавить новый товар", callback_data=f"Add_Prod"))
        prods.add(InlineKeyboardButton(text="Изменить название каталога", callback_data=f"Edit_Cat_Name"))
        prods.add(InlineKeyboardButton(text="!!!УДАЛИТЬ КАТАЛОГ!!!", callback_data="Delete_Cat"))
        prods.add(InlineKeyboardButton(text="Вернуться в каталоги", callback_data="Cat_Yes"))
        await bot.send_photo(call.message.chat.id,
                             caption="Вы можете удалить/добавить товары(после нажатия на товар он сразу удалится)\n",
                             photo=open("Photos/Admin_Open.png", "rb"),
                             reply_markup=prods)

    @dp.callback_query_handler(text_contains="Name")
    async def edit_cat_name(call: types.CallbackQuery):
        await bot.send_message(call.message.chat.id, "Напишите новое имя для данного продукта")
        await Info.name.set()

    @dp.message_handler(state=Info.name)
    async def edit_name(message: types.Message, state: FSMContext):
        cat = Info.edit_prod[1]
        name_prod = catalogue_products[Info.edit_prod[1]][Info.edit_prod[0]][0]
        data = pandas.read_csv("Settings/data.csv", index_col=0)
        for prod in data[data["Категории"] == cat].values:
            if name_prod in prod:
                i = data.index
                index = data["Товары"] == prod[0]
                result = i[index]
                data.at[result[0], "Товары"] = message.text
                data.to_csv("Settings/data.csv", encoding="utf-8-sig")
                break
        await bot.send_message(message.chat.id, "Готово!", reply_markup=admin_keyboard)
        await state.finish()
        refresh_prod()
        Info.edit_prod.clear()

    @dp.callback_query_handler(text_contains="Dest_Costing")
    async def edit_cat_dest(call: types.CallbackQuery):
        await bot.send_message(call.message.chat.id, "Напишите наценку для данного продукта(по доставке)")
        await Info.cost_dest.set()

    @dp.message_handler(state=Info.cost_dest)
    async def edit_dest(message: types.Message, state: FSMContext):
        cat = Info.edit_prod[1]
        name_prod = catalogue_products[Info.edit_prod[1]][Info.edit_prod[0]][0]
        data = pandas.read_csv("Settings/data.csv", index_col=0)
        for prod in data[data["Категории"] == cat].values:
            if name_prod in prod:
                i = data.index
                index = data["Товары"] == prod[0]
                result = i[index]
                try:
                    data.at[result[0], "Наценка за доставку"] = int(message.text)
                    data.to_csv("Settings/data.csv", encoding="utf-8-sig")
                    break
                except Exception:
                    await bot.send_message(message.chat.id, 'Произошла ошибка, возможно вы указали не число а текст')
        await bot.send_message(message.chat.id, "Готово!", reply_markup=admin_keyboard)
        await state.finish()
        refresh_prod()
        Info.edit_prod.clear()

    @dp.callback_query_handler(text_contains="Cost")
    async def edit_cat_cost(call: types.CallbackQuery):
        await bot.send_message(call.message.chat.id, "Напишите цену для данного продукта")
        await Info.cost.set()

    @dp.message_handler(state=Info.cost)
    async def edit_cost(message: types.Message, state: FSMContext):
        cat = Info.edit_prod[1]
        name_prod = catalogue_products[Info.edit_prod[1]][Info.edit_prod[0]][0]
        data = pandas.read_csv("Settings/data.csv", index_col=0)
        for prod in data[data["Категории"] == cat].values:
            if name_prod in prod:
                i = data.index
                index = data["Товары"] == prod[0]
                result = i[index]
                try:
                    data.at[result[0], "Цена"] = int(message.text)
                    data.to_csv("Settings/data.csv", encoding="utf-8-sig")
                    break
                except Exception:
                    await bot.send_message(message.chat.id, 'Произошла ошибка, возможно вы указали не число а текст')
        await bot.send_message(message.chat.id, "Готово!", reply_markup=admin_keyboard)
        await state.finish()
        refresh_prod()
        Info.edit_prod.clear()

    @dp.callback_query_handler(text_contains="Description")
    async def edit_cat_cost(call: types.CallbackQuery):
        await bot.send_message(call.message.chat.id, "Напишите новое описание для данного товара")
        await Info.description.set()

    @dp.message_handler(state=Info.description)
    async def edit_cost(message: types.Message, state: FSMContext):   
        cat = Info.edit_prod[1]
        name_prod = catalogue_products[Info.edit_prod[1]][Info.edit_prod[0]][0]
        data = pandas.read_csv("Settings/data.csv", index_col=0)
        for prod in data[data["Категории"] == cat].values:
            if name_prod in prod:
                i = data.index
                index = data["Товары"] == prod[0]
                result = i[index]
                try:
                    data.at[result[0], "Описание"] = str(message.text)
                    data.to_csv("Settings/data.csv", encoding="utf-8-sig")
                    break
                except Exception:
                    await bot.send_message(message.chat.id, 'Произошла ошибка')
        await bot.send_message(message.chat.id, "Готово!", reply_markup=admin_keyboard)
        await state.finish()
        refresh_prod()
        Info.edit_prod.clear()

    @dp.callback_query_handler(text_contains="prod_edit_")
    async def edit_prod(call: types.CallbackQuery):
        Info.edit_prod.clear()
        prod = call.data.split("_")[2]
        cat = ""
        prod_ind = ""
        for key in catalogue_products:
            for product in catalogue_products[key]:
                if prod in product:
                    prod_ind = catalogue_products[key].index(product)
                    cat = key
        if cat != "":
            if dest_or_no():
                msg = (f"Имя: {catalogue_products[cat][prod_ind][0]}\n"
                       f"Цена: {catalogue_products[cat][prod_ind][2]}\n"
                       f"Наценка за доставку: {catalogue_products[cat][prod_ind][3]}\n\n"
                       f"Описание: {catalogue_products[cat][prod_ind][4]}")
                edit_params = InlineKeyboardMarkup(row_width=2)
                edit_params.add(InlineKeyboardButton(text="Имя", callback_data="Name"),
                                InlineKeyboardButton(text="Цена", callback_data="Cost"))
                edit_params.add(InlineKeyboardButton(text="Наценка за доставку", callback_data="Dest_Costing"),
                                InlineKeyboardButton(text="Описание", callback_data="Description"))
                edit_params.add(InlineKeyboardButton(text="!!!Удалить товар!!!", callback_data="Delete_Prod"))
                edit_params.add(InlineKeyboardButton(text="Вернуться в каталоги", callback_data="Cat_Yes"))
            else:
                msg = (f"Имя: {catalogue_products[cat][prod_ind][0]}\n"
                       f"Цена: {catalogue_products[cat][prod_ind][2]}\n\n"
                       f"Описание: {catalogue_products[cat][prod_ind][4]}")
                edit_params = InlineKeyboardMarkup(row_width=2)
                edit_params.add(InlineKeyboardButton(text="Имя", callback_data="Name"),
                                InlineKeyboardButton(text="Цена", callback_data="Cost"))
                edit_params.add(InlineKeyboardButton(text="Описание", callback_data="Description"))
                edit_params.add(InlineKeyboardButton(text="!!!Удалить товар!!!", callback_data="Delete_Prod"))
                edit_params.add(InlineKeyboardButton(text="Вернуться в каталоги", callback_data="Cat_Yes"))

            await bot.send_message(call.message.chat.id, f"На данный момент у этого товара следующие данные:\n\n{msg}"
                                                         f"\n\nЧто вы хотели изменить?", reply_markup=edit_params)
            Info.edit_prod.append(prod_ind)
            Info.edit_prod.append(cat)

    @dp.callback_query_handler(text_contains="Delete_Prod_Conf")
    async def delete_prod_conf(call: types.CallbackQuery):
        prod = catalogue_products[Info.edit_prod[1]][Info.edit_prod[0]][0]
        data = pandas.read_csv("Settings/data.csv", index_col=0)
        await bot.send_message(call.message.chat.id, "Хорошо, удаляю")
        i = data.index
        index = data["Товары"] == prod
        result = i[index]
        for ind in result:
            data = data.drop(labels=ind)
        data.to_csv("Settings/data.csv", encoding="utf-8-sig")
        await bot.send_message(call.message.chat.id, "Готово!", reply_markup=admin_keyboard)
        refresh_prod()
        Info.edit_prod.clear()

    @dp.callback_query_handler(text_contains="Delete_Prod")
    async def delete_prod(call: types.CallbackQuery):
        await bot.send_message(call.message.chat.id, "Вы уверены что хотите удалить данный товар?\n"
                                                     "!!!Товар будет удален без возможности восстановления!!!",
                               reply_markup=delete_prod_decision)

    @dp.callback_query_handler(text_contains="Add_Cat")
    async def new_cat(call: types.CallbackQuery):
        await bot.send_photo(call.message.chat.id,
                             caption="Напишите название каталога, которое вы хотите добавить",
                             photo=open("Photos/Admin_Open.png", "rb"))
        Info.list_of_prod.clear()
        await Info.catalogue_name.set()

    @dp.message_handler(state=Info.catalogue_name)
    async def add_cat(message: types.Message, state: FSMContext):
        await bot.send_photo(message.chat.id,
                             caption="Отлично, теперь нужно добавить хотябы один товар в этот каталог, "
                                     "если вы передумали "
                                     "то вернитесь в меню, каталог в этом случае не будет добавлен",
                             photo=open("Photos/Admin_Open.png", "rb"), reply_markup=add_catalogue)
        Info.list_of_prod.append(message.text)
        await state.finish()

    @dp.callback_query_handler(text_contains="Add_Prod")
    async def add_cat(call: types.CallbackQuery):
        await bot.send_photo(call.message.chat.id,
                             caption="Как будет называться товар?",
                             photo=open("Photos/Admin_Open.png", "rb"))
        await Info.catalogue_prod.set()

    @dp.message_handler(state=Info.catalogue_prod)
    async def add_cat(message: types.Message):
        await bot.send_photo(message.chat.id,
                             caption="Опишите товар, характеристики например",
                             photo=open("Photos/Admin_Open.png", "rb"))
        Info.list_of_prod.append(message.text)
        await Info.catalogue_description.set()

    @dp.message_handler(state=Info.catalogue_description)
    async def add_cat(message: types.Message):
        await bot.send_photo(message.chat.id,
                             caption="Сколько он будет стоить?",
                             photo=open("Photos/Admin_Open.png", "rb"))
        Info.list_of_prod.append(message.text)
        if dest_or_no():
            await Info.catalogue_cost.set()
        else:
            await Info.catalogue_cost_without_dest.set()

    @dp.message_handler(state=Info.catalogue_cost_without_dest)
    async def add_cat(message: types.Message, state: FSMContext):
        try:
            Info.list_of_prod.append(int(message.text))
            Info.list_of_prod.append("0")
            await bot.send_photo(message.chat.id,
                                 caption="Отлично, товар добавлен!",
                                 photo=open("Photos/Admin_Open.png", "rb"), reply_markup=admin_keyboard)
            add_new_catalog(Info.list_of_prod)
            refresh_prod()
            Info.list_of_prod.clear()
            await state.finish()
        except Exception:
            await bot.send_message(message.chat.id, "Произошла ошибка, возможно вы указали не число а текст",
                                   reply_markup=admin_keyboard)
            Info.list_of_prod.clear()
            await state.finish()

    @dp.message_handler(state=Info.catalogue_cost)
    async def add_cat(message: types.Message, state: FSMContext):
        try:
            Info.list_of_prod.append(int(message.text))
            await bot.send_photo(message.chat.id,
                                 caption="Наценка за доставку?",
                                 photo=open("Photos/Admin_Open.png", "rb"))
            await Info.catalogue_cost_dest.set()
        except Exception:
            await bot.send_message(message.chat.id, "Произошла ошибка, возможно вы указали не число а текст",
                                   reply_markup=admin_keyboard)
            Info.list_of_prod.clear()
            await state.finish()

    @dp.message_handler(state=Info.catalogue_cost_dest)
    async def add_cat(message: types.Message, state: FSMContext):  
        try:
            await bot.send_photo(message.chat.id,
                                 caption="Отлично, товар добавлен!",
                                 photo=open("Photos/Admin_Open.png", "rb"), reply_markup=admin_keyboard)
            Info.list_of_prod.append(message.text)
            add_new_catalog(Info.list_of_prod)
            refresh_prod()
            Info.list_of_prod.clear()
            await state.finish()
        except Exception:
            await bot.send_message(message.chat.id, "Произошла ошибка, возможно вы указали не число а текст",
                                   reply_markup=admin_keyboard)
            Info.list_of_prod.clear()
            await state.finish()

    executor.start_polling(dp, skip_updates=False)


bot_chat()
