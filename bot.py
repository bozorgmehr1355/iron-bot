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
            json.dump(data, f, ensure_ascii=False)

def load_json(filepath, default):
    try:
        with _file_lock:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        return default

def is_admin(update):
    return update.effective_user.id == ADMIN_ID

# ========== آپدیت خودکار ==========
def update_rates():
    try:
        r = requests.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=5)
        if r.status_code == 200:
            asks = r.json().get("asks", [])
            free = int(float(asks[0][0])) // 10 if asks else 177400
        else:
            free = 183000
    except:
        free = 183000
    current = load_json(RATE_FILE, {})
    current["free"] = free
    current.setdefault("secondary", 140000)
    current["last_update"] = datetime.now().isoformat()
    save_json(RATE_FILE, current)

def scrape_billet_from_ahanmelal():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://ahanmelal.com/steel-ingots/steel-ingot-price", headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            table = soup.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        text = ' '.join(c.get_text() for c in cells)
                        for num in re.findall(r'(\d{1,3}(?:,\d{3})+)', text):
                            price = int(num.replace(',', ''))
                            if 40000 < price < 60000:
                                return price
    except Exception as e:
        print(f"خطای اسکرپر شمش: {e}")
    return None

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
                        for num in re.findall(r'(\d{1,3}(?:,\d{3})+)', text):
                            price = int(num.replace(',', ''))
                            if 50000 < price < 80000:
                                return price
    except Exception as e:
        print(f"خطای اسکرپر میلگرد: {e}")
    return None

def update_all_prices():
    current = load_json(PRICE_FILE, {
        "concentrate": 4800000, "pellet": 6500000,
        "dri": 14166, "billet": 42500, "rebar": 58000
    })
    billet = scrape_billet_from_ahanmelal()
    rebar = scrape_rebar_from_ahanmelal()
    if billet: current["billet"] = billet
    if rebar: current["rebar"] = rebar
    current["last_update"] = datetime.now().isoformat()
    save_json(PRICE_FILE, current)

