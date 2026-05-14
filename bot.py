
import os
import json
import time
import threading
import requests
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ==================== تنظیمات ====================
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 8742538592

RATE_FILE = "rates.json"
PRICE_FILE = "prices.json"
WORLD_PRICE_FILE = "world_prices.json"

_file_lock = threading.Lock()

# ==================== ابزارها ====================
def to_persian(num):
    persian = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}

    return ''.join(persian.get(ch, ch) for ch in str(num))

def format_number(num):
    return to_persian(f"{int(num):,}")

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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_prices_from_text(text, min_p, max_p):
    matches = re.findall(r'(\d{1,3}(?:,\d{3})+(?:\.\d+)?)', text)
    prices = []
    for m in matches:
        try:
            price = int(float(m.replace(',', '')))
            if min_p < price < max_p:

                prices.append(price)
        except:
            continue
    return prices

# ==================== اسکرپر ====================
def scrape_rebar():
    urls = [
        "https://ahanonline.com/product-category/میلگرد-آجدار/قیمت-میلگرد-آجدار/",
        "https://ahanonline.com/product-category/میلگرد/"
    ]
    all_prices = []
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                prices = get_prices_from_text(r.text, 55000, 90000)
                all_prices.extend(prices)
                if prices:
                    break
        except:
            continue
    return int(sum(all_prices)/len(all_prices)) if all_prices else None

# ==================== بروزرسانی ====================
def update_all_prices():
    current = load_json(PRICE_FILE, {"rebar": 58000, "billet": 42500, "dri": 14166})
    rebar = scrape_rebar()
    if rebar:
        current["rebar"] = rebar
    current["last_update"] = datetime.now().isoformat()
    save_json(PRICE_FILE, current)
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

    current = load_json(RATE_FILE, {})
    current["free"] = free
    current["last_update"] = datetime.now().isoformat()
    save_json(RATE_FILE, current)

    return current

def _run_loop(func, interval):
    def loop():
        while True:
            time.sleep(interval)
            try:
                func()
            except Exception as e:
                print(f"خطا در {func.__name__}: {e}")
    threading.Thread(target=loop, daemon=True).start()

# ==================== کیبوردها ====================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ])

def back_button():

    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]])

MAIN_TEXT = "🏭 ربات تخصصی آهن و فولاد 🏭\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:"

# ==================== هندلرها ====================
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
        text = "💱 نرخ ارز آزاد\n\n" \
               f"دلار آزاد: {format_number(rates.get('free', 177400))} تومان\n" \
               f"آخرین بروزرسانی: {rates.get('last_update', 

'نامشخص')[:16]}"

    elif data == "free":
        prices = load_json(PRICE_FILE, {})
        text = "🔄 بازار آزاد\n\n" \
               f"میلگرد: {format_number(prices.get('rebar', 58000))} تومان\n" \
               f"آخرین بروزرسانی: {prices.get('last_update', 'نامشخص')[:16]}"

    else:
        text = "این بخش هنوز کامل پیاده‌سازی نشده است.\nبه زودی اضافه خواهد شد."

    await query.edit_message_text(text, reply_markup=back_button())

# ==================== اجرا ====================
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return

    update_all_prices()
    update_rates()

    _run_loop(update_all_prices, 7200)   # هر ۲ ساعت
    _run_loop(update_rates, 900)         # هر ۱۵ دقیقه

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ ربات با موفقیت شروع شد")
    app.run_polling()


if __name__ == "__main__":
    main()
