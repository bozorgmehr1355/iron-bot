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

# ========== تنظیمات لاگ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== State های مکالمه ==========
SELECT_PRODUCT, GET_PRICE, GET_RATE, GET_TONNAGE, GET_FREIGHT, GET_PORT = range(6)

# حافظه موقت کاربر
user_data = {}

# کش قیمت ایران
iran_prices_cache = {
    "data": None,
    "last_update": None
}

# نمونه PriceArbiter
price_arbiter = PriceArbiter(tolerance_percent=2.0)

# ========== توابع نرخ ارز (تومان) ==========
def get_usd_nego_rate_toman() -> int:
    """نرخ دلار مبادله‌ای (نیمایی) – تومان"""
    # در صورت عدم دسترسی به API، مقدار پیش‌فرض 146,800 تومان برگردان
    return 146800

def get_usd_free_rate_toman() -> int:
    """نرخ دلار بازار آزاد – تومان (دریافت از nobitex یا tgju)"""
    # در صورت عدم دسترسی به API، مقدار پیش‌فرض 178,000 تومان برگردان
    return 178000

# ========== Web Scraping اختصاصی برای هر محصول ==========
async def fetch_ahanmelal_price(product_name: str) -> Optional[int]:
    """دریافت قیمت یک محصول از سایت آهن ملل (تومان/کیلو یا تومان/تن)"""
    urls = {
        "billet": "https://ahanmelal.com/steel-ingots/steel-ingot-price",
        "rebar": "https://ahanmelal.com/steel-products/rebar-price",
        "ibeam": "https://ahanmelal.com/steel-products/ibeam-price",
        "sponge": "https://ahanmelal.com/sponge-iron/sponge-iron-price",
    }
    if product_name not in urls:
        return None
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(urls[product_name], headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    # سلکتورهای احتمالی قیمت (باید با بررسی سایت دقیق شوند)
                    selectors = ['.product-price', '.price', '.current-price', '.price-value', '.product__price']
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
        logger.error(f"Error fetching {product_name} from ahanmelal: {e}")
    return None

async def fetch_metals_api_price(symbol: str) -> Optional[float]:
    """دریافت قیمت جهانی از metals-api (دلار/تن)"""
    api_key = os.environ.get("METALS_API_KEY")
    if not api_key:
        return None
    url = f"https://api.metals-api.com/v1/latest?access_key={api_key}&base=USD&symbols={symbol}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        return data["rates"].get(symbol)
    except Exception as e:
        logger.error(f"Metals-API error: {e}")
    return None

async def fetch_multiple_sources(product_key: str) -> Dict[str, Optional[float]]:
    """جمع‌آوری قیمت از منابع مختلف برای یک محصول خاص"""
    sources = {}
    if product_key == "billet":
        # منبع داخلی
        local_price = await fetch_ahanmelal_price("billet")
        if local_price:
            sources["ahanmelal"] = float(local_price)
        # منبع جهانی (دلار به تومان با نرخ آزاد)
        usd_price = await fetch_metals_api_price("STEEL")
        if usd_price:
            free_rate = get_usd_free_rate_toman()
            sources["metals-api"] = usd_price * free_rate
    elif product_key == "rebar":
        local_price = await fetch_ahanmelal_price("rebar")
        if local_price:
            sources["ahanmelal"] = float(local_price)
    elif product_key == "ibeam":
        local_price = await fetch_ahanmelal_price("ibeam")
        if local_price:
            sources["ahanmelal"] = float(local_price)
    elif product_key == "dri":
        local_price = await fetch_ahanmelal_price("sponge")
        if local_price:
            sources["ahanmelal"] = float(local_price)
    # اضافه کردن منبع ثابت (بازار آهن) در آینده
    return sources

# ========== دکمه بازگشت ==========
def get_back_button(step: str) -> InlineKeyboardMarkup:
    keyboard = []
    if step == "main":
        keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]]
    elif step == "price":
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به انتخاب محصول", callback_data="back_to_product")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
    elif step == "rate":
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به قیمت خرید", callback_data="back_to_price")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
    elif step == "tonnage":
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به نرخ ارز", callback_data="back_to_rate")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
    elif step == "freight":
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به تناژ", callback_data="back_to_tonnage")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
    elif step == "port":
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به هزینه حمل", callback_data="back_to_freight")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
    else:
        keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(keyboard)