def update_world_prices():
    print(f"[{datetime.now().strftime('%H:%M')}] بروزرسانی قیمت‌های جهانی...")

    # مقدار پیش‌فرض سنگ آهن 62% CFR چین
    iron_ore = 104.0
    source = "پیش‌فرض"

    # دریافت سنگ آهن از metalpriceapi
    if METALPRICE_API_KEY:
        try:
            r = requests.get("https://api.metalpriceapi.com/v1/latest", params={
                "api_key": METALPRICE_API_KEY, "base": "USD",
                "currencies": "IRON"
            }, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    rates = data.get("rates", {})
                    # USDIRON = قیمت مستقیم دلار/تن
                    if rates.get("USDIRON") and rates["USDIRON"] > 0:
                        iron_ore = round(rates["USDIRON"], 1)
                        source = "MetalpriceAPI"
                        print(f"سنگ آهن از API: ${iron_ore}/تن")
        except Exception as e:
            print(f"خطای API سنگ آهن: {e}")

    # ========== فرمول‌های محاسباتی بر اساس نسبت‌های تاریخی بازار ==========
    # کنسانتره سنگ آهن (62% Fe)
    con_north  = round(iron_ore, 1)                    # CFR شمال چین = قیمت پایه
    con_south  = round(iron_ore + 1, 1)                # CFR جنوب چین = شمال + 1$
    con_fob    = round(iron_ore - 19, 1)               # FOB خلیج فارس = شمال - 19$

    # گندله (ضریب تاریخی ≈ 1.49 برابر کنسانتره)
    pel_north  = round(con_north * 1.49, 1)
    pel_south  = round(con_south * 1.49, 1)
    pel_fob    = round(con_fob * 1.49, 1)

    # آهن اسفنجی DRI (ضریب ≈ 2.02 برابر گندله)
    dri_fob    = round(pel_fob * 2.02, 1)
    dri_north  = round(pel_north * 1.81, 1)
    dri_south  = round(pel_south * 1.81, 1)

    # شمش فولادی (ضریب ≈ 2.4 برابر آهن اسفنجی FOB)
    bil_fob    = round(dri_fob * 2.4, 1)
    bil_north  = round(bil_fob * 1.08, 1)
    bil_south  = round(bil_fob * 1.07, 1)

    # میلگرد (ضریب ≈ 1.15 برابر شمش)
    reb_fob    = round(bil_fob * 1.15, 1)
    reb_north  = round(bil_north * 1.15, 1)
    reb_south  = round(bil_south * 1.15, 1)

    world_prices = {
        "iron_ore_base": iron_ore,
        "concentrate_fob": con_fob,
        "concentrate_north": con_north,
        "concentrate_south": con_south,
        "pellet_fob": pel_fob,
        "pellet_north": pel_north,
        "pellet_south": pel_south,
        "dri_fob": dri_fob,
        "dri_north": dri_north,
        "dri_south": dri_south,
        "billet_fob": bil_fob,
        "billet_north": bil_north,
        "billet_south": bil_south,
        "rebar_fob": reb_fob,
        "rebar_north": reb_north,
        "rebar_south": reb_south,
        "last_update": datetime.now().isoformat(),
        "source": source
    }
    save_json(WORLD_PRICE_FILE, world_prices)
    print(f"[{datetime.now().strftime('%H:%M')}] قیمت جهانی کامل شد (پایه: ${iron_ore})")

def update_metals_prices():
    metals = load_json(METALS_FILE, {
        "gold": 4700, "silver": 33.5, "platinum": 2050,
        "palladium": 1480, "iron_ore": 105, "source": "پیش‌فرض"
    })
    if METALPRICE_API_KEY:
        try:
            r = requests.get("https://api.metalpriceapi.com/v1/latest", params={
                "api_key": METALPRICE_API_KEY, "base": "USD",
                "currencies": "XAU,XAG,XPT,XPD,IRON"
            }, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    rates = data.get("rates", {})
                    if rates.get("XAU"): metals["gold"] = round(1 / rates["XAU"], 2)
                    if rates.get("XAG"): metals["silver"] = round(1 / rates["XAG"], 2)
                    if rates.get("XPT"): metals["platinum"] = round(1 / rates["XPT"], 2)
                    if rates.get("XPD"): metals["palladium"] = round(1 / rates["XPD"], 2)
                    if rates.get("USDIRON"): metals["iron_ore"] = round(rates["USDIRON"], 2)
                    metals["source"] = "MetalpriceAPI"
        except Exception as e:
            print(f"خطای فلزات API: {e}")
    metals["last_update"] = datetime.now().isoformat()
    save_json(METALS_FILE, metals)

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
    _run_loop(update_rates, 15 * 60)
    _run_loop(update_all_prices, 6 * 60 * 60)
    _run_loop(update_world_prices, 6 * 60 * 60)
    _run_loop(update_metals_prices, 6 * 60 * 60)

# ========== لود داده ==========
def load_rates():
    return load_json(RATE_FILE, {"free": 183000, "secondary": 140000})

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
        "gold": 4700, "silver": 33.5, "platinum": 2050, "palladium": 1480, "iron_ore": 105
    })

# ========== کیبوردها ==========
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
    "• کنسانتره سنگ آهن\n• گندله\n• آهن اسفنجی\n"
    "• شمش فولادی\n• میلگرد\n• فلزات گران‌بها\n\n"
    "🔄 *بروزرسانی:* نرخ ارز هر ۱۵ دقیقه، قیمت‌ها هر ۶ ساعت\n\n"
    "لطفاً یکی از گزینه‌ها را انتخاب کنید:"
)

# ========== هندلرهای عمومی ==========
async def start(update, context):
    await update.message.reply_text(MAIN_TEXT, reply_markup=main_keyboard(), parse_mode="Markdown")

async def world(update, context):
    await update.callback_query.answer()
    p = load_world_prices()
    now = to_persian(datetime.now().strftime('%Y/%m/%d - %H:%M'))
    text = f"🌍 *قیمت‌های جهانی* 🌍\n🔄 {now}\n\n"
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
    text += f"\n📊 منبع: {p.get('source', 'MetalpriceAPI')}"
    text += f"\n🪨 پایه سنگ آهن ۶۲٪: *${p.get('iron_ore_base', 104)}*/تن"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

