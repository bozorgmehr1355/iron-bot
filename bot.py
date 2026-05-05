import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8742538592:AAHBoNMe33Wvsin73049sdi6htK-f3hEfUU"
CHAT_ID = 715854466

def get_currency():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        r = requests.get(url, timeout=10)
        data = r.json()
        rates = data.get("rates", {})
        result = {}
        result["EUR"] = round(rates.get("EUR", 0), 4)
        result["AED"] = round(rates.get("AED", 0), 4)
        result["IRR"] = round(rates.get("IRR", 0), 0)
        return result
    except:
        return None

def get_iron_price():
    try:
        API_KEY = "e6de2613ce5902f03d502dff62d5f83c"
        url = f"https://api.metalpriceapi.com/v1/latest?api_key={API_KEY}&base=USD&currencies=IRON"
        r = requests.get(url, timeout=10)
        data = r.json()
        price = data["rates"]["IRON"]
        return round(1 / price, 2)
    except:
        return None

def build_report():
    currencies = get_currency()
    iron = get_iron_price()
    msg = "--- Market Report ---\n\n"
    if currencies:
        msg += f"USD/EUR: {currencies.get('EUR', 'N/A')}\n"
        msg += f"USD/AED: {currencies.get('AED', 'N/A')}\n"
        msg += f"USD/IRR: {currencies.get('IRR', 'N/A')}\n"
    else:
        msg += "Error getting currency data\n"
    msg += "\n"
    if iron:
        msg += f"Iron Ore (global): ${iron}\n"
    else:
        msg += "Error getting iron price\n"
    msg += "\n--- end ---"
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Get Report", callback_data="report")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Hello! Press the button below", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "report":
        msg = build_report()
        await query.edit_message_text(msg)

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = build_report()
    await update.message.reply_text(msg)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot started...")
    app.run_polling()

