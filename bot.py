
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

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

# ==================== اسکرپرها ====================
def scrape_rebar():
    urls = [
        "https://ahanonline.com/product-category/میلگرد-آجدار/قیمت-میلگرد-آجدار/",
        "https://ahanonline.com/product-category/میلگرد/"
    ]
    all_prices = []
    for url in urls:
        try:
            print(f"🔍 اسکرپ: {url}")
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                prices = get_prices_from_text(r.text, 55000, 90000)
                all_prices.extend(prices)
                if prices:
                    print(f"✅ پیدا شد: {prices[0]}")
                    break
        except Exception as e:
            print(f"❌ خطا: {e}")
    return int(sum(all_prices)/len(all_prices)) if all_prices else None



def update_all_prices():
    current = load_json(PRICE_FILE, {"rebar": 58000, "billet": 42500, "dri": 14166})
    print("🔄 شروع بروزرسانی قیمت‌ها...")
    
    rebar = scrape_rebar()
    if rebar:
        current["rebar"] = rebar
    
    current["last_update"] = datetime.now().isoformat()
    save_json(PRICE_FILE, current)
    print(f"✅ بروزرسانی شد | میلگرد ≈ {rebar}")


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


def _run_loop(func, interval):
    def loop():
        while True:
            time.sleep(interval)
            try:
                func()
            except Exception as e:
                print(f"خطا در {func.__name__}: {e}")
    threading.Thread(target=loop, daemon=True).start()


def start_all_updaters():
    update_rates()
    update_all_prices()
    _run_loop(update_rates, 900)      # 15 دقیقه
    _run_loop(update_all_prices, 7200)  # 2 ساعت


# ==================== ربات ====================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],

        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ])


async def start(update: Update, context):
    await update.message.reply_text("🏭 ربات آهن و فولاد فعال است.\nمنو:", reply_markup=main_keyboard())


async def back(update: Update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🏭 ربات آهن و فولاد", reply_markup=main_keyboard())


def main():
    if not TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return

    start_all_updaters()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))


    print("✅ ربات شروع شد...")
    app.run_polling()


if __name__ == "__main__":
    main()
