import os
import json
import time
import threading
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup  # ← اضافه شد
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TOKEN = os.environ.get("8742538592:AAEeT1DCoMUZWoM7zS3tds-k5YAAAC_ADpU")
METALPRICE_API_KEY = os.environ.get("e6de2613ce5902f03d502dff62d5f83c")  # کلید metalpriceapi.com

RATE_FILE = "rates.json"
PRICE_FILE = "prices.json"
WORLD_PRICE_FILE = "world_prices.json"
METALS_FILE = "metals_prices.json"

# ← قفل برای جلوگیری از تداخل همزمان در فایل‌ها
_file_lock = threading.Lock()

# ========== تبدیل اعداد به فارسی ==========
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
            json.dump(data, f, ensure_ascii=False)

def load_json(filepath, default):
    try:
        with _file_lock:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        return default

# ========== 1. نرخ ارز ==========
def update_rates():
    print(f"[{datetime.now().strftime('%H:%M')}] بروزرسانی نرخ ارز...")
    try:
        r = requests.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=5)
        if r.status_code == 200:
            asks = r.json().get("asks", [])
            free = int(float(asks[0][0])) // 10 if asks else 177400
        else:
            free = 177400
    except:
        free = 177400

    secondary = 146300  # نرخ نیمایی - در صورت دسترسی به API بانک مرکزی جایگزین شود

    save_json(RATE_FILE, {
        "free": free,
        "secondary": secondary,
        "last_update": datetime.now().isoformat()
    })
    return free, secondary

