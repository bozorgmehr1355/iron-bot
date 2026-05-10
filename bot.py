import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("BOT_TOKEN")

# منابع قیمت (واقعی)
def get_usd_free():
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        return int(r.json()["stats"]["USDT-IRT"]["latest"]) // 10 if r.status_code == 200 else 178000
    except:
        return 178000

def get_usd_secondary():
    try:
        r = requests.get("https://www.tgju.org/sana/", timeout=5)
        import re
        match = re.search(r'(\d{1,3}(?:,\d{3})*)', r.text)
        return int(match.group(1).replace(',', '')) // 10 if match else 28500
    except:
        return 28500

# داده‌های ثابت (با اعداد منطقی)
products = [
    ("کنسانتره سنگ آهن", "۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰", "۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰"),
    ("گندله", "۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰", "۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰"),
    ("آهن اسفنجی", "۱۴,۸۰۰ - ۱۵,۵۰۰", "۱۶,۰۰۰ - ۱۶,۸۰۰"),
    ("شمش فولادی", "۴۱,۰۰۰ - ۴۴,۰۰۰", "۵۴,۰۰۰ - ۵۷,۰۰۰"),
    ("میلگرد", "۱۵,۸۰۰ - ۱۶,۸۰۰", "۶۳,۰۰۰ - ۶۸,۰۰۰"),
]

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.message.reply_text("ربات قیمت آهن و فولاد", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_world(update, context):
    await update.callback_query.answer()
    text = "🌍 قیمت جهانی:\n\n"
    text += "کنسانتره: $85/تن (FOB)\nگندله: $105/تن\nآهن اسفنجی: $200/تن\nشمش: $480/تن\nمیلگرد: $550/تن"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

async def show_ice(update, context):
    await update.callback_query.answer()
    text = "🏭 بورس کالا:\n\n"
    for name, ice, _ in products:
        text += f"{name}: {ice} تومان/تن\n"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

async def show_free(update, context):
    await update.callback_query.answer()
    text = "🔄 بازار آزاد:\n\n"
    for name, _, free in products:
        text += f"{name}: {free} تومان/تن\n"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

async def show_factory(update, context):
    await update.callback_query.answer()
    text = "🏭 قیمت کارخانه:\n\n"
    text += "شمش اصفهان: 43,091\nشمش یزد: 43,000\nمیلگرد ذوب آهن: 65,000\nگندله گل گهر: 6,400,000\nکنسانتره گل گهر: 4,300,000"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

async def show_rate(update, context):
    await update.callback_query.answer()
    text = f"💱 نرخ ارز:\n\n"
    text += f"نرخ مبادله‌ای: {get_usd_secondary()} تومان\n"
    text += f"نرخ بازار آزاد: {get_usd_free()} تومان"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]))

async def back(update, context):
    await update.callback_query.answer()
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.callback_query.edit_message_text("ربات قیمت آهن و فولاد", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_world, pattern="world"))
    app.add_handler(CallbackQueryHandler(show_ice, pattern="ice"))
    app.add_handler(CallbackQueryHandler(show_free, pattern="free"))
    app.add_handler(CallbackQueryHandler(show_factory, pattern="factory"))
    app.add_handler(CallbackQueryHandler(show_rate, pattern="rate"))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    print("ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