# ========== دریافت قیمت‌های ایران (با به‌روزرسانی خودکار) ==========
async def get_iran_prices():
    global iran_prices_cache
    now = datetime.now()
    if iran_prices_cache["data"] and iran_prices_cache["last_update"]:
        if (now - iran_prices_cache["last_update"]).total_seconds() < 21600:
            return iran_prices_cache["data"]

    logger.info("بروزرسانی قیمت‌های ایران از منابع چندگانه...")
    # دریافت قیمت شمش
    billet_sources = await fetch_multiple_sources("billet")
    billet_res = price_arbiter.resolve_price(billet_sources, default=55000)
    billet_price = billet_res["price"]
    # دریافت قیمت میلگرد
    rebar_sources = await fetch_multiple_sources("rebar")
    rebar_res = price_arbiter.resolve_price(rebar_sources, default=65000)
    rebar_price = rebar_res["price"]
    # دریافت قیمت تیرآهن
    ibeam_sources = await fetch_multiple_sources("ibeam")
    ibeam_res = price_arbiter.resolve_price(ibeam_sources, default=62000)
    ibeam_price = ibeam_res["price"]
    # دریافت قیمت آهن اسفنجی
    dri_sources = await fetch_multiple_sources("dri")
    dri_res = price_arbiter.resolve_price(dri_sources, default=15500)
    dri_price = dri_res["price"]

    # ساختار قیمت‌ها (بر اساس روش اعتبارسنجی)
    prices = {
        "concentrate": {
            "name": "کنسانتره سنگ آهن",
            "ice": "۶,۰۰۰,۰۰۰ - ۷,۰۰۰,۰۰۰",
            "free_market": "۶,۲۰۰,۰۰۰ - ۷,۲۰۰,۰۰۰",
            "factory": "گل گهر: ۶,۵۰۰,۰۰۰ | مرکزی: ۶,۸۰۰,۰۰۰",
            "unit": "تن"
        },
        "pellet": {
            "name": "گندله",
            "ice": "۸,۰۰۰,۰۰۰ - ۱۰,۵۰۰,۰۰۰",
            "free_market": "۸,۵۰۰,۰۰۰ - ۱۱,۵۰۰,۰۰۰",
            "factory": "گل گهر: ۱۰,۷۰۰,۰۰۰ | چادرملو: ۱۰,۲۰۰,۰۰۰",
            "unit": "تن"
        },
        "dri": {
            "name": "آهن اسفنجی",
            "ice": f"{int(dri_price * 0.95):,} - {int(dri_price * 1.02):,}",
            "free_market": f"{int(dri_price * 0.98):,} - {int(dri_price * 1.05):,}",
            "factory": f"میانگین منابع: {int(dri_price):,}",
            "unit": "کیلو"
        },
        "billet": {
            "name": "شمش فولادی",
            "ice": f"{int(billet_price * 0.95):,} - {int(billet_price * 1.02):,}",
            "free_market": f"{int(billet_price * 0.98):,} - {int(billet_price * 1.05):,}",
            "factory": f"میانگین منابع: {int(billet_price):,}",
            "unit": "کیلو"
        },
        "rebar": {
            "name": "میلگرد",
            "ice": f"{int(rebar_price * 0.95):,} - {int(rebar_price * 1.02):,}",
            "free_market": f"{int(rebar_price * 0.98):,} - {int(rebar_price * 1.05):,}",
            "factory": f"میانگین منابع: {int(rebar_price):,}",
            "unit": "کیلو"
        },
        "ibeam": {
            "name": "تیرآهن",
            "ice": f"{int(ibeam_price * 0.95):,} - {int(ibeam_price * 1.02):,}",
            "free_market": f"{int(ibeam_price * 0.98):,} - {int(ibeam_price * 1.05):,}",
            "factory": f"میانگین منابع: {int(ibeam_price):,}",
            "unit": "کیلو"
        }
    }
    iran_prices_cache["data"] = prices
    iran_prices_cache["last_update"] = now
    logger.info("قیمت‌های ایران بروزرسانی شد.")
    return prices