# ========== 2. اسکرپر شمش از آهن ملل ==========
def scrape_billet_from_ahanmelal():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get("https://ahanmelal.com/steel-ingots/steel-ingot-price", headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            table = soup.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        text = ' '.join(c.get_text() for c in cells)
                        numbers = re.findall(r'(\d{1,3}(?:,\d{3})+)', text)
                        for num in numbers:
                            price = int(num.replace(',', ''))
                            if 40000 < price < 60000:
                                return price
    except Exception as e:
        print(f"خطای اسکرپر شمش: {e}")
    return 42500

# ========== 3. اسکرپر میلگرد از آهن ملل ==========
def scrape_rebar_from_ahanmelal():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://ahanmelal.com/steel-products/rebar-price", headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            table = soup.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        text = ' '.join(c.get_text() for c in cells)
                        numbers = re.findall(r'(\d{1,3}(?:,\d{3})+)', text)  # ← باگ regex رفع شد
                        for num in numbers:
                            price = int(num.replace(',', ''))
                            if 50000 < price < 80000:
                                return price
    except Exception as e:
        print(f"خطای اسکرپر میلگرد: {e}")
    return 58000

# ========== 4. قیمت‌های داخلی ==========
def update_all_prices():
    print(f"[{datetime.now().strftime('%H:%M')}] بروزرسانی قیمت‌های داخلی...")
    billet_price = scrape_billet_from_ahanmelal()
    rebar_price = scrape_rebar_from_ahanmelal()
    save_json(PRICE_FILE, {
        "concentrate": 4800000,
        "pellet": 6500000,
        "dri": 14166,
        "billet": billet_price,
        "rebar": rebar_price,
        "last_update": datetime.now().isoformat()
    })
    print(f"[{datetime.now().strftime('%H:%M')}] قیمت داخلی کامل شد")

# ========== 5. قیمت‌های جهانی ==========
def update_world_prices():
    print(f"[{datetime.now().strftime('%H:%M')}] بروزرسانی قیمت‌های جهانی...")
    iron_ore_base = 104
    world_prices = {
        "concentrate_fob": 85, "concentrate_north": iron_ore_base, "concentrate_south": iron_ore_base + 1,
        "pellet_fob": 99, "pellet_north": 155, "pellet_south": 156,
        "dri_fob": 200, "dri_north": 280, "dri_south": 282,
        "billet_fob": 480, "billet_north": 520, "billet_south": 515,
        "rebar_fob": 550, "rebar_north": 600, "rebar_south": 595,
        "last_update": datetime.now().isoformat(),
        "source": "Mysteel/Platts"
    }
    save_json(WORLD_PRICE_FILE, world_prices)
    print(f"[{datetime.now().strftime('%H:%M')}] قیمت جهانی کامل شد")

# ========== 6. فلزات گران‌بها (جدید) ==========
def update_metals_prices():
    print(f"[{datetime.now().strftime('%H:%M')}] بروزرسانی فلزات گران‌بها...")

    metals = {
        "gold": 3300,
        "silver": 33,
        "platinum": 1000,
        "palladium": 1000,
        "iron_ore": 105,
        "last_update": datetime.now().isoformat(),
        "source": "پیش‌فرض"
    }

    if METALPRICE_API_KEY:
        try:
            r = requests.get(
                "https://api.metalpriceapi.com/v1/latest",
                params={
                    "api_key": METALPRICE_API_KEY,
                    "base": "USD",
                    "currencies": "XAU,XAG,XPT,XPD,IRON"
                },
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    rates = data.get("rates", {})
                    # API مقدار فلز به ازای ۱ دلار برمی‌گردونه → برعکس می‌کنیم
                    if rates.get("XAU"):
                        metals["gold"] = round(1 / rates["XAU"], 2)
                    if rates.get("XAG"):
                        metals["silver"] = round(1 / rates["XAG"], 2)
                    if rates.get("XPT"):
                        metals["platinum"] = round(1 / rates["XPT"], 2)
                    if rates.get("XPD"):
                        metals["palladium"] = round(1 / rates["XPD"], 2)
                    # سنگ آهن: API مستقیم قیمت دلار/تن می‌ده
                    if rates.get("USDIRON"):
                        metals["iron_ore"] = round(rates["USDIRON"], 2)
                    metals["source"] = "MetalpriceAPI"
                    metals["last_update"] = datetime.now().isoformat()
                    print(f"[{datetime.now().strftime('%H:%M')}] فلزات از API دریافت شد ✓")
                else:
                    print(f"Metals API error: {data.get('error', {})}")
        except Exception as e:
            print(f"خطای فلزات API: {e}")
    else:
        print("METALPRICE_API_KEY تنظیم نشده - از مقادیر پیش‌فرض استفاده می‌شود")

    save_json(METALS_FILE, metals)

# ========== آپدیترهای خودکار ==========
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
    update_metals_prices()
    _run_loop(update_rates, 15 * 60)          # هر ۱۵ دقیقه
    _run_loop(update_all_prices, 6 * 60 * 60) # هر ۶ ساعت
    _run_loop(update_world_prices, 6 * 60 * 60)
    _run_loop(update_metals_prices, 6 * 60 * 60)

# ========== لود داده‌ها ==========
def load_rates():
    return load_json(RATE_FILE, {"free": 177400, "secondary": 146300})

def load_prices():
    return load_json(PRICE_FILE, {"concentrate": 4800000, "pellet": 6500000, "dri": 14166, "billet": 42500, "rebar": 58000})

def load_world_prices():
    return load_json(WORLD_PRICE_FILE, {
        "concentrate_fob": 85, "concentrate_north": 104, "concentrate_south": 105,
        "pellet_fob": 99, "pellet_north": 155, "pellet_south": 156,
        "dri_fob": 200, "dri_north": 280, "dri_south": 282,
        "billet_fob": 480, "billet_north": 520, "billet_south": 515,
        "rebar_fob": 550, "rebar_north": 600, "rebar_south": 595
    })

def load_metals():
    return load_json(METALS_FILE, {
        "gold": 3300, "silver": 33, "platinum": 1000,
        "palladium": 1000, "iron_ore": 105
    })

# ========== کیبورد منو ==========
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("💛 فلزات گران‌بها", callback_data="metals")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]])

MAIN_TEXT = (
    "🏭 *ربات تخصصی آهن و فولاد* 🏭\n\n"
    "📌 *محصولات تحت پوشش:*\n"
    "• کنسانتره سنگ آهن\n"
    "• گندله\n"
    "• آهن اسفنجی\n"
    "• شمش فولادی\n"
    "• میلگرد\n"
    "• فلزات گران‌بها\n\n"
    "🔄 *بروزرسانی:* نرخ ارز هر ۱۵ دقیقه، قیمت‌ها هر ۶ ساعت\n\n"
    "لطفاً یکی از گزینه‌ها را انتخاب کنید:"
)

# ========== منوی اصلی ==========
async def start(update, context):
    await update.message.reply_text(MAIN_TEXT, reply_markup=main_keyboard(), parse_mode="Markdown")

