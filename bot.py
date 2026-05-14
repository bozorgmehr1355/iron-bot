
import os
import json
import time	
import threading
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

TOKEN = os.environ.get("BOT_TOKEN")
METALPRICE_API_KEY = os.environ.get("METALPRICE_API_KEY")
ADMIN_ID = 715854466

RATE_FILE = "rates.json"
PRICE_FILE = "prices.json"
WORLD_PRICE_FILE = "world_prices.json"
METALS_FILE = "metals_prices.json"

WAITING_VALUE = 1
_file_lock = threading.Lock()

# ========== ابزارها ==========

def to_persian(num):
    persian = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
               '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}
    return ''.join(persian.get(ch, ch) for ch in str(num))

def format_number(num):
    return to_persian(f"{num:,}")

def format_float(num, decimals=2):
    return to_persian(f"{num:,.{decimals}f}")

def save_json(filepath, data):
    with _file_lock:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(filepath, default):
    try:
        with _file_lock:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        return default

def is_admin(update):
    return update.effective_user.id == ADMIN_ID

# بقیه کد اصلی شما (همه توابع) بدون تغییر
# ... (برای جلوگیری از طولانی شدن پیام، بگو ادامه بده تا بقیه کد را 

بفرستم)

# ========== اجرا ==========
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return

    start_all_updaters()

    app = Application.builder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={
            WAITING_VALUE: [
                CallbackQueryHandler(admin_callback, pattern="^(adm_|edit_)"),
                MessageHandler(filters.TEXT & \~filters.COMMAND, receive_value)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("push_prices", 

push_prices))
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(world,   pattern="^world$"))
    app.add_handler(CallbackQueryHandler(metals,  pattern="^metals$"))
    app.add_handler(CallbackQueryHandler(ice,     pattern="^ice$"))
    app.add_handler(CallbackQueryHandler(free,    pattern="^free$"))
    app.add_handler(CallbackQueryHandler(factory, pattern="^factory$"))
    app.add_handler(CallbackQueryHandler(rate,    pattern="^rate$"))
    app.add_handler(CallbackQueryHandler(back,    pattern="^back$"))

    print("✅ ربات روشن شد")
    app.run_polling()


if __name__ == "__main__":
    main()