async def metals(update, context):
    await update.callback_query.answer()
    m = load_metals()
    now = to_persian(datetime.now().strftime('%Y/%m/%d - %H:%M'))
    text = f"💛 *فلزات گران‌بها* 💛\n🔄 {now}\n" + "━" * 30 + "\n\n"
    text += f"🥇 طلا (XAU):\n   *${format_float(m['gold'])}* / اونس تروی\n\n"
    text += f"🥈 نقره (XAG):\n   *${format_float(m['silver'])}* / اونس تروی\n\n"
    text += f"⚪️ پلاتین (XPT):\n   *${format_float(m['platinum'])}* / اونس تروی\n\n"
    text += f"🔘 پالادیوم (XPD):\n   *${format_float(m['palladium'])}* / اونس تروی\n\n"
    text += f"🪨 سنگ آهن (IRON):\n   *${format_float(m['iron_ore'])}* / تن\n"
    text += "\n" + "━" * 30 + "\n"
    text += f"📊 منبع: {m.get('source', 'MetalpriceAPI')}\n"
    text += "⚠️ داده‌ها با تاخیر ۲۴ ساعته (پلن رایگان)"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

async def ice(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🏭 *قیمت بورس کالا* 🏭\n" + "━" * 35 + "\n\n"
    text += f"🪨 کنسانتره:\n   *{format_number(p['concentrate'])}* تومان/تن\n\n"
    text += f"🟤 گندله:\n   *{format_number(p['pellet'])}* تومان/تن\n\n"
    text += f"🏭 آهن اسفنجی:\n   *{format_number(p['dri'])}* تومان/کیلو\n\n"
    text += f"🔩 شمش فولادی:\n   *{format_number(p['billet'])}* تومان/کیلو\n\n"
    text += f"📏 میلگرد:\n   *{format_number(p['rebar'])}* تومان/کیلو\n"
    text += "\n" + "━" * 35 + "\n"
    text += f"📅 بروزرسانی: {to_persian(p.get('last_update', '')[:16])}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

async def free(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🔄 *قیمت بازار آزاد ایران* 🔄\n" + "━" * 35 + "\n\n"
    text += f"🪨 کنسانتره:\n   *{format_number(p['concentrate']-200000)} - {format_number(p['concentrate']+200000)}* تومان/تن\n\n"
    text += f"🟤 گندله:\n   *{format_number(p['pellet']-300000)} - {format_number(p['pellet']+300000)}* تومان/تن\n\n"
    text += f"🏭 آهن اسفنجی:\n   *{format_number(p['dri']-500)} - {format_number(p['dri']+500)}* تومان/کیلو\n\n"
    text += f"🔩 شمش فولادی:\n   *{format_number(p['billet']-2000)} - {format_number(p['billet']+2000)}* تومان/کیلو\n\n"
    text += f"📏 میلگرد:\n   *{format_number(p['rebar']-3000)} - {format_number(p['rebar']+3000)}* تومان/کیلو\n"
    text += "\n" + "━" * 35 + "\n"
    text += f"📅 بروزرسانی: {to_persian(p.get('last_update', '')[:16])}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

async def factory(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🏭 *قیمت درب کارخانه* 🏭\n" + "━" * 35 + "\n\n"
    text += "🔩 *شمش فولادی (تومان/کیلو)*\n"
    text += f"   • فولاد اصفهان: *{format_number(p['billet'])}*\n"
    text += f"   • فولاد یزد: *{format_number(p['billet']-100)}*\n"
    text += f"   • فولاد قزوین: *{format_number(p['billet']-2000)}*\n\n"
    text += "📏 *میلگرد (تومان/کیلو)*\n"
    text += f"   • ذوب آهن اصفهان: *{format_number(p['rebar'])}*\n"
    text += f"   • امیرکبیر کاشان: *{format_number(p['rebar']+1000)}*\n"
    text += f"   • فولاد کاوه: *{format_number(p['rebar']-1000)}*\n\n"
    text += "🏭 *آهن اسفنجی (تومان/کیلو)*\n"
    text += f"   • فولاد میانه: *{format_number(p['dri']+600)}*\n"
    text += f"   • فولاد نطنز: *{format_number(p['dri']+400)}*\n"
    text += f"   • فولاد کاویان: *{format_number(p['dri']+200)}*\n\n"
    text += "🟤 *گندله (تومان/تن)*\n"
    text += f"   • گل گهر: *{format_number(p['pellet']-100000)}*\n"
    text += f"   • چادرملو: *{format_number(p['pellet']-200000)}*\n\n"
    text += "🪨 *کنسانتره (تومان/تن)*\n"
    text += f"   • گل گهر: *{format_number(p['concentrate']-500000)}*\n"
    text += f"   • سنگ آهن مرکزی: *{format_number(p['concentrate']-200000)}*\n"
    text += "\n" + "━" * 35 + "\n"
    text += f"📅 بروزرسانی: {to_persian(p.get('last_update', '')[:16])}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

async def rate(update, context):
    await update.callback_query.answer()
    rates = load_rates()
    text = "💱 *نرخ ارز بازار ایران* 💱\n" + "━" * 35 + "\n\n"
    text += f"🏦 نرخ نیمایی:\n   • دلار: *{format_number(rates['secondary'])}* تومان\n\n"
    text += f"🔄 بازار آزاد:\n   • دلار: *{format_number(rates['free'])}* تومان\n"
    text += "\n" + "━" * 35 + "\n"
    text += f"📅 بروزرسانی: {to_persian(rates.get('last_update', '')[:16])}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

async def back(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(MAIN_TEXT, reply_markup=main_keyboard(), parse_mode="Markdown")

# ========== پنل ادمین ==========
ADMIN_FIELDS = {
    "w_con_fob":   ("world", "concentrate_fob",  "کنسانتره FOB خلیج فارس ($/تن)"),
    "w_con_north": ("world", "concentrate_north", "کنسانتره CFR شمال چین ($/تن)"),
    "w_con_south": ("world", "concentrate_south", "کنسانتره CFR جنوب چین ($/تن)"),
    "w_pel_fob":   ("world", "pellet_fob",        "گندله FOB خلیج فارس ($/تن)"),
    "w_pel_north": ("world", "pellet_north",      "گندله CFR شمال چین ($/تن)"),
    "w_pel_south": ("world", "pellet_south",      "گندله CFR جنوب چین ($/تن)"),
    "w_dri_fob":   ("world", "dri_fob",           "آهن اسفنجی FOB ($/تن)"),
    "w_dri_north": ("world", "dri_north",         "آهن اسفنجی CFR شمال ($/تن)"),
    "w_dri_south": ("world", "dri_south",         "آهن اسفنجی CFR جنوب ($/تن)"),
    "w_bil_fob":   ("world", "billet_fob",        "شمش FOB ($/تن)"),
    "w_bil_north": ("world", "billet_north",      "شمش CFR شمال ($/تن)"),
    "w_bil_south": ("world", "billet_south",      "شمش CFR جنوب ($/تن)"),
    "w_reb_fob":   ("world", "rebar_fob",         "میلگرد FOB ($/تن)"),
    "w_reb_north": ("world", "rebar_north",       "میلگرد CFR شمال ($/تن)"),
    "w_reb_south": ("world", "rebar_south",       "میلگرد CFR جنوب ($/تن)"),
    "p_con":       ("price", "concentrate",       "کنسانتره بورس (تومان/تن)"),
    "p_pel":       ("price", "pellet",            "گندله بورس (تومان/تن)"),
    "p_dri":       ("price", "dri",               "آهن اسفنجی بورس (تومان/کیلو)"),
    "p_bil":       ("price", "billet",            "شمش بورس (تومان/کیلو)"),
    "p_reb":       ("price", "rebar",             "میلگرد بورس (تومان/کیلو)"),
    "r_free":      ("rate",  "free",              "دلار بازار آزاد (تومان)"),
    "r_sec":       ("rate",  "secondary",         "دلار نیمایی (تومان)"),
}

def get_current_value(field_key):
    ftype, key, _ = ADMIN_FIELDS[field_key]
    if ftype == "world": return load_world_prices().get(key, 0)
    elif ftype == "price": return load_prices().get(key, 0)
    elif ftype == "rate": return load_rates().get(key, 0)

def set_value(field_key, value):
    ftype, key, _ = ADMIN_FIELDS[field_key]
    if ftype == "world":
        data = load_world_prices(); data[key] = value
        data["last_update"] = datetime.now().isoformat()
        save_json(WORLD_PRICE_FILE, data)
    elif ftype == "price":
        data = load_prices(); data[key] = value
        data["last_update"] = datetime.now().isoformat()
        save_json(PRICE_FILE, data)
    elif ftype == "rate":
        data = load_rates(); data[key] = value
        data["last_update"] = datetime.now().isoformat()
        save_json(RATE_FILE, data)

def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 قیمت‌های جهانی", callback_data="adm_world")],
        [InlineKeyboardButton("🏭 قیمت‌های داخلی", callback_data="adm_domestic")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="adm_rate")],
        [InlineKeyboardButton("🔄 آپدیت خودکار همه", callback_data="adm_refresh")],
        [InlineKeyboardButton("❌ خروج", callback_data="adm_exit")]
    ])

def world_prices_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("کنسانتره FOB", callback_data="edit_w_con_fob"),
         InlineKeyboardButton("شمال", callback_data="edit_w_con_north"),
         InlineKeyboardButton("جنوب", callback_data="edit_w_con_south")],
        [InlineKeyboardButton("گندله FOB", callback_data="edit_w_pel_fob"),
         InlineKeyboardButton("شمال", callback_data="edit_w_pel_north"),
         InlineKeyboardButton("جنوب", callback_data="edit_w_pel_south")],
        [InlineKeyboardButton("DRI FOB", callback_data="edit_w_dri_fob"),
         InlineKeyboardButton("شمال", callback_data="edit_w_dri_north"),
         InlineKeyboardButton("جنوب", callback_data="edit_w_dri_south")],
        [InlineKeyboardButton("شمش FOB", callback_data="edit_w_bil_fob"),
         InlineKeyboardButton("شمال", callback_data="edit_w_bil_north"),
         InlineKeyboardButton("جنوب", callback_data="edit_w_bil_south")],
        [InlineKeyboardButton("میلگرد FOB", callback_data="edit_w_reb_fob"),
         InlineKeyboardButton("شمال", callback_data="edit_w_reb_north"),
         InlineKeyboardButton("جنوب", callback_data="edit_w_reb_south")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back")]
    ])

