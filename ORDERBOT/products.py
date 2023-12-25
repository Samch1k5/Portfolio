from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class GenerateProductList:

    def __init__(self, prod_dict):
        self.products = []
        self.keyboard = 0
        for item in prod_dict.items():
            name = item[0]
            cost = item[1][0]
            cost_dest = item[1][1]
            description = item[1][2]
            self.products.append((name, cost, cost_dest, description))

    def make_keyboard(self):
        self.keyboard = InlineKeyboardMarkup(row_width=3)
        for prod in self.products:
            self.keyboard.add(InlineKeyboardButton(text=f"{prod[0]}: {prod[1]}₽", callback_data=f"Prod_{prod[0]}"))
        self.keyboard.add(InlineKeyboardButton(text="Назад", callback_data="Back"))