# ========== قیمت‌های جهانی (ساده) ==========
def get_global_prices():
    return {
        "concentrate": {"name": "کنسانتره سنگ آهن", "fob_pg": 85, "north": 130, "south": 131},
        "pellet": {"name": "گندله", "fob_pg": 105, "north": 155, "south": 156},
        "dri": {"name": "آهن اسفنجی", "fob_pg": 200, "north": 280, "south": 282},
        "billet": {"name": "شمش فولادی", "fob_pg": 480, "north": 520, "south": 515},
        "rebar": {"name": "میلگرد", "fob_pg": 550, "north": 600, "south": 595}
    }

# ========== هندلرهای منوی اصلی ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="start_profit")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="show_global")],
        [InlineKeyboardButton("🇮🇷 قیمت ایران", callback_data="show_iran")]
    ]
    await update.message.reply_text(
        "🏭 *ربات تخصصی زنجیره آهن و فولاد* 🏭\n\n"
        "📌 محصولات تحت پوشش:\n• کنسانتره • گندله • آهن اسفنجی • شمش • میلگرد • تیرآهن\n\n"
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
        "🏭 *ربات تخصصی زنجیره آهن و فولاد* 🏭\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def show_global(update: Update, context):
    query = update.callback_query
    await query.answer()
    text = "🌍 *قیمت‌های جهانی* 🌍\n" + datetime.now().strftime('%Y/%m/%d - %H:%M') + "\n\n"
    for key, d in get_global_prices().items():
        text += f"• *{d['name']}*\n   🇮🇷 FOB خلیج فارس: ${d['fob_pg']}\n   🇨🇳 CFR شمال چین: ${d['north']}\n   🇨🇳 CFR جنوب چین: ${d['south']}\n\n"
    await query.edit_message_text(text, reply_markup=get_back_button("main"), parse_mode="Markdown")

async def show_iran(update: Update, context):
    query = update.callback_query
    await query.answer()
    iran_prices = await get_iran_prices()
    nego = get_usd_nego_rate_toman()
    free = get_usd_free_rate_toman()
    last = iran_prices_cache["last_update"]
    upd_txt = f"🔄 {last.strftime('%Y/%m/%d - %H:%M')}" if last else "🔄 در حال دریافت..."
    text = f"🇮🇷 *قیمت‌های داخلی ایران* 🇮🇷\n{upd_txt}\n\n💱 *نرخ ارز (تومان):*\n   • مبادله‌ای: {nego:,}\n   • آزاد: {free:,}\n\n"
    text += "══ بورس کالا ══\n"
    for k, v in iran_prices.items():
        text += f"• {v['name']}: {v['ice']} تومان/{v['unit']}\n"
    text += "\n══ بازار آزاد ══\n"
    for k, v in iran_prices.items():
        text += f"• {v['name']}: {v['free_market']} تومان/{v['unit']}\n"
    text += "\n══ قیمت درب کارخانه ══\n"
    text += f"🔩 شمش: {iran_prices['billet']['factory']} تومان/کیلو\n"
    text += f"📏 میلگرد: {iran_prices['rebar']['factory']} تومان/کیلو\n"
    text += f"🏗️ تیرآهن: {iran_prices['ibeam']['factory']} تومان/کیلو\n"
    text += "📆 قیمت‌ها هر ۶ ساعت به‌روزرسانی می‌شوند."
    await query.edit_message_text(text, reply_markup=get_back_button("main"), parse_mode="Markdown")

# ========== محاسبه سود (Conversation) ==========
async def start_profit(update: Update, context):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data[uid] = {}
    keyboard = [
        [InlineKeyboardButton("کنسانتره سنگ آهن", callback_data="prod_concentrate")],
        [InlineKeyboardButton("گندله", callback_data="prod_pellet")],
        [InlineKeyboardButton("آهن اسفنجی", callback_data="prod_dri")],
        [InlineKeyboardButton("شمش فولادی", callback_data="prod_billet")],
        [InlineKeyboardButton("میلگرد", callback_data="prod_rebar")],
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
    mapping = {
        "prod_concentrate": "کنسانتره سنگ آهن",
        "prod_pellet": "گندله",
        "prod_dri": "آهن اسفنجی",
        "prod_billet": "شمش فولادی",
        "prod_rebar": "میلگرد"
    }
    product = mapping.get(query.data)
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
        nego = get_usd_nego_rate_toman()
        free = get_usd_free_rate_toman()
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
        raw = update.message.text.replace(',', '').replace('،', '').strip()
        val = float(raw)
        nego = get_usd_nego_rate_toman()
        free = get_usd_free_rate_toman()
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
            f"✅ نرخ ارز {rate_type}: *{user_data[uid]['rate']:,}* تومان\n\n⚖️ *تناژ* (تن) را وارد کنید:\n(مثال: 5000)",
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
        result = f"""
📊 *نتیجه محاسبه سود*
📅 {datetime.now().strftime('%Y/%m/%d - %H:%M')}
{'─' * 30}
📦 محصول: {d['product']}
⚖️ تناژ: {t:,.0f} تن
💰 قیمت خرید: ${purchase:,.0f}/تن
💵 قیمت فروش (FOB 20%): ${fob:,.0f}/تن
{'─' * 30}
🚢 حمل: ${freight:,.0f}/تن
⚓ پورت: ${port_cost:,.0f}/تن
{'─' * 30}
✅ *سود خالص:*
🇺🇸 دلار: ${profit_usd:,.0f}
🇮🇷 تومان: {profit_toman:,.0f} تومان
{'─' * 30}
💱 نرخ ارز: {rate:,} تومان
"""
        await update.message.reply_text(result, reply_markup=get_back_button("main"), parse_mode="Markdown")
        del user_data[uid]
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in get_port: {e}")
        await update.message.reply_text("❌ خطا: لطفاً یک عدد معتبر وارد کنید.", reply_markup=get_back_button("port"))
        return GET_PORT

async def cancel(update: Update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=get_back_button("main"))

# ========== هندلرهای بازگشت ==========
async def back_to_product(update: Update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("کنسانتره سنگ آهن", callback_data="prod_concentrate")],
        [InlineKeyboardButton("گندله", callback_data="prod_pellet")],
        [InlineKeyboardButton("آهن اسفنجی", callback_data="prod_dri")],
        [InlineKeyboardButton("شمش فولادی", callback_data="prod_billet")],
        [InlineKeyboardButton("میلگرد", callback_data="prod_rebar")],
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
    product = user_data[uid]["product"]
    await query.edit_message_text(
        f"📊 *محاسبه سود - {product}*\n\n💰 قیمت خرید خود را به *دلار* وارد کنید:\n(مثال: 95)",
        reply_markup=get_back_button("price"),
        parse_mode="Markdown"
    )
    return GET_PRICE

async def back_to_rate(update: Update, context):
    query = update.callback_query
    await query.answer()
    nego = get_usd_nego_rate_toman()
    free = get_usd_free_rate_toman()
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

# ========== وظیفه زمانبندی شده برای بروزرسانی خودکار قیمت‌ها ==========
async def scheduled_price_update():
    while True:
        await asyncio.sleep(21600)  # 6 ساعت
        logger.info("بروزرسانی خودکار قیمت‌های ایران (زمانبندی)...")
        await get_iran_prices()

# ========== اجرای اصلی ==========
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not found!")
        return
    app = Application.builder().token(token).build()

    # هندلرهای بازگشت
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

    async def post_init(application):
        asyncio.create_task(scheduled_price_update())
        await get_iran_prices()

    app.post_init = post_init
    logger.info("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
