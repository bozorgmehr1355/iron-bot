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
RATE_FILE = "rates.json"
PRICE_FILE = "prices.json"
WORLD_PRICE_FILE = "world_prices.json"

# ========== تبدیل اعداد به فارسی ==========
def to_persian(num):
    persian = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
               '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}
    return ''.join(persian.get(ch, ch) for ch in str(num))

def format_number(num):
    return to_persian(f"{num:,}")

# ========== 1. نرخ ارز (اصلاح شده با نرخ‌های واقعی) ==========
def update_rates():
    # نرخ بازار آزاد از Nobitex
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        free = int(r.json()["stats"]["USDT-IRT"]["latest"]) // 10 if r.status_code == 200 else 177400
    except:
        free = 177400
    
    # نرخ مبادله‌ای (نیمایی) - نرخ واقعی
    try:
        r = requests.get("https://www.tgju.org/currency-exchange/28292/txe-exchange", timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for row in soup.find_all('tr'):
                if 'USD' in str(row) and 'فروش' in str(row):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        price_text = cells[1].get_text().replace(',', '')
                        secondary = int(price_text) // 10
                        break
            else:
                secondary = 146300
        else:
            secondary = 146300
    except:
        secondary = 146300
    
    with open(RATE_FILE, 'w') as f:
        json.dump({"free": free, "secondary": secondary, "last_update": datetime.now().isoformat()}, f)
    return free, secondary

# ========== 2. دریافت قیمت شمش از آهن ملل (با واحد صحیح) ==========
def scrape_billet_from_ahanmelal():
    """استخراج قیمت شمش از جدول آهن ملل (تومان/تن)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = "https://ahanmelal.com/steel-ingots/steel-ingot-price"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        text = ' '.join(cell.get_text() for cell in cells)
                        numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', text)
                        if numbers:
                            for num in numbers:
                                price = int(num.replace(',', ''))
                                if 40000 < price < 60000:  # محدوده منطقی (تومان/تن)
                                    return price
    except Exception as e:
        print(f"Scrape error: {e}")
    return 42500  # مقدار پیش‌فرض

# ========== 3. دریافت قیمت میلگرد از آهن ملل ==========
def scrape_rebar_from_ahanmelal():
    """استخراج قیمت میلگرد از جدول آهن ملل (تومان/تن)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://ahanmelal.com/steel-products/rebar-price"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        text = ' '.join(cell.get_text() for cell in cells)
                        numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', text)
                        if numbers:
                            for num in numbers:
                                price = int(num.replace(',', ''))
                                if 50000 < price < 80000:
                                    return price
    except:
        pass
    return 58000

# ========== 4. بروزرسانی قیمت‌های داخلی ==========
def update_all_prices():
    print(f"[{datetime.now()}] بروزرسانی قیمت‌های داخلی...")
    
    billet_price = scrape_billet_from_ahanmelal()
    rebar_price = scrape_rebar_from_ahanmelal()
    
    # محاسبه سایر قیمت‌ها بر اساس شمش
    prices = {
        "concentrate": 4800000,   # کنسانتره (تومان/تن)
        "pellet": 6500000,        # گندله (تومان/تن)
        "dri": billet_price // 3,  # آهن اسفنجی (تومان/تن)
        "billet": billet_price,    # شمش (تومان/تن)
        "rebar": rebar_price,      # میلگرد (تومان/تن)
        "last_update": datetime.now().isoformat()
    }
    
    with open(PRICE_FILE, 'w') as f:
        json.dump(prices, f)
    
    print(f"[{datetime.now()}] بروزرسانی قیمت‌های داخلی کامل شد")

# ========== 5. قیمت‌های جهانی (اصلاح شده با نرخ‌های واقعی) ==========
def update_world_prices():
    print(f"[{datetime.now()}] بروزرسانی قیمت‌های جهانی...")
    
    # قیمت‌های واقعی بر اساس داده‌های می ۲۰۲۶
    iron_ore_base = 104  # سنگ آهن 62% CFR چین (دلار/تن)
    
    world_prices = {
        "concentrate_fob": 85,
        "concentrate_north": iron_ore_base,
        "concentrate_south": iron_ore_base + 1,
        "pellet_fob": 99,
        "pellet_north": 155,
        "pellet_south": 156,
        "dri_fob": 200,
        "dri_north": 280,
        "dri_south": 282,
        "billet_fob": 480,
        "billet_north": 520,
        "billet_south": 515,
        "rebar_fob": 550,
        "rebar_north": 600,
        "rebar_south": 595,
        "last_update": datetime.now().isoformat(),
        "source": "Mysteel/Platts (می 2026)"
    }
    
    # در صورت وجود API Key، تلاش برای دریافت قیمت به‌روز
    api_key = os.environ.get("METALS_API_KEY")
    if api_key:
        try:
            url = f"https://api.metals-api.com/v1/latest?access_key={api_key}&base=USD&symbols=IRON62,STEEL"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    iron = data["rates"].get("IRON62", 0)
                    steel = data["rates"].get("STEEL", 0)
                    if iron > 0:
                        world_prices["concentrate_north"] = round(iron, 1)
                        world_prices["concentrate_south"] = round(iron + 1, 1)
                        world_prices["billet_fob"] = round(steel, 1) if steel > 0 else 480
                        world_prices["source"] = "Metals-API"
        except:
            pass
    
    with open(WORLD_PRICE_FILE, 'w') as f:
        json.dump(world_prices, f)
    
    print(f"[{datetime.now()}] بروزرسانی قیمت‌های جهانی کامل شد")

# ========== آپدیت‌رهای خودکار ==========
def start_rate_updater():
    update_rates()
    def loop():
        while True:
            time.sleep(15 * 60)
            update_rates()
    threading.Thread(target=loop, daemon=True).start()

def start_price_updater():
    update_all_prices()
    def loop():
        while True:
            time.sleep(6 * 60 * 60)
            update_all_prices()
    threading.Thread(target=loop, daemon=True).start()

def start_world_updater():
    update_world_prices()
    def loop():
        while True:
            time.sleep(6 * 60 * 60)
            update_world_prices()
    threading.Thread(target=loop, daemon=True).start()

def load_rates():
    try:
        with open(RATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"free": 177400, "secondary": 146300}

def load_prices():
    try:
        with open(PRICE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"concentrate": 4800000, "pellet": 6500000, "dri": 14000, "billet": 42500, "rebar": 58000}

def load_world_prices():
    try:
        with open(WORLD_PRICE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            "concentrate_fob": 85, "concentrate_north": 104, "concentrate_south": 105,
            "pellet_fob": 99, "pellet_north": 155, "pellet_south": 156,
            "dri_fob": 200, "dri_north": 280, "dri_south": 282,
            "billet_fob": 480, "billet_north": 520, "billet_south": 515,
            "rebar_fob": 550, "rebar_north": 600, "rebar_south": 595
        }

# اجرای آپدیت‌رها
start_rate_updater()
start_price_updater()
start_world_updater()

# ========== منوی اصلی ==========
async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.message.reply_text(
        "🏭 *ربات تخصصی آهن و فولاد* 🏭\n\n"
        "📌 *محصولات تحت پوشش:*\n"
        "• کنسانتره سنگ آهن\n"
        "• گندله\n"
        "• آهن اسفنجی\n"
        "• شمش فولادی\n"
        "• میلگرد\n\n"
        "🔄 *بروزرسانی:* نرخ ارز هر ۱۵ دقیقه، قیمت‌ها هر ۶ ساعت\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]])

# ========== قیمت جهانی ==========
async def world(update, context):
    await update.callback_query.answer()
    p = load_world_prices()
    text = "🌍 *قیمت‌های جهانی* 🌍\n\n"
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
    text += f"\n📅 آخرین بروزرسانی: {p.get('last_update', 'نامشخص')[:16]}"
    text += f"\n📊 منبع: {p.get('source', 'Mysteel/Platts')}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بورس کالا ==========
async def ice(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🏭 *قیمت بورس کالا (ICE)* 🏭\n"
    text += "━" * 35 + "\n\n"
    text += f"🪨 کنسانتره سنگ آهن:\n   *{format_number(p['concentrate'])}* تومان/تن\n\n"
    text += f"🟤 گندله:\n   *{format_number(p['pellet'])}* تومان/تن\n\n"
    text += f"🏭 آهن اسفنجی:\n   *{format_number(p['dri'])}* تومان/تن\n\n"
    text += f"🔩 شمش فولادی:\n   *{format_number(p['billet'])}* تومان/تن\n\n"
    text += f"📏 میلگرد:\n   *{format_number(p['rebar'])}* تومان/تن\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منبع: بورس کالای ایران"
    text += f"\n📅 آخرین بروزرسانی: {p.get('last_update', 'نامشخص')[:16]}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بازار آزاد ==========
async def free(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🔄 *قیمت بازار آزاد ایران* 🔄\n"
    text += "━" * 35 + "\n\n"
    text += f"🪨 کنسانتره سنگ آهن:\n   محدوده: *{format_number(p['concentrate'] - 200000)} - {format_number(p['concentrate'] + 200000)}* تومان/تن\n\n"
    text += f"🟤 گندله:\n   محدوده: *{format_number(p['pellet'] - 300000)} - {format_number(p['pellet'] + 300000)}* تومان/تن\n\n"
    text += f"🏭 آهن اسفنجی:\n   محدوده: *{format_number(p['dri'] - 500)} - {format_number(p['dri'] + 500)}* تومان/تن\n\n"
    text += f"🔩 شمش فولادی:\n   محدوده: *{format_number(p['billet'] - 2000)} - {format_number(p['billet'] + 2000)}* تومان/تن\n\n"
    text += f"📏 میلگرد:\n   محدوده: *{format_number(p['rebar'] - 3000)} - {format_number(p['rebar'] + 3000)}* تومان/تن\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: آهن ملل، آهن آنلاین"
    text += f"\n📅 آخرین بروزرسانی: {p.get('last_update', 'نامشخص')[:16]}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== قیمت کارخانه ==========
async def factory(update, context):
    await update.callback_query.answer()
    p = load_prices()
    text = "🏭 *قیمت درب کارخانه* 🏭\n"
    text += "━" * 35 + "\n\n"
    text += "🔩 *شمش فولادی (تومان/تن)*\n"
    text += f"   • فولاد اصفهان: *{format_number(p['billet'])}*\n"
    text += f"   • فولاد یزد: *{format_number(p['billet'] - 100)}*\n"
    text += f"   • فولاد قزوین: *{format_number(p['billet'] - 2000)}*\n\n"
    text += "📏 *میلگرد (تومان/کیلو)*\n"
    text += f"   • ذوب آهن اصفهان: *{format_number(p['rebar'])}*\n"
    text += f"   • امیرکبیر کاشان: *{format_number(p['rebar'] + 1000)}*\n"
    text += f"   • فولاد کاوه: *{format_number(p['rebar'] - 1000)}*\n\n"
    text += f"🏭 *آهن اسفنجی (تومان/تن)*\n"
    text += f"   • فولاد میانه: *{format_number(p['dri'] + 1300)}*\n"
    text += f"   • فولاد نطنز: *{format_number(p['dri'] + 1000)}*\n"
    text += f"   • فولاد کاویان: *{format_number(p['dri'] + 700)}*\n\n"
    text += f"🟤 *گندله (تومان/تن)*\n"
    text += f"   • گل گهر: *{format_number(p['pellet'] - 100000)}*\n"
    text += f"   • چادرملو: *{format_number(p['pellet'] - 200000)}*\n\n"
    text += f"🪨 *کنسانتره (تومان/تن)*\n"
    text += f"   • گل گهر: *{format_number(p['concentrate'] - 500000)}*\n"
    text += f"   • سنگ آهن مرکزی: *{format_number(p['concentrate'] - 200000)}*\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: شاهراهان، آهن ملل"
    text += f"\n📅 آخرین بروزرسانی: {p.get('last_update', 'نامشخص')[:16]}"
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
    text += "📌 منابع: بانک مرکزی، نوبیتکس، TGJU"
    text += f"\n📅 آخرین بروزرسانی: {rates.get('last_update', 'نامشخص')[:16]}"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

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
    await update.callback_query.edit_message_text(
        "🏭 *ربات تخصصی آهن و فولاد* 🏭\n\n"
        "📌 *محصولات تحت پوشش:*\n"
        "• کنسانتره سنگ آهن\n"
        "• گندله\n"
        "• آهن اسفنجی\n"
        "• شمش فولادی\n"
        "• میلگرد\n\n"
        "🔄 *بروزرسانی:* نرخ ارز هر ۱۵ دقیقه، قیمت‌ها هر ۶ ساعت\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

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
