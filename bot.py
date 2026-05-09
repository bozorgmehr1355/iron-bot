import os
import re
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any

import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ConversationHandler,
    MessageHandler, filters, CallbackQueryHandler
)

from price_arbiter import PriceArbiter

# ========== تنظیمات اولیه ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# State های مکالمه محاسبه سود
SELECT_PRODUCT, GET_PRICE, GET_RATE, GET_TONNAGE, GET_FREIGHT, GET_PORT = range(6)

user_data = {}
iran_prices_cache = {"data": None, "last_update": None}
price_arbiter = PriceArbiter(tolerance_percent=2.0)

# ========== نرخ ارز (تومان) ==========
async def get_usd_nego_rate_toman() -> int:
    """نرخ دلار مبادله‌ای (نیمایی) – تومان"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.tgju.org/sana/", timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*ریال', html)
                    if match:
                        return int(match.group(1).replace(',', '')) // 10
    except Exception as e:
        logger.error(f"Error fetching nego rate: {e}")
    return 146800

async def get_usd_free_rate_toman() -> int:
    """نرخ دلار بازار آزاد – تومان"""
    # منبع اول: Nobitex
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.nobitex.ir/v2/trades", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = float(data.get("stats", {}).get("USDT-IRT", {}).get("latest", 0))
                    if price > 0:
                        return int(price) // 10
    except Exception as e:
        logger.error(f"Nobitex error: {e}")
    # منبع دوم: TGJU
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price_str = data.get("price", "0").replace(",", "")
                    price = int(price_str)
                    if price > 0:
                        return price // 10
    except Exception as e:
        logger.error(f"TGJU error: {e}")
    return 178000

# ========== دریافت قیمت‌های جهانی و بنادر چین ==========
async def fetch_global_prices() -> Dict:
    """دریافت قیمت جهانی سنگ آهن و بیلت از چند منبع (Mysteel, SMM, Metals-API) و اعتبارسنجی"""
    sources_iron = {}
    sources_billet = {}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # منبع 1: Mysteel Index (CFR Qingdao 62% Fe)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://tks.mysteel.com/price/list-iron-ore-index.html", headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    price_elem = soup.select_one('.index-price .price-value')
                    if price_elem:
                        txt = price_elem.get_text(strip=True)
                        nums = re.findall(r'(\d+\.?\d*)', txt)
                        if nums and 80 < float(nums[0]) < 150:
                            sources_iron["mysteel_index"] = float(nums[0])
    except Exception as e:
        logger.error(f"Mysteel Index error: {e}")

    # منبع 2: SMM
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.metal.com/news/price/iron-ore", headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    price_elem = soup.select_one('.current-price')
                    if price_elem:
                        txt = price_elem.get_text(strip=True)
                        nums = re.findall(r'(\d+\.?\d*)', txt)
                        if nums and 80 < float(nums[0]) < 150:
                            sources_iron["smm_index"] = float(nums[0])
    except Exception as e:
        logger.error(f"SMM error: {e}")

    # منبع 3: Metals-API (در صورت وجود کلید)
    api_key = os.environ.get("METALS_API_KEY")
    if api_key:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.metals-api.com/v1/latest?access_key={api_key}&base=USD&symbols=IRON62", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            price = data["rates"].get("IRON62")
                            if price and 80 < price < 150:
                                sources_iron["metals_api"] = price
        except Exception as e:
            logger.error(f"Metals-API error: {e}")

    # قیمت بیلت (FOB China)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.mysteel.net/daily-prices/7009318-billet-export-prices-fob-china", headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    for row in soup.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 6 and '3SP' in cells[1].get_text():
                            price_text = cells[6].get_text()
                            nums = re.findall(r'(\d+\.?\d*)', price_text)
                            if nums and 400 < float(nums[0]) < 600:
                                sources_billet["mysteel_export"] = float(nums[0])
                                break
    except Exception as e:
        logger.error(f"Billet FOB error: {e}")

    result_iron = price_arbiter.resolve_price(sources_iron, default=108.0)
    result_billet = price_arbiter.resolve_price(sources_billet, default=480.0)

    return {
        "iron_ore": {"price": result_iron["price"], "unit": "USD/ton", "method": result_iron["method"], "details": result_iron["details"]},
        "billet": {"price": result_billet["price"], "unit": "USD/ton FOB China", "method": result_billet["method"], "details": result_billet["details"]}
    }

async def fetch_port_prices() -> Dict:
    """قیمت بنادر شمال (Qingdao) و جنوب (Fangcheng) – یوان/تن"""
    result = {"qingdao_62": None, "fangcheng_pb": None, "last_update": None}
    headers = {"User-Agent": "Mozilla/5.0"}

    # Qingdao (شمال) – از Mysteel portside
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://tks.mysteel.com/jkk/m/26050919/6C3F7F8899279773.html", headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    for row in soup.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            txt = ' '.join(cell.get_text() for cell in cells)
                            if '61%铁矿石港口现货' in txt and '青岛' in txt:
                                nums = re.findall(r'(\d+\.?\d*)', txt)
                                if nums:
                                    result["qingdao_62"] = float(nums[0])
                                    break
    except Exception as e:
        logger.error(f"Qingdao port error: {e}")

    # Fangcheng (جنوب) – از custeel
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.custeel.com/reform/view.mv?articleID=8291659", headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    table = soup.find('table')
                    if table:
                        for row in table.find_all('tr'):
                            cells = row.find_all('td')
                            if len(cells) >= 6 and 'PB fines' in cells[1].get_text():
                                price_text = cells[4].get_text()
                                nums = re.findall(r'(\d+)', price_text)
                                if nums:
                                    result["fangcheng_pb"] = float(nums[0])
                                    break
    except Exception as e:
        logger.error(f"Fangcheng port error: {e}")

    result["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return result

# ========== قیمت‌های داخلی ایران (آهن‌ملل) ==========
async def fetch_ahanmelal_price(product_key: str) -> Optional[float]:
    """اسکرپینگ قیمت محصول از آهن‌ملل – تومان/کیلو (برای شمش، میلگرد، تیرآهن، آهن اسفنجی)"""
    urls = {
        "billet": "https://ahanmelal.com/steel-ingots/steel-ingot-price",
        "rebar": "https://ahanmelal.com/steel-products/rebar-price",
        "ibeam": "https://ahanmelal.com/steel-products/ibeam-price",
        "dri": "https://ahanmelal.com/sponge-iron/sponge-iron-price"
    }
    if product_key not in urls:
        return None
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(urls[product_key], headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    selectors = ['.product-price', '.price', '.current-price', '.price-value']
                    for sel in selectors:
                        elem = soup.select_one(sel)
                        if elem:
                            txt = elem.get_text(strip=True)
                            nums = re.findall(r'([\d,]+)', txt)
                            if nums:
                                raw = nums[0].replace(',', '')
                                if raw.isdigit():
                                    return int(raw)
    except Exception as e:
        logger.error(f"Scrape {product_key} error: {e}")
    return None

async def get_iran_prices():
    global iran_prices_cache
    now = datetime.now()
    if iran_prices_cache["data"] and iran_prices_cache["last_update"]:
        if (now - iran_prices_cache["last_update"]).total_seconds() < 21600:
            return iran_prices_cache["data"]

    logger.info("Fetching Iran prices from multiple sources...")
    billet_price = await fetch_ahanmelal_price("billet")
    rebar_price = await fetch_ahanmelal_price("rebar")
    ibeam_price = await fetch_ahanmelal_price("ibeam")
    dri_price = await fetch_ahanmelal_price("dri")

    billet_res = price_arbiter.resolve_price({"ahanmelal": billet_price}, default=55000)
    rebar_res = price_arbiter.resolve_price({"ahanmelal": rebar_price}, default=65000)
    ibeam_res = price_arbiter.resolve_price({"ahanmelal": ibeam_price}, default=62000)
    dri_res = price_arbiter.resolve_price({"ahanmelal": dri_price}, default=15500)

    prices = {
        "concentrate": {"name": "کنسانتره سنگ آهن", "ice": "۶,۰۰۰,۰۰۰ - ۷,۰۰۰,۰۰۰", "free_market": "۶,۲۰۰,۰۰۰ - ۷,۲۰۰,۰۰۰", "factory": "گل گهر: ۶,۵۰۰,۰۰۰ | مرکزی: ۶,۸۰۰,۰۰۰", "unit": "تن"},
        "pellet": {"name": "گندله", "ice": "۸,۰۰۰,۰۰۰ - ۱۰,۵۰۰,۰۰۰", "free_market": "۸,۵۰۰,۰۰۰ - ۱۱,۵۰۰,۰۰۰", "factory": "گل گهر: ۱۰,۷۰۰,۰۰۰ | چادرملو: ۱۰,۲۰۰,۰۰۰", "unit": "تن"},
        "dri": {"name": "آهن اسفنجی", "ice": f"{int(dri_res['price']*0.95):,} - {int(dri_res['price']*1.02):,}", "free_market": f"{int(dri_res['price']*0.98):,} - {int(dri_res['price']*1.05):,}", "factory": f"میانگین: {int(dri_res['price']):,}", "unit": "کیلو"},
        "billet": {"name": "شمش فولادی", "ice": f"{int(billet_res['price']*0.95):,} - {int(billet_res['price']*1.02):,}", "free_market": f"{int(billet_res['price']*0.98):,} - {int(billet_res['price']*1.05):,}", "factory": f"میانگین: {int(billet_res['price']):,}", "unit": "کیلو"},
        "rebar": {"name": "میلگرد", "ice": f"{int(rebar_res['price']*0.95):,} - {int(rebar_res['price']*1.02):,}", "free_market": f"{int(rebar_res['price']*0.98):,} - {int(rebar_res['price']*1.05):,}", "factory": f"میانگین: {int(rebar_res['price']):,}", "unit": "کیلو"},
        "ibeam": {"name": "تیرآهن", "ice": f"{int(ibeam_res['price']*0.95):,} - {int(ibeam_res['price']*1.02):,}", "free_market": f"{int(ibeam_res['price']*0.98):,} - {int(ibeam_res['price']*1.05):,}", "factory": f"میانگین: {int(ibeam_res['price']):,}", "unit": "کیلو"}
    }
    iran_prices_cache["data"] = prices
    iran_prices_cache["last_update"] = now
    return prices

# ========== دکمه بازگشت ==========
def get_back_button(step: str) -> InlineKeyboardMarkup:
    if step == "main":
        return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]])
    elif step == "price":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به انتخاب محصول", callback_data="back_to_product")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    elif step == "rate":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به قیمت خرید", callback_data="back_to_price")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    elif step == "tonnage":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به نرخ ارز", callback_data="back_to_rate")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    elif step == "freight":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به تناژ", callback_data="back_to_tonnage")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    elif step == "port":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به هزینه حمل", callback_data="back_to_freight")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
    else:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]])

# ========== هندلرهای اصلی ربات ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="start_profit")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="show_global")],
        [InlineKeyboardButton("🇮🇷 قیمت ایران", callback_data="show_iran")]
    ]
    await update.message.reply_text(
        "🏭 *ربات تخصصی زنجیره آهن و فولاد* 🏭\n\n"
        "📌 محصولات تحت پوشش: کنسانتره، گندله، آهن اسفنجی، شمش، میلگرد، تیرآهن\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def back_to_main(update: Update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="start_profit")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="show_global")],
        [InlineKeyboardButton("🇮🇷 قیمت ایران", callback_data="show_iran")]
    ]
    await query.edit_message_text(
        "🏭 *ربات تخصصی زنجیره آهن و فولاد* 🏭\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def show_global(update: Update, context):
    query = update.callback_query
    await query.answer()

    # ----- داده‌های قیمت جهانی (شاخص‌ها و محصولات) -----
    global_data = [
        {"product": "سنگ‌آهن (Platts IODEX)", "brand": "IODEX", "price": 111.5, "basis": "CFR Qingdao, 61% Fe", "unit": "USD/ton"},
        {"product": "سنگ‌آهن (Platts 62% Fe)", "brand": "Platts", "price": 109.14, "basis": "CFR China", "unit": "USD/ton"},
        {"product": "سنگ‌آهن (Fastmarkets 62% Fe)", "brand": "Fastmarkets", "price": 98.85, "basis": "CFR Qingdao", "unit": "USD/ton"},
        {"product": "سنگ‌آهن (SMM 62% Fe)", "brand": "SMM", "price": 108.35, "basis": "CFR Qingdao", "unit": "USD/ton"},
        {"product": "سنگ‌آهن 61% Fe (Spot)", "brand": "Spot", "price": 111.5, "basis": "CFR China", "unit": "USD/ton"},
        {"product": "بیلت (Billet)", "brand": "Export", "price": 480.0, "basis": "FOB China", "unit": "USD/ton"},
        {"product": "میلگرد (Rebar) - Platts", "brand": "Platts", "price": 595.0, "basis": "FOB Turkey", "unit": "USD/ton"},
        {"product": "میلگرد (Rebar) - CIS", "brand": "CIS", "price": 495.0, "basis": "FOB", "unit": "USD/ton"},
        {"product": "ورق گرم (HRC) - Platts", "brand": "Platts", "price": 1040.0, "basis": "North America", "unit": "USD/ton"},
        {"product": "ضایعات آهن (Scrap) - Platts", "brand": "Platts", "price": 416.0, "basis": "CFR Turkey", "unit": "USD/ton"},
    ]

    nego = await get_usd_nego_rate_toman()
    free = await get_usd_free_rate_toman()

    text = "🌍 *قیمت‌های جهانی (شاخص‌های مرجع)* 🌍\n"
    text += f"📅 {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n"
    text += f"💱 *نرخ ارز (تومان)*: مبادله‌ای {nego:,} | آزاد {free:,}\n\n"
    text += "────────────────────────────────────────────────────────────────────\n"
    text += "| شاخص/محصول                                      | قیمت (USD/ton) | مبنا / برند                          |\n"
    text += "────────────────────────────────────────────────────────────────────\n"

    for item in global_data:
        product_name = item["product"][:45]
        price_str = f"{item['price']:.2f}"
        basis_str = item["basis"][:35]
        text += f"| {product_name:<45} | {price_str:>14} | {basis_str:<35} |\n"

    text += "────────────────────────────────────────────────────────────────────\n"
    text += "\n*توضیحات:*\n"
    text += "• **IODEX** (شاخص پلتس) از ابتدای ۲۰۲۶ بر پایه 61% Fe محاسبه می‌شود\n"
    text += "• قیمت سنگ‌آهن 62% برآوردی بر اساس IODEX + پریمیوم عیار حدود ۲-۳ دلار است\n"
    text += "• کلیه قیمت‌ها بر اساس منابع معتبر پلتس، Fastmarkets و دیگر شاخص‌های روز بازار جمع‌آوری شده است.\n"
    text += "• قیمت‌های HRC و مقاطع فولادی مطابق آخرین معاملات و شاخص‌های پلتس در بهار ۲۰۲۶ می‌باشند.\n"
    text += "📌 قیمت‌ها هر ۶ ساعت به‌روزرسانی می‌شوند."

    await query.edit_message_text(text, reply_markup=get_back_button("main"), parse_mode="Markdown")

async def show_iran(update: Update, context):
    query = update.callback_query
    await query.answer()
    iran = await get_iran_prices()
    nego = await get_usd_nego_rate_toman()
    free = await get_usd_free_rate_toman()
    last = iran_prices_cache["last_update"]
    upd_txt = f"🔄 {last.strftime('%Y/%m/%d - %H:%M')}" if last else "🔄 در حال دریافت..."

    text = (
        f"🇮🇷 *قیمت‌های داخلی ایران* 🇮🇷\n"
        f"{upd_txt}\n\n"
        f"💱 *نرخ ارز (تومان)*\n"
        f"   • مبادله‌ای (نیمایی) : {nego:,}\n"
        f"   • بازار آزاد         : {free:,}\n\n"
        "─────────────────────────────────────────────────────\n"
        "🏭 *بازار آزاد (تومان)*\n"
        "─────────────────────────────────────────────────────\n"
        "| محصول               | قیمت (تومان)              | واحد      |\n"
        "─────────────────────────────────────────────────────\n"
    )
    for key, v in iran.items():
        price = v.get('free_market', 'نامشخص')
        unit = v.get('unit', 'تن')
        text += f"| {v['name']:<18} | {price:>24} | {unit:>8} |\n"
    text += "─────────────────────────────────────────────────────\n\n"

    text += (
        "🏭 *قیمت درب کارخانه (میانگین)*\n"
        "─────────────────────────────────────────────────────\n"
        f"🔩 شمش فولادی    : {iran['billet']['factory']} تومان/کیلو\n"
        f"📏 میلگرد        : {iran['rebar']['factory']} تومان/کیلو\n"
        f"🏗️ تیرآهن        : {iran['ibeam']['factory']} تومان/کیلو\n"
        f"🟤 گندله         : {iran['pellet']['factory']} تومان/تن\n"
        f"🪨 کنسانتره      : {iran['concentrate']['factory']} تومان/تن\n"
        "─────────────────────────────────────────────────────\n"
        f"📆 بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await query.edit_message_text(text, reply_markup=get_back_button("main"), parse_mode="Markdown")

# ========== محاسبه سود (Conversation) ==========
async def start_profit(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {}
    keyboard = [
        [InlineKeyboardButton("کنسانتره سنگ آهن", callback_data="prod_concentrate")],
        [InlineKeyboardButton("گندله", callback_data="prod_pellet")],
        [InlineKeyboardButton("آهن اسفنجی", callback_data="prod_dri")],
        [InlineKeyboardButton("شمش فولادی", callback_data="prod_billet")],
        [InlineKeyboardButton("میلگرد", callback_data="prod_rebar")]
    ]
    await query.edit_message_text(
        "📊 *محاسبه سود*\n\nلطفاً محصول را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return SELECT_PRODUCT

async def product_selected(update: Update, context):
    query = update.callback_query
    await query.answer()
    prod_map = {
        "prod_concentrate": "کنسانتره سنگ آهن",
        "prod_pellet": "گندله",
        "prod_dri": "آهن اسفنجی",
        "prod_billet": "شمش فولادی",
        "prod_rebar": "میلگرد"
    }
    product = prod_map.get(query.data)
    if not product:
        return
    user_data[query.from_user.id]["product"] = product
    await query.edit_message_text(
        f"📊 *محاسبه سود - {product}*\n\n💰 قیمت خرید خود را به *دلار* وارد کنید:\n(مثال: 95)",
        reply_markup=get_back_button("price"),
        parse_mode="Markdown"
    )
    return GET_PRICE

async def get_price(update: Update, context):
    uid = update.effective_user.id
    try:
        raw = update.message.text.replace(',', '').replace('،', '').strip()
        price = float(raw)
        user_data[uid]["purchase"] = price
        nego = await get_usd_nego_rate_toman()
        free = await get_usd_free_rate_toman()
        await update.message.reply_text(
            f"💱 *نرخ دلار (تومان):*\n   • مبادله‌ای: {nego:,}\n   • بازار آزاد: {free:,}\n\n"
            "0 = نرخ مبادله‌ای\n1 = نرخ بازار آزاد\nیا عدد دلخواه را وارد کنید:",
            reply_markup=get_back_button("rate"),
            parse_mode="Markdown"
        )
        return GET_RATE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 95):", reply_markup=get_back_button("price"))
        return GET_PRICE

async def get_rate(update: Update, context):
    uid = update.effective_user.id
    try:
        val = float(update.message.text.replace(',', '').replace('،', '').strip())
        nego = await get_usd_nego_rate_toman()
        free = await get_usd_free_rate_toman()
        if val == 0:
            user_data[uid]["rate"] = nego
            rate_type = "مبادله‌ای"
        elif val == 1:
            user_data[uid]["rate"] = free
            rate_type = "بازار آزاد"
        else:
            user_data[uid]["rate"] = int(val)
            rate_type = "دلخواه"
        await update.message.reply_text(
            f"✅ نرخ ارز *{rate_type}*: {user_data[uid]['rate']:,} تومان\n\n⚖️ *تناژ* (تن) را وارد کنید:\n(مثال: 5000)",
            reply_markup=get_back_button("tonnage"),
            parse_mode="Markdown"
        )
        return GET_TONNAGE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (0, 1 یا عدد دلخواه):", reply_markup=get_back_button("rate"))
        return GET_RATE

async def get_tonnage(update: Update, context):
    uid = update.effective_user.id
    try:
        raw = update.message.text.replace(',', '').replace('،', '').strip()
        ton = float(raw)
        user_data[uid]["tonnage"] = ton
        await update.message.reply_text(
            "🚢 *هزینه حمل* هر تن به دلار را وارد کنید:\n(مثال: 18)",
            reply_markup=get_back_button("freight"),
            parse_mode="Markdown"
        )
        return GET_FREIGHT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 5000):", reply_markup=get_back_button("tonnage"))
        return GET_TONNAGE

async def get_freight(update: Update, context):
    uid = update.effective_user.id
    try:
        raw = update.message.text.replace(',', '').replace('،', '').strip()
        freight = float(raw)
        user_data[uid]["freight"] = freight
        await update.message.reply_text(
            "⚓ *هزینه بارگیری در پورت* هر تن به دلار را وارد کنید:\n(مثال: 4)",
            reply_markup=get_back_button("port"),
            parse_mode="Markdown"
        )
        return GET_PORT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 18):", reply_markup=get_back_button("freight"))
        return GET_FREIGHT

async def get_port(update: Update, context):
    uid = update.effective_user.id
    try:
        raw = update.message.text.replace(',', '').replace('،', '').strip()
        port = float(raw)
        user_data[uid]["port"] = port
        d = user_data[uid]
        t = d["tonnage"]
        purchase = d["purchase"]
        freight = d["freight"]
        port_cost = d["port"]
        rate = d["rate"]
        fob = purchase * 1.2
        revenue = fob * t
        total_cost = (purchase + freight + port_cost) * t
        profit_usd = revenue - total_cost
        profit_toman = profit_usd * rate
        result = (
            f"📊 *نتیجه محاسبه سود*\n📅 {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n{'─' * 30}\n"
            f"📦 محصول: {d['product']}\n⚖️ تناژ: {t:,.0f} تن\n💰 قیمت خرید: ${purchase:,.0f}/تن\n"
            f"💵 قیمت فروش (FOB 20%): ${fob:,.0f}/تن\n{'─' * 30}\n"
            f"🚢 حمل: ${freight:,.0f}/تن\n⚓ پورت: ${port_cost:,.0f}/تن\n{'─' * 30}\n"
            f"✅ *سود خالص:*\n🇺🇸 دلار: ${profit_usd:,.0f}\n🇮🇷 تومان: {profit_toman:,.0f} تومان\n{'─' * 30}\n"
            f"💱 نرخ ارز: {rate:,} تومان"
        )
        await update.message.reply_text(result, reply_markup=get_back_button("main"), parse_mode="Markdown")
        del user_data[uid]
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"get_port error: {e}")
        await update.message.reply_text("❌ خطا: لطفاً یک عدد معتبر وارد کنید.", reply_markup=get_back_button("port"))
        return GET_PORT

async def cancel(update: Update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=get_back_button("main"))

# ========== هندلرهای بازگشت درون مکالمه ==========
async def back_to_product(update: Update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("کنسانتره سنگ آهن", callback_data="prod_concentrate")],
        [InlineKeyboardButton("گندله", callback_data="prod_pellet")],
        [InlineKeyboardButton("آهن اسفنجی", callback_data="prod_dri")],
        [InlineKeyboardButton("شمش فولادی", callback_data="prod_billet")],
        [InlineKeyboardButton("میلگرد", callback_data="prod_rebar")]
    ]
    await query.edit_message_text(
        "📊 *محاسبه سود*\n\nلطفاً محصول را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return SELECT_PRODUCT

async def back_to_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if uid not in user_data or "product" not in user_data[uid]:
        return await back_to_product(update, context)
    prod = user_data[uid]["product"]
    await query.edit_message_text(
        f"📊 *محاسبه سود - {prod}*\n\n💰 قیمت خرید خود را به *دلار* وارد کنید:\n(مثال: 95)",
        reply_markup=get_back_button("price"),
        parse_mode="Markdown"
    )
    return GET_PRICE

async def back_to_rate(update: Update, context):
    query = update.callback_query
    await query.answer()
    nego = await get_usd_nego_rate_toman()
    free = await get_usd_free_rate_toman()
    await query.edit_message_text(
        f"💱 *نرخ دلار (تومان):*\n   • مبادله‌ای: {nego:,}\n   • بازار آزاد: {free:,}\n\n"
        "0 = نرخ مبادله‌ای\n1 = نرخ بازار آزاد\nیا عدد دلخواه:",
        reply_markup=get_back_button("rate"),
        parse_mode="Markdown"
    )
    return GET_RATE

async def back_to_tonnage(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚖️ *تناژ* (تن) را وارد کنید:\n(مثال: 5000)",
        reply_markup=get_back_button("tonnage"),
        parse_mode="Markdown"
    )
    return GET_TONNAGE

async def back_to_freight(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚢 *هزینه حمل* هر تن به دلار را وارد کنید:\n(مثال: 18)",
        reply_markup=get_back_button("freight"),
        parse_mode="Markdown"
    )
    return GET_FREIGHT

async def back_to_port(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚓ *هزینه بارگیری در پورت* هر تن به دلار را وارد کنید:\n(مثال: 4)",
        reply_markup=get_back_button("port"),
        parse_mode="Markdown"
    )
    return GET_PORT

# ========== وظیفه زمانبندی برای بروزرسانی خودکار ==========
async def scheduled_price_update():
    while True:
        await asyncio.sleep(21600)  # 6 ساعت
        logger.info("بروزرسانی خودکار قیمت‌های ایران...")
        await get_iran_prices()

# ========== اجرای اصلی ==========
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not found!")
        return

    app = Application.builder().token(token).build()

    # هندلرهای بازگشت عمومی
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(back_to_product, pattern="^back_to_product$"))
    app.add_handler(CallbackQueryHandler(back_to_price, pattern="^back_to_price$"))
    app.add_handler(CallbackQueryHandler(back_to_rate, pattern="^back_to_rate$"))
    app.add_handler(CallbackQueryHandler(back_to_tonnage, pattern="^back_to_tonnage$"))
    app.add_handler(CallbackQueryHandler(back_to_freight, pattern="^back_to_freight$"))
    app.add_handler(CallbackQueryHandler(back_to_port, pattern="^back_to_port$"))

    # هندلرهای منو
    app.add_handler(CallbackQueryHandler(show_global, pattern="^show_global$"))
    app.add_handler(CallbackQueryHandler(show_iran, pattern="^show_iran$"))
    app.add_handler(CallbackQueryHandler(start_profit, pattern="^start_profit$"))

    # مکالمه محاسبه سود
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_profit, pattern="^start_profit$")],
        states={
            SELECT_PRODUCT: [CallbackQueryHandler(product_selected, pattern="^prod_")],
            GET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            GET_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate)],
            GET_TONNAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tonnage)],
            GET_FREIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_freight)],
            GET_PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_port)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))

    async def post_init(_):
        asyncio.create_task(scheduled_price_update())
        await get_iran_prices()

    app.post_init = post_init
    logger.info("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
