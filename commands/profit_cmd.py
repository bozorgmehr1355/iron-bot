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
        except Exception:
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
            if val == 0 and "suggested_fob" in data:
                data["fob"] = data["suggested_fob"]
            else:
                data["fob"] = val
        except Exception:
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
            await update.message.reply_text(
                "Step 4/7: Exchange rate (Rials/USD)?\n"
                "Example: 1798800"
            )

    elif "rate" not in data:
        try:
            val = float(text)
            if val == 0 and "suggested_rate" in data:
                data["rate"] = float(data["suggested_rate"])
            else:
                data["rate"] = val
        except Exception:
            awai

t update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 5/7: Tonnage (tons)?\nExample: 5000")

    elif "tonnage" not in data:
        try:
            data["tonnage"] = float(text)
        except Exception:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 6/7: Freight cost ($/ton)?\nExample: 18")

    elif "freight" not in data:
        try:
            data["freight"] = float(text)
        except Exception:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 7/7: Port and loading cost ($/ton)?\nExample: 4")

    elif "port" not in data:
        try:
            data["port"] = float(text)
        except Exception:
            await update.message.reply_text("Please enter a valid number")
            return

        t = data["tonnage"]
        purchase = data["purchase"]
        fob = data["fob"]
        rate = data["rate"]
        freight = data["freight"]
        port = data["port"]

        revenue_usd = fob  t
        purchase_cost = purchase  t
        freight_cost = freight  t
        port_cost = port  t
        total_cost = purchase_cost + freight_cost + port_cost
        profit_usd = revenue_usd - total_cost
        profit_rials = profit_usd * rate

        now = datetime.now().strftime("%b %d, %Y - %H:%M")

        result = "Profit Calculation\n"
        result += now + "\n"
        result += "-------------------\n"
        result += "Product: " + data["product"] + "\n"
        result += "Tonnage: " + f"{t:,.0f}" + " tons\n"
        result += "Purchase price: $" + str(purchase) + "/ton\n"
        result += "FOB price: $" + str(fob) + "/ton\n"
        result += "Exchange rate: " + f"{rate:,.0f}" + "\n"
        result += "-------------------\n"
        result += "Revenue: $" + f"{revenue_usd:,.0f}" + "\n"
        result += "Purchase cost: $" + f"{purchase_cost:,.0f}" + "\n"
        result += "Freight: $" + f"{freight_cost:,.0f}" + "\n"
        result += "Port costs: $" + f"{port_cost:,.0f}" + "\n"
        result += "Total Cost: $" + f"{total_cost:,.0f}" + "\n"
        result += "-------------------\n"
        result += "Net Profit (USD): $" + f"{profit_usd:,.0f}" + "\n"
        result += "Net Profit (Rials): " + f"{profit_rials:,.0f}" + "\n"
        result += "-------------------\n"

        await update.message.reply_text(result)
        del user_data[user_id]

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from datetime import datetime

# States for ConversationHandler
PRODUCT, PURCHASE, FOB, RATE, TONNAGE, FREIGHT, PORT = range(7)

# Simple in-memory database
user_data = {}

