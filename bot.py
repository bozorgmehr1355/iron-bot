import os
import logging
import requests
import re
import time
import threading
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from price_scraper import start_price_updater, DATA_FILE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOKEN = os.environ.get("BOT_TOKEN")

# ========== ذخیره و بازیابی نرخ ارز ==========
RATE_FILE = "rates.json"

def load_rates():
    try:
        with open(RATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"free": 178000, "secondary": 28500}

def save_rates(data):
    with open(RATE_FILE, 'w') as f:
        json.dump(data, f)

def update_rates():
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        free = int(r.json()["stats"]["USDT-IRT"]["latest"]) // 10 if r.status_code == 200 else 178000
    except:
        free = 178000
    try:
        r = requests.get("https://www.tgju.org/sana/", timeout=5)
        match = re.search(r'(\d{1,3}(?:,\d{3})*)', r.text)
        secondary = int(match.group(1).replace(',', '')) // 10 if match else 28500
    except:
        secondary = 28500
    save_rates({"free": free, "secondary": secondary})
    return free, secondary

def start_rate_updater():
    update_rates()
    def loop():
        while True:
            time.sleep(15 * 60)
            update_rates()
    threading.Thread(target=loop, daemon=True).start()

start_rate_updater()
start_price_updater()

# ========== منوی اصلی ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.message.reply_text(
        "🏭 ربات آهن و فولاد\n\nلطفاً انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت", callback_data="back")]])

def load_prices():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

async def world(update, context):
    await update.callback_query.answer()
    text = "🌍 قیمت جهانی:\n\n"
    text += "کنسانتره: FOB $85 | CFR شمال $130 | CFR جنوب $131\n"
    text += "گندله: FOB $105 | CFR شمال $155 | CFR جنوب $156\n"
    text += "آهن اسفنجی: FOB $200 | CFR شمال $280 | CFR جنوب $282\n"
    text += "شمش: FOB $480 | CFR شمال $520 | CFR جنوب $515\n"
    text += "میلگرد: FOB $550 | CFR شمال $600 | CFR جنوب $595"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

async def ice(update, context):
    await update.callback_query.answer()
    p = load_prices()
    if not p:
        p = {}
    text = "🏭 بورس کالا:\n\n"
    text += f"کنسانتره: {p.get('ice_concentrate', '۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰')} تومان/تن\n"
    text += f"گندله: {p.get('ice_pellet', '۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰')} تومان/تن\n"
    text += f"آهن اسفنجی: {p.get('ice_dri', '۱۴,۸۰۰ - ۱۵,۵۰۰')} تومان/تن\n"
    text += f"شمش: {p.get('ice_billet', '۴۱,۰۰۰ - ۴۴,۰۰۰')} تومان/تن\n"
    text += f"میلگرد: {p.get('ice_rebar', '۵۰,۰۰۰ - ۶۵,۰۰۰')} تومان/کیلو"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

async def free(update, context):
    await update.callback_query.answer()
    p = load_prices()
    if not p:
        p = {}
    text = "🔄 بازار آزاد:\n\n"
    text += f"کنسانتره: {p.get('free_concentrate', '۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰')} تومان/تن\n"
    text += f"گندله: {p.get('free_pellet', '۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰')} تومان/تن\n"
    text += f"آهن اسفنجی: {p.get('free_dri', '۱۶,۰۰۰ - ۱۶,۸۰۰')} تومان/تن\n"
    text += f"شمش: {p.get('free_billet', '۵۴,۰۰۰ - ۵۷,۰۰۰')} تومان/تن\n"
    text += f"میلگرد: {p.get('free_rebar', '۶۳,۰۰۰ - ۶۸,۰۰۰')} تومان/تن"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

async def factory(update, context):
    await update.callback_query.answer()
    p = load_prices()
    if not p:
        p = {}
    text = "🏭 قیمت کارخانه:\n\n"
    text += f"شمش: {p.get('factory_billet', 'اصفهان: ۴۳,۰۹۱ | یزد: ۴۳,۰۰۰ | قزوین: ۴۰,۴۰۹')}\n"
    text += f"میلگرد: {p.get('factory_rebar', 'ذوب آهن: ۶۵,۰۰۰ | امیرکبیر: ۶۶,۰۰۰')}\n"
    text += f"آهن اسفنجی: {p.get('factory_dri', 'میانه: ۱۶,۸۰۰ | نطنز: ۱۶,۵۰۰')}\n"
    text += f"گندله: {p.get('factory_pellet', 'گل گهر: ۶,۴۰۰,۰۰۰ | چادرملو: ۶,۳۰۰,۰۰۰')}\n"
    text += f"کنسانتره: {p.get('factory_concentrate', 'گل گهر: ۴,۳۰۰,۰۰۰ | مرکزی: ۴,۶۰۰,۰۰۰')}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

async def rate(update, context):
    await update.callback_query.answer()
    rates = load_rates()
    text = f"💱 نرخ ارز:\n\nنرخ مبادله‌ای: {rates['secondary']:,} تومان\nنرخ بازار آزاد: {rates['free']:,} تومان"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

async def back(update, context):
    await update.callback_query.answer()
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.callback_query.edit_message_text("ربات آهن و فولاد", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    if not TOKEN:
        print("BOT_TOKEN not found!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(world, pattern="world"))
    app.add_handler(CallbackQueryHandler(ice, pattern="ice"))
    app.add_handler(CallbackQueryHandler(free, pattern="free"))
    app.add_handler(CallbackQueryHandler(factory, pattern="factory"))
    app.add_handler(CallbackQueryHandler(rate, pattern="rate"))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    print("ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
