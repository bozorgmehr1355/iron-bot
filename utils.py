from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_back_button(step: str) -> InlineKeyboardMarkup:
    if step == "main":
        return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]])
    elif step == "price":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به انتخاب محصول", callback_data="back_to_product")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    elif step == "rate":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به قیمت خرید", callback_data="back_to_price")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    elif step == "tonnage":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به نرخ ارز", callback_data="back_to_rate")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    elif step == "freight":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به تناژ", callback_data="back_to_tonnage")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    elif step == "port":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به هزینه حمل", callback_data="back_to_freight")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    else:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]])