# ========== /start command ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("Profit Calculation", callback_data="new_profit")],
        [InlineKeyboardButton("Product Prices", callback_data="prices")],
        [InlineKeyboardButton("Guide / Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to Ironston Bot!\n\n"
        "Choose an option from the buttons below:",
        reply_markup=reply_markup
    )

# ========== Handle button clicks ==========
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "new_profit":
        user_id = query.from_user.id
        user_data[user_id] = {}
        await query.message.reply_text("Step 1/7: Enter product name:\nExample: Iron Ore 62%, Fe 65%, Pellet, Billet")
        return PRODUCT

    elif query.data == "prices":
        await query.message.reply_text(
            "Current Iron Ore Prices:\n\n"
            "Iron Ore 62%: $118.5/ton\n"
            "Fe 65%: $135.2/ton\n"
            "Pellet: $156.8/ton\n"
            "Billet: $520/ton\n\n"
            "Last update: Just now"
        )
        return

    elif query.data == "help":
        await query.message.reply_text(
            "Bot Guide:\n\n"
            "1. Press 'Profit Calculation' to start\n"
            "2. Answer questions step by step\n"
            "3. Enter numbers when asked\n\n"
            "Commands:\n"
            "/start - Main menu\n"
            "/cancel - Cancel current operation"
        )
        return

# ========== Profit calculation steps ==========
async def step1_product(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    user_data[user_id]["product"] = text
    await update.message.reply_text("Step 2/7: Purchase price (USD per ton)?\nExample: 105")
    return PURCHASE

async def step2_purchase(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["purchase"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return PURCHASE
    await update.message.reply_text("Step 3/7: FOB selling price (USD per ton)?\nExample: 118.5")
    return FOB

async def step3_fob(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["fob"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return FOB
    await update.message.reply_text("Step 4/7: Exchange rate (Rials per USD)?\nExample: 65000")
    return RATE

async def step4_rate(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["rate"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return RATE
    await update.message.reply_text("Step 5/7: Tonnage (tons)?\nExample: 5000")
    return TONNAGE

async def step5_tonnage(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["tonnage"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return TONNAGE
    await update.message.reply_text("Step 6/7: Freight cost (USD per ton)?\nExample: 18")
    return FREIGHT

async def step6_freight(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["freight"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid num

ber")
        return FREIGHT
    await update.message.reply_text("Step 7/7: Port and loading cost (USD per ton)?\nExample: 4")
    return PORT

async def step7_port(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["port"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return PORT

    # Calculate profit
    data = user_data[user_id]
    t = data["tonnage"]
    purchase = data["purchase"]
    fob = data["fob"]
    rate = data["rate"]
    freight = data["freight"]
    port = data["port"]

    revenue_usd = fob  t
    purchase_cost = purchase  t
    freight_cost = freight  t
    port_cost = port  t
    total_cost = purchase_cost + freight_cost + port_cost
    profit_usd = revenue_usd - total_cost
    profit_rials = profit_usd * rate

    now = datetime.now().strftime("%b %d, %Y - %H:%M")

    result = (
        f"=== PROFIT CALCULATION ===\n"
        f"{now}\n"
        f"------------------------\n"
        f"Product: {data['product']}\n"
        f"Tonnage: {t:,.0f} tons\n"
        f"Purchase price: ${purchase}/ton\n"
        f"FOB price: ${fob}/ton\n"
        f"Exchange rate: {rate:,.0f} Rials\n"
        f"------------------------\n"
        f"Revenue: ${revenue_usd:,.0f}\n"
        f"Purchase cost: ${purchase_cost:,.0f}\n"
        f"Freight: ${freight_cost:,.0f}\n"
        f"Port costs: ${port_cost:,.0f}\n"
        f"Total Cost: ${total_cost:,.0f}\n"
        f"------------------------\n"
        f"Net Profit (USD): ${profit_usd:,.0f}\n"
        f"Net Profit (Rials): {profit_rials:,.0f}\n"
        f"------------------------"
    )

    await update.message.reply_text(result)
    del user_data[user_id]
    return ConversationHandler.END

# ========== Cancel operation ==========
async def cancel(update: Update, context):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Operation cancelled.\nPress /start to begin again.")
    return ConversationHandler.END

# ========== MAIN FUNCTION ==========
def main():
    # IMPORTANT: Replace with your actual bot token
    TOKEN = "YOUR_BOT_TOKEN_HERE"

    # Create application
    app = Application.builder().token(TOKEN).build()

    # Create conversation handler for profit calculation
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^new_profit$")],
        states={
            PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, step1_product)],
            PURCHASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, step2_purchase)],
            FOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, step3_fob)],
            RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, step4_rate)],
            TONNAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, step5_tonnage)],
            FREIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, step6_freight)],
            PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, step7_port)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(new_profit|prices|help)$"))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))

    # Start the bot
    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if name == "__main__":
    main()

