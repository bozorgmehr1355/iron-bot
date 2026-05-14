
import os
import json
import time
import threading
import requests
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")

_file_lock = threading.Lock()

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


def format_number(num):
    persian = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}
    return ''.join(persian.get(ch, ch) for ch in str(int(num)))

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_prices_from_text(text):
    matches = re.findall(r'(\d{1,3}(?:,\d{3})+(?:\.\d+)?)', text)
    prices = []
    for m in matches:
        try:
            p = int(float(m.replace(',', '')))
            if 55000 < p < 90000:
                prices.append(p)
        except:
            continue
    return prices

def scrape_rebar():
    try:
        r = requests.get("https://ahanonline.com/product-category/میلگرد-آجدار/قیمت-میلگرد-آجدار/", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            prices = get_prices_from_text(r.text)
            if prices:

                return int(sum(prices)/len(prices))
    except:
        pass
    return None

def update_all_prices():
    current = load_json("prices.json", {"rebar": 58000})
    rebar = scrape_rebar()
    if rebar:
        current["rebar"] = rebar
    current["last_update"] = datetime.now().isoformat()
    save_json("prices.json", current)
    return current

def update_rates():
    try:
        r = requests.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10)
        if r.status_code == 200:
            asks = r.json().get("asks", [])
            free = int(float(asks[0][0])) // 10 if asks else 177400
        else:
            free = 177400
    except:
        free = 177400

    current = load_json("rates.json", {})
    current["free"] = free

    current["last_update"] = datetime.now().isoformat()
    save_json("rates.json", current)
    return current

def _run_loop(func, interval):
    def loop():
        while True:
            time.sleep(interval)
            try:
                func()
            except Exception as e:
                print(f"خطا: {e}")
    threading.Thread(target=loop, daemon=True).start()

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]])

MAIN_TEXT = "🏭 ربات تخصصی آهن و فولاد 🏭\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:"

async def start(update: Update, context):
    await update.message.reply_text(MAIN_TEXT, reply_markup=main_keyboard())

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        await query.edit_message_text(MAIN_TEXT, reply_markup=main_keyboard())
        return

    if data == "rate":
        rates = update_rates()
        text = f"💱 نرخ ارز آزاد\n\nدلار آزاد: {format_number(rates.get('free', 177400))} تومان"

    elif data == "free":
        prices = load_json("prices.json", {})
        text = f"🔄 بازار آزاد\n\nمیلگرد: {format_number(prices.get('rebar', 58000))} تومان"

    else:
        text = "این بخش به زودی اضافه میشود."


    await query.edit_message_text(text, reply_markup=back_button())

def main():
    if not TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return

    update_all_prices()
    update_rates()
    _run_loop(update_all_prices, 7200)
    _run_loop(update_rates, 900)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ ربات شروع شد")
    app.run_polling()

if __name__ == "__main__":
    main()