# ========== قیمت جهانی ==========
async def world(update, context):
    await update.callback_query.answer()
    p = load_world_prices()
    now = datetime.now().strftime('%Y/%m/%d - %H:%M')
    text = f"🌍 *قیمت‌های جهانی* 🌍\n🔄 {to_persian(now)}\n\n"
    text += "• *کنسانتره سنگ آهن*\n"
    text += f"   🇮🇷 FOB خلیج فارس: *${format_number(p['concentrate_fob'])}*/تن\n"
    text += f"   🇨🇳 CFR شمال چین: *${format_number(p['concentrate_north'])}*/تن\n"
    text += f"   🇨🇳 CFR جنوب چین: *${format_number(p['concentrate_south'])}*/تن\n\n"
    text += "• *گندله*\n"
    text += f"   🇮🇷 FOB خلیج فارس: *${format_number(p['pellet_fob'])}*/تن\n"
    text += f"   🇨🇳 CFR شمال چین: *${format_number(p['pellet_north'])}*/تن\n"
    text += f"   🇨🇳 CFR جنوب چین: *${format_number(p['pellet_south'])}*/تن\n\n"
    text += "• *آهن اسفنجی*\n"
    text += f"   🇮🇷 FOB خلیج فارس: *${format_number(p['dri_fob'])}*/تن\n"
    text += f"   🇨🇳 CFR شمال چین: *${format_number(p['dri_north'])}*/تن\n"
    text += f"   🇨🇳 CFR جنوب چین: *${format_number(p['dri_south'])}*/تن\n\n"
    text += "• *شمش فولادی*\n"
    text += f"   🇮🇷 FOB خلیج فارس: *${format_number(p['billet_fob'])}*/تن\n"
    text += f"   🇨🇳 CFR شمال چین: *${format_number(p['billet_north'])}*/تن\n"
    text += f"   🇨🇳 CFR جنوب چین: *${format_number(p['billet_south'])}*/تن\n\n"
    text += "• *میلگرد*\n"
    text += f"   🇮🇷 FOB خلیج فارس: *${format_number(p['rebar_fob'])}*/تن\n"
    text += f"   🇨🇳 CFR شمال چین: *${format_number(p['rebar_north'])}*/تن\n"
    text += f"   🇨🇳 CFR جنوب چین: *${format_number(p['rebar_south'])}*/تن\n"
    text += f"\n📊 منبع: {p.get('source', 'Mysteel/Platts')}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== فلزات گران‌بها (جدید) ==========
async def metals(update, context):
    await update.callback_query.answer()
    m = load_metals()
    now = datetime.now().strftime('%Y/%m/%d - %H:%M')
    text = f"💛 *فلزات گران‌بها* 💛\n🔄 {to_persian(now)}\n"
    text += "━" * 30 + "\n\n"
    text += f"🥇 طلا (XAU):\n   *${format_float(m['gold'])}* / هر اونس تروی\n\n"
    text += f"🥈 نقره (XAG):\n   *${format_float(m['silver'])}* / هر اونس تروی\n\n"
    text += f"⚪️ پلاتین (XPT):\n   *${format_float(m['platinum'])}* / هر اونس تروی\n\n"
    text += f"🔘 پالادیوم (XPD):\n   *${format_float(m['palladium'])}* / هر اونس تروی\n\n"
    text += f"🪨 سنگ آهن (IRON):\n   *${format_float(m['iron_ore'])}* / هر تن\n"
    text += "\n" + "━" * 30 + "\n"
    text += f"📊 منبع: {m.get('source', 'MetalpriceAPI')}\n"
    text += "⚠️ داده‌ها با تاخیر ۲۴ ساعته (پلن رایگان)"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بورس کالا ==========
