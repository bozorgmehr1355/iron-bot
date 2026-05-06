from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from services.iron import get_iron_62, get_fe65
from services.billet import get_billet_price
from services.forex import get_usd_free
from datetime import datetime

user_data = {}

async def profit_start(update, context):
    user_id = update.message.from_user.id
    user_data[user_id] = {}
    keyboard = [
        [InlineKeyboardButton("Iron Ore 62%", callback_data="prod_1"),
         InlineKeyboardButton("Fe 65%", callback_data="prod_2")],
        [InlineKeyboardButton("Pellet", callback_data="prod_3"),
         InlineKeyboardButton("Billet", callback_data="prod_4")],
        [InlineKeyboardButton("Custom price", callback_data="prod_5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Step 1/7: Select product:", reply_markup=reply_markup)

async def profit_product_select(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {}

    products = {
        "prod_1": ("Iron Ore 62%", get_iron_62),
        "prod_2": ("Fe 65% Concentrate", get_fe65),
        "prod_3": ("Pellet", lambda: round(get_iron_62() + 15, 2)),
        "prod_4": ("Billet", get_billet_price),
        "prod_5": ("Custom", None)
    }

    name, fn = products[query.data]
    user_data[user_id]["product"] = name
    user_data[user_id]["price_fn"] = fn

    await query.edit_message_text("Fetching market data...")

    if fn:
        price = fn()
        user_data[user_id]["suggested_fob"] = price
        await query.edit_message_text(
            "Product: " + name + "\n"
            "Current market price: $" + str(price) + "/ton\n\n"
            "Step 2/7: Purchase price in Iran ($/ton)?\n"
            "Example: 95"
        )
    else:
        await query.edit_message_text(
            "Step 2/7: Purchase price in Iran ($/ton)?\n"
            "Example: 95"
        )

async def profit_step(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id not in user_data or "product" not in user_data[user_id]:
        return

    data = user_data[user_id]

    if "purchase" not in data:
        try:
            data["purchase"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        fn = data.get("price_fn")
        if fn:
            price = data.get("suggested_fob", fn())
            await update.message.reply_text(
                "Step 3/7: FOB selling price ($/ton)?\n"
                "Current market: $" + str(price) + "/ton\n"
                "Send 0 to use market price or enter custom:"
            )
        else:
            await update.message.reply_text("Step 3/7: FOB selling price ($/ton)?")

    elif "fob" not in data:
        try:
            val = float(text)
            data["fob"] = data["suggested_fob"] if val == 0 and "suggested_fob" in data else val
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Fetching exchange rate...")
        rate = get_usd_free()
        if rate:
            clean = rate.replace(",", "")
            data["suggested_rate"] = clean
            await update.message.reply_text(
                "Step 4/7: Exchange rate (Rials/USD)?\n"
                "Current rate: " + rate + "\n"
                "Send 0 to use current rate or enter custom:"
            )
        else:
            await update.message.reply_text("Step 4/7: Exchange rate (Rials/USD)?\nExample: 1798800")

    elif "rate" not in data:
        try:
            val = float(text)
            data["rate"] = float(data["suggested_rate"]) if val == 0 and "suggested_rate" in data else val
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 5/7: Tonnage (tons)?\nExample: 5000")

    elif "tonnage" not in data:

try:
            data["tonnage"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 6/7: Freight cost ($/ton)?\nExample: 18")

    elif "freight" not in data:
        try:
            data["freight"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 7/7: Port and loading cost ($/ton)?\nExample: 4")

    elif "port" not in data:
        try:
            data["port"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")