def domestic_prices_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("کنسانتره", callback_data="edit_p_con"),
         InlineKeyboardButton("گندله", callback_data="edit_p_pel")],
        [InlineKeyboardButton("آهن اسفنجی", callback_data="edit_p_dri"),
         InlineKeyboardButton("شمش", callback_data="edit_p_bil")],
        [InlineKeyboardButton("میلگرد", callback_data="edit_p_reb")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back")]
    ])

def rate_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("دلار آزاد", callback_data="edit_r_free"),
         InlineKeyboardButton("دلار نیمایی", callback_data="edit_r_sec")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back")]
    ])

async def admin_panel(update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔️ دسترسی ندارید.")
        return ConversationHandler.END
    await update.message.reply_text(
        "🔐 *پنل مدیریت*\n\nکدام بخش را می‌خواهید ویرایش کنید؟",
        reply_markup=admin_main_keyboard(), parse_mode="Markdown"
    )
    return WAITING_VALUE

async def admin_callback(update, context):
    if not is_admin(update):
        await update.callback_query.answer("⛔️ دسترسی ندارید.")
        return WAITING_VALUE

    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "adm_world":
        p = load_world_prices()
        text = "🌍 *ویرایش قیمت‌های جهانی*\n\n"
        text += f"کنسانتره: FOB={p['concentrate_fob']}$ | شمال={p['concentrate_north']}$ | جنوب={p['concentrate_south']}$\n"
        text += f"گندله: FOB={p['pellet_fob']}$ | شمال={p['pellet_north']}$ | جنوب={p['pellet_south']}$\n"
        text += f"DRI: FOB={p['dri_fob']}$ | شمال={p['dri_north']}$ | جنوب={p['dri_south']}$\n"
        text += f"شمش: FOB={p['billet_fob']}$ | شمال={p['billet_north']}$ | جنوب={p['billet_south']}$\n"
        text += f"میلگرد: FOB={p['rebar_fob']}$ | شمال={p['rebar_north']}$ | جنوب={p['rebar_south']}$\n"
        await query.edit_message_text(text, reply_markup=world_prices_keyboard(), parse_mode="Markdown")

    elif data == "adm_domestic":
        p = load_prices()
        text = "🏭 *ویرایش قیمت‌های داخلی*\n\n"
        text += f"کنسانتره: {p['concentrate']:,} ت/تن\n"
        text += f"گندله: {p['pellet']:,} ت/تن\n"
        text += f"آهن اسفنجی: {p['dri']:,} ت/کیلو\n"
        text += f"شمش: {p['billet']:,} ت/کیلو\n"
        text += f"میلگرد: {p['rebar']:,} ت/کیلو\n"
        await query.edit_message_text(text, reply_markup=domestic_prices_keyboard(), parse_mode="Markdown")

    elif data == "adm_rate":
        r = load_rates()
        text = "💱 *ویرایش نرخ ارز*\n\n"
        text += f"دلار آزاد: {r['free']:,} تومان\n"
        text += f"دلار نیمایی: {r['secondary']:,} تومان\n"
        await query.edit_message_text(text, reply_markup=rate_keyboard(), parse_mode="Markdown")

    elif data == "adm_refresh":
        await query.edit_message_text("🔄 در حال بروزرسانی خودکار...")
        threading.Thread(target=lambda: (
            update_rates(), update_all_prices(),
            update_world_prices(), update_metals_prices()
        ), daemon=True).start()
        await query.edit_message_text("✅ بروزرسانی خودکار انجام شد.", reply_markup=admin_main_keyboard())

    elif data == "adm_back":
        await query.edit_message_text(
            "🔐 *پنل مدیریت*\n\nکدام بخش را می‌خواهید ویرایش کنید؟",
            reply_markup=admin_main_keyboard(), parse_mode="Markdown"
        )

    elif data == "adm_exit":
        await query.edit_message_text("✅ از پنل مدیریت خارج شدید.")
        return ConversationHandler.END

    elif data.startswith("edit_"):
        field_key = data[5:]
        if field_key in ADMIN_FIELDS:
            _, _, label = ADMIN_FIELDS[field_key]
            current = get_current_value(field_key)
            context.user_data["editing_field"] = field_key
            await query.edit_message_text(
                f"✏️ *ویرایش: {label}*\n\n"
                f"مقدار فعلی: *{current:,}*\n\n"
                f"عدد جدید را وارد کنید:",
                parse_mode="Markdown"
            )

    return WAITING_VALUE

async def receive_value(update, context):
    if not is_admin(update):
        return WAITING_VALUE

    field_key = context.user_data.get("editing_field")
    if not field_key:
        return WAITING_VALUE

    text = update.message.text.strip().replace(",", "").replace("،", "")
    fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    text = text.translate(fa_to_en)

    try:
        value = float(text)
        set_value(field_key, value)
        _, _, label = ADMIN_FIELDS[field_key]
        context.user_data["editing_field"] = None
        await update.message.reply_text(
            f"✅ *{label}*\nبه *{value:,}* بروزرسانی شد.",
            reply_markup=admin_main_keyboard(),
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ عدد نامعتبر. دوباره وارد کنید:")

    return WAITING_VALUE

# ========== دریافت قیمت از اسکرپر (push از کامپیوتر) ==========
SCRAPER_SECRET = os.environ.get("SCRAPER_SECRET", "change_this_secret")

async def push_prices(update, context):
    """دستور مخفی برای دریافت قیمت از اسکرپر محلی"""
    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text("❌ فرمت اشتباه.")
        return

    try:
        # فرمت: /push_prices SECRET {"key": value, ...}
        if context.args[0] != SCRAPER_SECRET:
            await update.message.reply_text("❌ کلید اشتباه.")
            return

        raw = " ".join(context.args[1:])
        data = json.loads(raw)

        updated = []

        # قیمت‌های داخلی
        if "domestic" in data:
            d = load_prices()
            d.update(data["domestic"])
            d["last_update"] = datetime.now().isoformat()
            save_json(PRICE_FILE, d)
            updated.append("قیمت داخلی ✅")

        # قیمت‌های جهانی
        if "world" in data:
            w = load_world_prices()
            w.update(data["world"])
            w["last_update"] = datetime.now().isoformat()
            w["source"] = "markazeahan/اسکرپر"
            save_json(WORLD_PRICE_FILE, w)
            updated.append("قیمت جهانی ✅")

        # نرخ ارز
        if "rates" in data:
            r = load_rates()
            r.update(data["rates"])
            r["last_update"] = datetime.now().isoformat()
            save_json(RATE_FILE, r)
            updated.append("نرخ ارز ✅")

        msg = "📥 *قیمت‌ها از اسکرپر دریافت شد:*\n" + "\n".join(updated)
        await update.message.reply_text(msg, parse_mode="Markdown")

    except json.JSONDecodeError:
        await update.message.reply_text("❌ JSON نامعتبر.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")

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
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_value)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("push_prices", push_prices))
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