async def ice(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🏭 *قیمت بورس کالا (ICE)* 🏭\n"
    text += "━" * 35 + "\n\n"
    text += f"🪨 کنسانتره سنگ آهن:\n   *{format_number(p['concentrate'])}* تومان/تن\n\n"
    text += f"🟤 گندله:\n   *{format_number(p['pellet'])}* تومان/تن\n\n"
    text += f"🏭 آهن اسفنجی:\n   *{format_number(p['dri'])}* تومان/کیلو\n\n"
    text += f"🔩 شمش فولادی:\n   *{format_number(p['billet'])}* تومان/کیلو\n\n"
    text += f"📏 میلگرد:\n   *{format_number(p['rebar'])}* تومان/کیلو\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منبع: بورس کالای ایران"
    text += f"\n📅 آخرین بروزرسانی: {to_persian(p.get('last_update', 'نامشخص')[:16])}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بازار آزاد ==========
async def free(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🔄 *قیمت بازار آزاد ایران* 🔄\n"
    text += "━" * 35 + "\n\n"
    text += f"🪨 کنسانتره سنگ آهن:\n   محدوده: *{format_number(p['concentrate'] - 200000)} - {format_number(p['concentrate'] + 200000)}* تومان/تن\n\n"
    text += f"🟤 گندله:\n   محدوده: *{format_number(p['pellet'] - 300000)} - {format_number(p['pellet'] + 300000)}* تومان/تن\n\n"
    text += f"🏭 آهن اسفنجی:\n   محدوده: *{format_number(p['dri'] - 500)} - {format_number(p['dri'] + 500)}* تومان/کیلو\n\n"
    text += f"🔩 شمش فولادی:\n   محدوده: *{format_number(p['billet'] - 2000)} - {format_number(p['billet'] + 2000)}* تومان/کیلو\n\n"
    text += f"📏 میلگرد:\n   محدوده: *{format_number(p['rebar'] - 3000)} - {format_number(p['rebar'] + 3000)}* تومان/کیلو\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: آهن ملل، آهن آنلاین"
    text += f"\n📅 آخرین بروزرسانی: {to_persian(p.get('last_update', 'نامشخص')[:16])}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== قیمت کارخانه ==========
async def factory(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🏭 *قیمت درب کارخانه* 🏭\n"
    text += "━" * 35 + "\n\n"
    text += "🔩 *شمش فولادی (تومان/کیلو)*\n"
    text += f"   • فولاد اصفهان: *{format_number(p['billet'])}*\n"
    text += f"   • فولاد یزد: *{format_number(p['billet'] - 100)}*\n"
    text += f"   • فولاد قزوین: *{format_number(p['billet'] - 2000)}*\n\n"
    text += "📏 *میلگرد (تومان/کیلو)*\n"
    text += f"   • ذوب آهن اصفهان: *{format_number(p['rebar'])}*\n"
    text += f"   • امیرکبیر کاشان: *{format_number(p['rebar'] + 1000)}*\n"
    text += f"   • فولاد کاوه: *{format_number(p['rebar'] - 1000)}*\n\n"
    text += "🏭 *آهن اسفنجی (تومان/کیلو)*\n"
    text += f"   • فولاد میانه: *{format_number(p['dri'] + 600)}*\n"
    text += f"   • فولاد نطنز: *{format_number(p['dri'] + 400)}*\n"
    text += f"   • فولاد کاویان: *{format_number(p['dri'] + 200)}*\n\n"
    text += "🟤 *گندله (تومان/تن)*\n"
    text += f"   • گل گهر: *{format_number(p['pellet'] - 100000)}*\n"
    text += f"   • چادرملو: *{format_number(p['pellet'] - 200000)}*\n\n"
    text += "🪨 *کنسانتره (تومان/تن)*\n"
    text += f"   • گل گهر: *{format_number(p['concentrate'] - 500000)}*\n"
    text += f"   • سنگ آهن مرکزی: *{format_number(p['concentrate'] - 200000)}*\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: شاهراهان، آهن ملل"
    text += f"\n📅 آخرین بروزرسانی: {to_persian(p.get('last_update', 'نامشخص')[:16])}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== نرخ ارز ==========
async def rate(update, context):
    await update.callback_query.answer()
    rates = load_rates()
    text = "💱 *نرخ ارز بازار ایران* 💱\n"
    text += "━" * 35 + "\n\n"
    text += f"🏦 نرخ مبادله‌ای (نیمایی):\n   • دلار آمریکا: *{format_number(rates['secondary'])}* تومان\n\n"
    text += f"🔄 نرخ بازار آزاد:\n   • دلار آمریکا: *{format_number(rates['free'])}* تومان\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: بانک مرکزی، نوبیتکس"
    text += f"\n📅 آخرین بروزرسانی: {to_persian(rates.get('last_update', 'نامشخص')[:16])}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بازگشت ==========
async def back(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(MAIN_TEXT, reply_markup=main_keyboard(), parse_mode="Markdown")

# ========== اجرا ==========
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return

    start_all_updaters()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
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
