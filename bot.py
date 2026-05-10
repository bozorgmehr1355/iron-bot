import os
import re
import asyncio
import logging
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ConversationHandler,
    MessageHandler, filters, CallbackQueryHandler
)

# ========== تنظیمات لاگ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== توابع کمکی ==========
def to_persian_digits(text: str) -> str:
    persian_digits = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }
    return ''.join(persian_digits.get(ch, ch) for ch in text)

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

# ========== نرخ ارز ==========
async def get_usd_nego_rate_toman() -> int:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.tgju.org/sana/", timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*ریال', html)
                    if match:
                        return int(match.group(1).replace(',', '')) // 10
    except:
        pass
    return 146800

async def get_usd_free_rate_toman() -> int:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price_str = data.get("price", "0").replace(",", "")
                    price = int(price_str)
                    if price > 0:
                        return price // 10
    except:
        pass
    return 178000

# ========== قیمت‌های جهانی (ثابت) ==========
GLOBAL_PRODUCTS = [
    {"name": "کنسانتره سنگ آهن", "fob": 85, "north": 130, "south": 131},
    {"name": "گندله", "fob": 105, "north": 155, "south": 156},
    {"name": "آهن اسفنجی", "fob": 200, "north": 280, "south": 282},
    {"name": "شمش فولادی", "fob": 480, "north": 520, "south": 515},
    {"name": "میلگرد", "fob": 550, "north": 600, "south": 595},
]

# ========== قیمت‌های داخلی ایران ==========
iran_prices_cache = {"data": None, "last_update": None}

async def fetch_ahanmelal_price(product_key: str):
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
                    for sel in ['.product-price', '.price', '.current-price']:
                        elem = soup.select_one(sel)
                        if elem:
                            txt = elem.get_text(strip=True)
                            nums = re.findall(r'(\d{1,3}(?:,\d{3})*)', txt)
                            if nums:
                                raw = nums[0].replace(',', '')
                                if raw.isdigit():
                                    return int(raw)
    except:
        pass
    return None

async def get_iran_prices():
    global iran_prices_cache
    now = datetime.now()
    if iran_prices_cache["data"] and iran_prices_cache["last_update"]:
        if (now - iran_prices_cache["last_update"]).total_seconds() < 21600:
            return iran_prices_cache["data"]

    billet = await fetch_ahanmelal_price("billet") or 55000
    rebar = await fetch_ahanmelal_price("rebar") or 65000
    ibeam = await fetch_ahanmelal_price("ibeam") or 62000
    dri = await fetch_ahanmelal_price("dri") or 15500

    prices = {
        "concentrate": {"name": "کنسانتره سنگ آهن", "ice": "۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰", "free_market": "۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰", "factory": "گل گهر: ۴,۳۰۰,۰۰۰ | مرکزی: ۴,۶۰۰,۰۰۰", "unit": "تن"},
        "pellet": {"name": "گندله", "ice": "۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰", "free_market": "۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰", "factory": "گل گهر: ۶,۴۰۰,۰۰۰ | چادرملو: ۶,۳۰۰,۰۰۰", "unit": "تن"},
        "dri": {"name": "آهن اسفنجی", "ice": f"{int(dri*0.95):,} - {int(dri*1.02):,}", "free_market": f"{int(dri*0.98):,} - {int(dri*1.05):,}", "factory": f"میانگین: {int(dri):,}", "unit": "کیلو"},
        "billet": {"name": "شمش فولادی", "ice": f"{int(billet*0.95):,} - {int(billet*1.02):,}", "free_market": f"{int(billet*0.98):,} - {int(billet*1.05):,}", "factory": f"اصفهان: {billet:,} | یزد: {billet-500:,} | قزوین: {billet-1500:,}", "unit": "کیلو"},
        "rebar": {"name": "میلگرد", "ice": f"{int(rebar*0.95):,} - {int(rebar*1.02):,}", "free_market": f"{int(rebar*0.98):,} - {int(rebar*1.05):,}", "factory": f"ذوب آهن: {rebar:,} | امیرکبیر: {rebar+1000:,}", "unit": "کیلو"},
        "ibeam": {"name": "تیرآهن", "ice": f"{int(ibeam*0.95):,} - {int(ibeam*1.02):,}", "free_market": f"{int(ibeam*0.98):,} - {int(ibeam*1.05):,}", "factory": f"ذوب آهن: {ibeam:,}", "unit": "کیلو"}
    }
    iran_prices_cache["data"] = prices
    iran_prices_cache["last_update"] = now
    return prices

# ========== State های مکالمه ==========
SELECT_PRODUCT, GET_PRICE, GET_RATE, GET_TONNAGE, GET_FREIGHT, GET_PORT = range(6)
user_data = {}

