
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

# ==================== تنظیمات ====================
TOKEN = os.environ.get("BOT_TOKEN")          # ← مهم: از Environment استفاده کن
ADMIN_ID = 8742538592

RATE_FILE = "rates.json"
PRICE_FILE = "prices.json"
WORLD_PRICE_FILE = "world_prices.json"
METALS_FILE = "metals_prices.json"

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

def is_admin(update):
    return update.effective_user.id == ADMIN_ID

# ==================== اسکرپرها ====================
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

def scrape_rebar():
    urls = [
        "https://ahanonline.com/product-category/میلگرد-آجدار/قیمت-میلگرد-آجدار/",
        "https://ahanprice.com/Price/میلگرد-آجدار",
        "https://www.markazeahan.com/product-category/میلگرد/",
        "https://ahanmelal.com/rebar/ribbed-rebar-price"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    all_prices = []
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:

                continue
            prices = get_prices_from_text(r.text, 55000, 90000)
            all_prices.extend(prices)
            if prices:
                print(f"✅ میلگرد گرفته شد: {prices[0]}")
        except Exception as e:
            print(f"خطا در scrape_rebar {url}: {e}")
    return int(sum(all_prices)/len(all_prices)) if all_prices else None

def scrape_billet():
    urls = [
        "https://ahanjam.com/قیمت-شمش-فولادی/",
        "https://ahanmelal.com/steel-ingots/steel-ingot-price",
        "https://www.markazeahan.com/product-category/steel-ingot/"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    all_prices = []
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=12)
            prices = get_prices_from_text(r.text, 35000, 70000)
            all_prices.extend(prices)
        except:

            continue
    return int(sum(all_prices)/len(all_prices)) if all_prices else None

def scrape_dri():
    urls = [
        "https://ahanmelal.com/steel-basic-materials/sponge-iron-price",
        "https://www.markazeahan.com/product-category/sponge-iron-price/"
    ]
    all_prices = []
    for url in urls:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
            prices = get_prices_from_text(r.text, 12000, 20000)
            all_prices.extend(prices)
        except:
            continue
    return int(sum(all_prices)/len(all_prices)) if all_prices else None

# ==================== بروزرسانی قیمت‌ها ====================
def update_all_prices():
    current = load_json(PRICE_FILE, {
        "concentrate": 4800000,

        "pellet": 6500000,
        "dri": 14166,
        "billet": 42500,
        "rebar": 58000
    })
    print("🔄 شروع بروزرسانی قیمت‌های داخلی...")

    rebar = scrape_rebar()
    billet = scrape_billet()
    dri = scrape_dri()

    if rebar:
        current["rebar"] = rebar
    if billet:
        current["billet"] = billet
    if dri:
        current["dri"] = dri

    current["last_update"] = datetime.now().isoformat()
    save_json(PRICE_FILE, current)
    print(f"✅ داخلی بروز شد | میلگرد={rebar} | شمش={billet} | DRI={dri}")


def update_world_prices():
    data = load_json(WORLD_PRICE_FILE, {
        "concentrate_fob": 85, "concentrate_north": 104, "concentrate_south": 105,
        "pellet_fob": 99, "pellet_north": 155, "pellet_south": 

156,
        "dri_fob": 200, "dri_north": 280, "dri_south": 282,
        "billet_fob": 480, "billet_north": 520, "billet_south": 515,
        "rebar_fob": 550, "rebar_north": 600, "rebar_south": 595,
    })

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get("https://tradingeconomics.com/commodity/iron-ore", headers=headers, timeout=12)
        if r.status_code == 200:
            prices = get_prices_from_text(r.text, 90, 150)
            if prices:
                iron = prices[0]
                data["concentrate_north"] = round(iron)
                data["concentrate_fob"] = round(iron - 15)
                print(f"✅ Iron Ore جهانی: ${iron}")
    except Exception as e:
        print(f"خطا جهانی: {e}")

    iron = data.get("concentrate_north", 105)
    data["billet_north"] = round(iron * 5)
    data["rebar_north"] = round(iron * 5.8)
    data["last_update"] = datetime.now().isoformat()
    data["source"] = "TradingEconomics + تخمین"
    save_json(WORLD_PRICE_FILE, data)
    print("✅ قیمت‌های جهانی بروز شد")



def update_rates():
    try:
        r = requests.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=5)
        if r.status_code == 200:
            asks = r.json().get("asks", [])
            free = int(float(asks[0][0])) // 10 if asks else 177400
        else:
            free = 177400
    except:
        free = 177400

    current = load_json(RATE_FILE, {})
    current["free"] = free
    current.setdefault("secondary", 146300)
    current["last_update"] = datetime.now().isoformat()
    save_json(RATE_FILE, current)


# ==================== لوپ بروزرسانی ====================
def _run_loop(func, interval_seconds):
    def loop():
        while True:
            time.sleep(interval_seconds)
            try:

                func()
            except Exception as e:
                print(f"خطا در {func.__name__}: {e}")
    threading.Thread(target=loop, daemon=True).start()


def start_all_updaters():
    update_rates()
    update_all_prices()
    update_world_prices()

    _run_loop(update_rates, 15 * 60)           # هر ۱۵ دقیقه
    _run_loop(update_all_prices, 4 * 60 * 60)  # هر ۴ ساعت
    _run_loop(update_world_prices, 6 * 60 * 60) # هر ۶ ساعت


# ==================== کیبورد ====================
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


async def start(update: Update, context):
    await update.message.reply_text(MAIN_TEXT, reply_markup=main_keyboard(), parse_mode="Markdown")


async def back(update: Update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(MAIN_TEXT, reply_markup=main_keyboard(), parse_mode="Markdown")

# ==================== راه‌اندازی ربات ====================
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده است!")
        return

    start_all_updaters()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))

    print("✅ ربات با موفقیت شروع شد")
    app.run_polling()


if __name__ == "__main__":
    main()
