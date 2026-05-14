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

TOKEN = os.environ.get("8742538592:AAEjPrIZoIe4DS3R1J46zrJ3FWHy7wC5-wM")
METALPRICE_API_KEY = os.environ.get("e6de2613ce5902f03d502dff62d5f83c")
ADMIN_ID = 8742538592  # بهتره از env بخونی

RATE_FILE = "rates.json"
PRICE_FILE = "prices.json"
WORLD_PRICE_FILE = "world_prices.json"
METALS_FILE = "metals_prices.json"

WAITING_VALUE = 1
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

# ==================== اسکرپرهای داخلی (بهبود یافته) ====================
def get_prices_from_text(text, min_p, max_p):
    matches = re.findall(r'(\d{1,3}(?:,\d{3})+(?:\.\d+)?)', text)
    prices = [int(float(m.replace(',', ''))) for m in matches if min_p < int(float(m.replace(',', ''))) < max_p]
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
            if r.status_code != 200: continue
            prices = get_prices_from_text(r.text, 55000, 90000)
            all_prices.extend(prices)
            if prices:
                print(f"✅ میلگرد از {url.split('//')[1][:20]}: {prices[0]}")
        except: continue
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
        except: continue
    return int(sum(all_prices)/len(all_prices)) if all_prices else None

def scrape_dri():
    urls = ["https://ahanmelal.com/steel-basic-materials/sponge-iron-price",
            "https://www.markazeahan.com/product-category/sponge-iron-price/"]
    all_prices = []
    for url in urls:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
            prices = get_prices_from_text(r.text, 12000, 20000)
            all_prices.extend(prices)
        except: continue
    return int(sum(all_prices)/len(all_prices)) if all_prices else None

def update_all_prices():
    current = load_json(PRICE_FILE, {"concentrate": 4800000, "pellet": 6500000, "dri": 14166, "billet": 42500, "rebar": 58000})

    print("🔄 شروع بروزرسانی قیمت‌های داخلی...")
    rebar = scrape_rebar()
    billet = scrape_billet()
    dri = scrape_dri()

    if rebar: current["rebar"] = rebar
    if billet: current["billet"] = billet
    if dri: current["dri"] = dri

    current["last

update"] = datetime.now().isoformat()
    save_json(PRICE_FILE, current)
    print(f"✅ داخلی: میلگرد={rebar} | شمش={billet} | DRI={dri}")

# ==================== قیمت‌های جهانی ====================
def update_world_prices():
    data = load_json(WORLD_PRICE_FILE, {
        "concentrate_fob": 85, "concentrate_north": 104, "concentrate_south": 105,
        "pellet_fob": 99, "pellet_north": 155, "pellet_south": 156,
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
    except: pass

    iron = data.get("concentrate_north", 105)
    data["billet_north"] = round(iron  5)
    data["rebar_north"] = round(iron  5.8)
    data["last_update"] = datetime.now().isoformat()
    data["source"] = "TradingEconomics + تخمین"
    save_json(WORLD_PRICE_FILE, data)
    print("✅ قیمت‌های جهانی بروز شد")

# ==================== بقیه کد (هندلرها، کیبوردها و ...) ====================
# (برای کوتاه شدن پیام، بقیه کد رو فعلاً مثل قبل نگه داشتم ولی تمیزتر)

def start_all_updaters():
    update_rates()
    update_all_prices()
    update_world_prices()
    run_loop(update_rates, 15*60)
    _run_loop(update_all_prices, 4*60*60)      # هر ۴ ساعت
    _run_loop(update_world_prices, 6*60*60)

# ... (بقیه توابع main_keyboard, world, metals, ice و ... مثل کد قبلی باقی می‌مانند)

# فقط تابع main رو کمی بهتر کردم
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return

    start_all_updaters()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(world, pattern="^world$"))
    app.add_handler(CallbackQueryHandler(metals, pattern="^metals$"))
    app.add_handler(CallbackQueryHandler(ice, pattern="^ice$"))
    app.add_handler(CallbackQueryHandler(free, pattern="^free$"))
    app.add_handler(CallbackQueryHandler(factory, pattern="^factory$"))
    app.add_handler(CallbackQueryHandler(rate, pattern="^rate$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^adm_|^edit_"))

    print("✅ ربات با اسکرپرهای بهبود یافته روشن شد")
    app.run_polling()

if __name == "__main__":
    main()