# ========== منوی اصلی ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="start_profit")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="show_global")],
        [InlineKeyboardButton("🇮🇷 قیمت ایران", callback_data="show_iran")]
    ]
    await update.message.reply_text(
        "🏭 *ربات تخصصی زنجیره آهن و فولاد* 🏭\n\n"
        "📌 محصولات تحت پوشش:\n"
        "• کنسانتره سنگ آهن\n"
        "• گندله\n"
        "• آهن اسفنجی\n"
        "• شمش فولادی\n"
        "• میلگرد\n\n"
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
        "📌 محصولات تحت پوشش:\n"
        "• کنسانتره سنگ آهن\n"
        "• گندله\n"
        "• آهن اسفنجی\n"
        "• شمش فولادی\n"
        "• میلگرد\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ========== قیمت جهانی ==========
async def show_global(update: Update, context):
    query = update.callback_query
    await query.answer()
    text = "🌍 *قیمت‌های جهانی* 🌍\n\n"
    for p in GLOBAL_PRODUCTS:
        text += f"• *{p['name']}*\n"
        text += f"   🇮🇷 FOB خلیج فارس: *{to_persian_digits(f'${p["fob"]}')}*\n"
        text += f"   🇨🇳 CFR شمال چین: *{to_persian_digits(f'${p["north"]}')}*\n"
        text += f"   🇨🇳 CFR جنوب چین: *{to_persian_digits(f'${p["south"]}')}*\n\n"
    text += f"🔄 بروزرسانی: {to_persian_digits(datetime.now().strftime('%H:%M - %Y/%m/%d'))}"
    await query.edit_message_text(text, reply_markup=get_back_button("main"), parse_mode="Markdown")

# ========== قیمت ایران ==========
async def show_iran(update: Update, context):
    query = update.callback_query
    await query.answer()
    iran = await get_iran_prices()
    nego = await get_usd_nego_rate_toman()
    free = await get_usd_free_rate_toman()
    last = iran_prices_cache.get("last_update")
    upd_txt = f"🔄 {last.strftime('%H:%M - %Y/%m/%d')}" if last else "🔄 در حال دریافت..."
    text = f"🇮🇷 *قیمت‌های داخلی ایران* 🇮🇷\n{to_persian_digits(upd_txt)}\n\n"
    text += "💱 *نرخ ارز:*\n"
    text += f"   • دلار مبادله‌ای (نیمایی): *{to_persian_digits(f'{nego:,}')}* تومان\n"
    text += f"   • دلار بازار آزاد: *{to_persian_digits(f'{free:,}')}* تومان\n\n"
    text += "🏭 *بورس کالا (ICE) - تومان:*\n"
    for k, v in iran.items():
        text += f"   • {v['name']}: *{to_persian_digits(v['ice'])}* تومان/{v['unit']}\n"
    text += "\n🔄 *بازار آزاد - تومان:*\n"
    for k, v in iran.items():
        text += f"   • {v['name']}: *{to_persian_digits(v['free_market'])}* تومان/{v['unit']}\n"
    text += "\n🏭 *قیمت درب کارخانه:*\n"
    text += f"   • شمش: {to_persian_digits(iran['billet']['factory'])} تومان/کیلو\n"
    text += f"   • میلگرد: {to_persian_digits(iran['rebar']['factory'])} تومان/کیلو\n"
    text += f"   • گندله: {to_persian_digits(iran['pellet']['factory'])} تومان/تن\n"
    text += f"   • کنسانتره: {to_persian_digits(iran['concentrate']['factory'])} تومان/تن\n"
    text += "\n📌 منابع: بورس کالا، آهن ملل، نوبیتکس، TGJU"
    await query.edit_message_text(text, reply_markup=get_back_button("main"), parse_mode="Markdown")

# ========== محاسبه سود ==========
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
        f"📊 *محاسبه سود - {product}*\n\n💰 قیمت خرید خود را به *دلار* وارد کنید:\n(مثال: ۹۵)",
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
            f"💱 *نرخ دلار (تومان):*\n   • مبادله‌ای: {to_persian_digits(f'{nego:,}')}\n   • بازار آزاد: {to_persian_digits(f'{free:,}')}\n\n"
            "۰ = نرخ مبادله‌ای\n۱ = نرخ بازار آزاد\nیا عدد دلخواه را وارد کنید:",
            reply_markup=get_back_button("rate"),
            parse_mode="Markdown"
        )
        return GET_RATE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: ۹۵):", reply_markup=get_back_button("price"))
        return GET_PRICE

async def get_rate(update: Update, context):
    uid = update.effective_user.id
    try:
        val = float(update.message.text.replace(',', '').replace('،', '').strip())
        nego = await get_usd_nego_rate_toman()
        free = await get_usd_free_rate_toman()
        if val == 0:
            user_data[uid]["rate"] = nego
        elif val == 1:
            user_data[uid]["rate"] = free
        else:
            user_data[uid]["rate"] = int(val)
        await update.message.reply_text(
            f"✅ نرخ ارز: {to_persian_digits(f'{user_data[uid]["rate"]:,}')} تومان\n\n⚖️ *تناژ* (تن) را وارد کنید:\n(مثال: ۵۰۰۰)",
            reply_markup=get_back_button("tonnage"),
            parse_mode="Markdown"
        )
        return GET_TONNAGE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:", reply_markup=get_back_button("rate"))
        return GET_RATE

