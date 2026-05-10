import os
import logging
import requests
import re
import time
import threading
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOKEN = os.environ.get("BOT_TOKEN")

# ========== ذخیره و بازیابی نرخ ارز ==========
DATA_FILE = "rates.json"

def load_rates():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"free": 178000, "secondary": 28500}

def save_rates(data):
    with open(DATA_FILE, 'w') as f:
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

def start_updater():
    update_rates()
    def loop():
        while True:
            time.sleep(15 * 60)
            update_rates()
    threading.Thread(target=loop, daemon=True).start()

start_updater()

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

# ========== قیمت جهانی ==========
async def world(update, context):
    await update.callback_query.answer()
    text = "🌍 قیمت جهانی:\n\n"
    text += "کنسانتره: FOB $85 | CFR شمال $130 | CFR جنوب $131\n"
    text += "گندله: FOB $105 | CFR شمال $155 | CFR جنوب $156\n"
    text += "آهن اسفنجی: FOB $200 | CFR شمال $280 | CFR جنوب $282\n"
    text += "شمش: FOB $480 | CFR شمال $520 | CFR جنوب $515\n"
    text += "میلگرد: FOB $550 | CFR شمال $600 | CFR جنوب $595"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

# ========== بورس کالا ==========
async def ice(update, context):
    await update.callback_query.answer()
    text = "🏭 بورس کالا:\n\n"
    text += "کنسانتره: ۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰ تومان/تن\n"
    text += "گندله: ۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰ تومان/تن\n"
    text += "آهن اسفنجی: ۱۴,۸۰۰ - ۱۵,۵۰۰ تومان/تن\n"
    text += "شمش: ۴۱,۰۰۰ - ۴۴,۰۰۰ تومان/تن\n"
    text += "میلگرد: ۵۰,۰۰۰ - ۶۵,۰۰۰ تومان/کیلو"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

# ========== بازار آزاد ==========
async def free(update, context):
    await update.callback_query.answer()
    text = "🔄 بازار آزاد:\n\n"
    text += "کنسانتره: ۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰ تومان/تن\n"
    text += "گندله: ۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰ تومان/تن\n"
    text += "آهن اسفنجی: ۱۶,۰۰۰ - ۱۶,۸۰۰ تومان/تن\n"
    text += "شمش: ۵۴,۰۰۰ - ۵۷,۰۰۰ تومان/تن\n"
    text += "میلگرد: ۶۳,۰۰۰ - ۶۸,۰۰۰ تومان/تن"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

# ========== قیمت کارخانه ==========
async def factory(update, context):
    await update.callback_query.answer()
    text = "🏭 قیمت کارخانه:\n\n"
    text += "شمش اصفهان: ۴۳,۰۹۱ | یزد: ۴۳,۰۰۰ | قزوین: ۴۰,۴۰۹\n"
    text += "میلگرد ذوب آهن: ۶۵,۰۰۰ | امیرکبیر: ۶۶,۰۰۰\n"
    text += "آهن اسفنجی میانه: ۱۶,۸۰۰ | نطنز: ۱۶,۵۰۰\n"
    text += "گندله گل گهر: ۶,۴۰۰,۰۰۰ | چادرملو: ۶,۳۰۰,۰۰۰\n"
    text += "کنسانتره گل گهر: ۴,۳۰۰,۰۰۰ | مرکزی: ۴,۶۰۰,۰۰۰"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

# ========== نرخ ارز ==========
async def rate(update, context):
    await update.callback_query.answer()
    rates = load_rates()
    text = f"💱 نرخ ارز:\n\n"
    text += f"نرخ مبادله‌ای: {rates['secondary']:,} تومان\n"
    text += f"نرخ بازار آزاد: {rates['free']:,} تومان"
    await update.callback_query.edit_message_text(text, reply_markup=back_button())

# ========== بازگشت ==========
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

# ========== اجرا ==========
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