async def get_tonnage(update: Update, context):
    uid = update.effective_user.id
    try:
        raw = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["tonnage"] = float(raw)
        await update.message.reply_text(
            "🚢 *هزینه حمل* هر تن به دلار را وارد کنید:\n(مثال: ۱۸)",
            reply_markup=get_back_button("freight"),
            parse_mode="Markdown"
        )
        return GET_FREIGHT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:", reply_markup=get_back_button("tonnage"))
        return GET_TONNAGE

async def get_freight(update: Update, context):
    uid = update.effective_user.id
    try:
        raw = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["freight"] = float(raw)
        await update.message.reply_text(
            "⚓ *هزینه بارگیری در پورت* هر تن به دلار را وارد کنید:\n(مثال: ۴)",
            reply_markup=get_back_button("port"),
            parse_mode="Markdown"
        )
        return GET_PORT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:", reply_markup=get_back_button("freight"))
        return GET_FREIGHT

async def get_port(update: Update, context):
    uid = update.effective_user.id
    try:
        raw = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["port"] = float(raw)
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
            f"📦 محصول: {d['product']}\n⚖️ تناژ: {to_persian_digits(f'{t:,.0f}')} تن\n"
            f"💰 قیمت خرید: {to_persian_digits(f'${purchase:,.0f}')}/تن\n"
            f"💵 قیمت فروش (FOB ۲۰٪): {to_persian_digits(f'${fob:,.0f}')}/تن\n{'─' * 30}\n"
            f"🚢 حمل: {to_persian_digits(f'${freight:,.0f}')}/تن\n⚓ پورت: {to_persian_digits(f'${port_cost:,.0f}')}/تن\n{'─' * 30}\n"
            f"✅ *سود خالص:*\n🇺🇸 دلار: {to_persian_digits(f'${profit_usd:,.0f}')}\n🇮🇷 تومان: {to_persian_digits(f'{profit_toman:,.0f}')} تومان\n{'─' * 30}\n"
            f"💱 نرخ ارز: {to_persian_digits(f'{rate:,}')} تومان"
        )
        await update.message.reply_text(result, reply_markup=get_back_button("main"), parse_mode="Markdown")
        del user_data[uid]
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("❌ خطا: لطفاً یک عدد معتبر وارد کنید.", reply_markup=get_back_button("port"))
        return GET_PORT

async def cancel(update: Update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=get_back_button("main"))

# ========== بازگشت ==========
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
        f"📊 *محاسبه سود - {prod}*\n\n💰 قیمت خرید خود را به *دلار* وارد کنید:\n(مثال: ۹۵)",
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
        f"💱 *نرخ دلار (تومان):*\n   • مبادله‌ای: {to_persian_digits(f'{nego:,}')}\n   • بازار آزاد: {to_persian_digits(f'{free:,}')}\n\n"
        "۰ = نرخ مبادله‌ای\n۱ = نرخ بازار آزاد\nیا عدد دلخواه:",
        reply_markup=get_back_button("rate"),
        parse_mode="Markdown"
    )
    return GET_RATE

async def back_to_tonnage(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚖️ *تناژ* (تن) را وارد کنید:\n(مثال: ۵۰۰۰)",
        reply_markup=get_back_button("tonnage"),
        parse_mode="Markdown"
    )
    return GET_TONNAGE

async def back_to_freight(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚢 *هزینه حمل* هر تن به دلار را وارد کنید:\n(مثال: ۱۸)",
        reply_markup=get_back_button("freight"),
        parse_mode="Markdown"
    )
    return GET_FREIGHT

async def back_to_port(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚓ *هزینه بارگیری در پورت* هر تن به دلار را وارد کنید:\n(مثال: ۴)",
        reply_markup=get_back_button("port"),
        parse_mode="Markdown"
    )
    return GET_PORT

# ========== اجرای اصلی ==========
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not found!")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(back_to_product, pattern="^back_to_product$"))
    app.add_handler(CallbackQueryHandler(back_to_price, pattern="^back_to_price$"))
    app.add_handler(CallbackQueryHandler(back_to_rate, pattern="^back_to_rate$"))
    app.add_handler(CallbackQueryHandler(back_to_tonnage, pattern="^back_to_tonnage$"))
    app.add_handler(CallbackQueryHandler(back_to_freight, pattern="^back_to_freight$"))
    app.add_handler(CallbackQueryHandler(back_to_port, pattern="^back_to_port$"))
    app.add_handler(CallbackQueryHandler(show_global, pattern="^show_global$"))
    app.add_handler(CallbackQueryHandler(show_iran, pattern="^show_iran$"))
    app.add_handler(CallbackQueryHandler(start_profit, pattern="^start_profit$"))

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_profit, pattern="^start_profit$")],
        states={
            SELECT_PRODUCT: [CallbackQueryHandler(product_selected, pattern="^prod_")],
            GET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            GET_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate)],
            GET_TONNAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tonnage)],
            GET_FREIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_freight)],
            GET_PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_port)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(back_to_main, pattern="^back_to_main$")],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))

    async def post_init(_):
        await get_iran_prices()
    app.post_init = post_init

    logger.info("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
