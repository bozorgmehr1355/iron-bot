from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
import requests
from datetime import datetime
import asyncio
import re
import json
from bs4 import BeautifulSoup

# States
SELECT_PRODUCT, GET_PRICE, GET_RATE, GET_TONNAGE, GET_FREIGHT, GET_PORT = range(6)

user_data = {}

# ========== کش قیمت ایران ==========
iran_prices_cache = {
    "data": None,
    "last_update": None
}

# ========== نرخ دلار مبادله‌ای (نیمایی) - تومان ==========
def get_usd_nego_rate_toman():
    try:
        r = requests.get("https://www.tgju.org/sana/", timeout=10)
        if r.status_code == 200:
            match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*ریال', r.text)
            if match:
                rial = int(match.group(1).replace(',', ''))
                return rial // 10
    except:
        pass
    return 146800

# ========== نرخ دلار بازار آزاد - تومان ==========
def get_usd_free_rate_toman():
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price = float(data.get("stats", {}).get("USDT-IRT", {}).get("latest", 0))
            if price > 0:
                return int(price) // 10
    except:
        pass
    try:
        r = requests.get("https://api.nobitex.ir/market/global/price", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("usdt"):
                return int(float(data["usdt"]["price"])) // 10
    except:
        pass
    try:
        r = requests.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price_str = data.get("price", "0").replace(",", "")
            price = int(price_str)
            if price > 0:
                return price // 10
    except:
        pass
    return 178000

# ========== Web Scraping از آهن ملل ==========
async def scrape_ahanmelal():
    """دریافت قیمت‌های به‌روز از سایت آهن ملل با چندین سلکتور"""
    prices = {}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fa-IR,fa;q=0.9',
    }
    
    # مشخصات صفحات
    targets = [
        {"name": "billet", "url": "https://ahanmelal.com/steel-ingots/steel-ingot-price", "selector": ".product-price, .price, .current-price, .price-value, .product__price"},
        {"name": "rebar", "url": "https://ahanmelal.com/steel-products/rebar-price", "selector": ".product-price, .price, .current-price, .price-value, .product__price"},
        {"name": "ibeam", "url": "https://ahanmelal.com/steel-products/ibeam-price", "selector": ".product-price, .price, .current-price"},
    ]
    
    for target in targets:
        try:
            response = requests.get(target["url"], headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                price_value = None
                
                for selector in target["selector"].split(", "):
                    elem = soup.select_one(selector)
                    if elem:
                        price_text = elem.get_text(strip=True)
                        numbers = re.findall(r'([\d,]+)', price_text)
                        if numbers:
                            raw_price = numbers[0].replace(',', '')
                            if re.match(r'^\d+$', raw_price):
                                price_value = int(raw_price)
                                break
                
                if price_value and price_value > 0:
                    prices[target["name"]] = price_value
                    print(f"✅ دریافت قیمت {target['name']}: {price_value} تومان")
        except Exception as e:
            print(f"خطا در دریافت {target['name']}: {e}")
    
    return prices

# ========== دکمه بازگشت ==========
def get_back_button(step):
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

# ========== دریافت قیمت‌های ایران (با بروزرسانی خودکار) ==========
async def get_iran_prices():
    global iran_prices_cache
    
    now = datetime.now()
    
    if iran_prices_cache["data"] and iran_prices_cache["last_update"]:
        time_diff = (now - iran_prices_cache["last_update"]).total_seconds()
        if time_diff < 21600:
            return iran_prices_cache["data"]
    
    print("🔄 بروزرسانی قیمت‌های ایران...")
    
    # دریافت قیمت از آهن ملل
    scraped_prices = await scrape_ahanmelal()
    
    # قیمت‌های به‌روز بازار ایران (با پشتیبانی از داده‌های اسکرپ شده)
    prices = {
        "concentrate": {
            "name": "کنسانتره سنگ آهن",
            "ice": "۶,۰۰۰,۰۰۰ - ۷,۰۰۰,۰۰۰",
            "free_market": "۶,۲۰۰,۰۰۰ - 7,200,000",
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
            "ice": "۱۵,۵۰۰ - ۱۶,۵۰۰",
            "free_market": "۱۶,۵۰۰ - ۱۷,۵۰۰",
            "factory": "میانه: ۱۶,۸۰۰ | نطنز: ۱۶,۵۰۰",
            "unit": "کیلو"
        },
        "billet": {
            "name": "شمش فولادی",
            "ice": "۵۲,۰۰۰ - ۵۴,۰۰۰",
            "free_market": "۵۴,۰۰۰ - ۵۷,۰۰۰",
            "factory": "اصفهان: ۵۵,۷۰۰ | یزد: ۵۵,۵۰۰ | قم: ۵۵,۸۰۰ | کاوه: ۵۴,۵۰۰",
            "unit": "کیلو"
        },
        "rebar": {
            "name": "میلگرد",
            "ice": "۶۲,۰۰۰ - ۶۵,۰۰۰",
            "free_market": "۶۳,۰۰۰ - ۶۸,۰۰۰",
            "factory": "ذوب آهن: ۶۵,۰۰۰ | امیرکبیر: ۶۶,۰۰۰ | کاوه: ۶۴,۰۰۰",
            "unit": "کیلو"
        },
        "ibeam": {
            "name": "تیرآهن",
            "ice": "۵۵,۰۰۰ - ۶۰,۰۰۰",
            "free_market": "۵۹,۰۰۰ - ۶۷,۰۰۰",
            "factory": "ذوب آهن: ۶۲,۰۰۰ | امیرکبیر: ۶۳,۰۰۰",
            "unit": "کیلو"
        }
    }
    
    # به‌روزرسانی با داده‌های اسکرپ شده
    if scraped_prices.get("billet") and scraped_prices["billet"] > 50000:
        billet_price = scraped_prices["billet"]
        prices["billet"]["free_market"] = f"{billet_price-1000:,} - {billet_price+1000:,}"
        prices["billet"]["factory"] = f"فولاد اصفهان: {billet_price:,}"
        prices["billet"]["ice"] = f"{billet_price-2000:,} - {billet_price:,}"
    
    if scraped_prices.get("rebar") and scraped_prices["rebar"] > 60000:
        rebar_price = scraped_prices["rebar"]
        prices["rebar"]["free_market"] = f"{rebar_price-2000:,} - {rebar_price+2000:,}"
        prices["rebar"]["ice"] = f"{rebar_price-3000:,} - {rebar_price-1000:,}"
    
    if scraped_prices.get("ibeam") and scraped_prices["ibeam"] > 55000:
        ibeam_price = scraped_prices["ibeam"]
        prices["ibeam"]["free_market"] = f"{ibeam_price-2000:,} - {ibeam_price+2000:,}"
        prices["ibeam"]["ice"] = f"{ibeam_price-4000:,} - {ibeam_price-1000:,}"
    
    iran_prices_cache["data"] = prices
    iran_prices_cache["last_update"] = now
    
    print(f"✅ قیمت‌های ایران بروزرسانی شد: {now.strftime('%Y/%m/%d - %H:%M')}")
    return prices

# ========== قیمت‌های جهانی ==========
def get_global_prices():
    return {
        "concentrate": {"name": "کنسانتره سنگ آهن", "fob_pg": 85, "north": 130, "south": 131},
        "pellet": {"name": "گندله", "fob_pg": 105, "north": 155, "south": 156},
        "dri": {"name": "آهن اسفنجی", "fob_pg": 200, "north": 280, "south": 282},
        "billet": {"name": "شمش فولادی", "fob_pg": 480, "north": 520, "south": 515},
        "rebar": {"name": "میلگرد", "fob_pg": 550, "north": 600, "south": 595}
    }

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
        "• میلگرد\n"
        "• تیرآهن\n\n"
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
        "• میلگرد\n"
        "• تیرآهن\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ========== نمایش قیمت جهانی ==========
async def show_global(update: Update, context):
    query = update.callback_query
    await query.answer()
    text = "🌍 *قیمت‌های جهانی* 🌍\n"
    text += f"🔄 {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n\n"
    for key, d in get_global_prices().items():
        text += f"• *{d['name']}*\n"
        text += f"   🇮🇷 FOB خلیج فارس: ${d['fob_pg']}\n"
        text += f"   🇨🇳 CFR شمال چین: ${d['north']}\n"
        text += f"   🇨🇳 CFR جنوب چین: ${d['south']}\n\n"
    await query.edit_message_text(text, reply_markup=get_back_button("main"), parse_mode="Markdown")

# ========== نمایش قیمت ایران ==========
async def show_iran(update: Update, context):
    query = update.callback_query
    await query.answer()
    iran_prices = await get_iran_prices()
    nego_rate = get_usd_nego_rate_toman()
    free_rate = get_usd_free_rate_toman()
    
    last_update = iran_prices_cache["last_update"]
    update_text = f"🔄 {last_update.strftime('%Y/%m/%d - %H:%M')}" if last_update else "🔄 در حال دریافت..."
    
    text = "🇮🇷 *قیمت‌های داخلی ایران* 🇮🇷\n"
    text += f"{update_text}\n\n"
    text += "💱 *نرخ ارز (تومان):*\n"
    text += f"   • دلار مبادله‌ای (نیمایی): *{nego_rate:,}* تومان\n"
    text += f"   • دلار بازار آزاد: *{free_rate:,}* تومان\n\n"
    text += "═══════════════════════════\n"
    text += "🏭 *بورس کالا:*\n\n"
    for key, d in iran_prices.items():
        unit = d.get("unit", "تن")
        text += f"• *{d['name']}*: {d['ice']} تومان/{unit}\n"
    text += "\n🔄 *بازار آزاد:*\n\n"
    for key, d in iran_prices.items():
        unit = d.get("unit", "تن")
        text += f"• *{d['name']}*: {d['free_market']} تومان/{unit}\n"
    text += "\n🏭 *قیمت درب کارخانه:*\n\n"
    text += f"🔩 شمش: {iran_prices['billet']['factory']} تومان/کیلو\n"
    text += f"🟤 گندله: {iran_prices['pellet']['factory']} تومان/تن\n"
    text += f"🪨 کنسانتره: {iran_prices['concentrate']['factory']} تومان/تن\n"
    text += f"📏 میلگرد: {iran_prices['rebar']['factory']} تومان/کیلو\n"
    text += f"🏗️ تیرآهن: {iran_prices['ibeam']['factory']} تومان/کیلو\n"
    text += "═══════════════════════════\n"
    text += "📆 قیمت‌ها هر 6 ساعت به‌طور خودکار بروزرسانی می‌شوند."
    await query.edit_message_text(text, reply_markup=get_back_button("main"), parse_mode="Markdown")

# ========== شروع محاسبه سود ==========
async def start_profit(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {}
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
    product_map = {
        "prod_concentrate": "کنسانتره سنگ آهن",
        "prod_pellet": "گندله",
        "prod_dri": "آهن اسفنجی",
        "prod_billet": "شمش فولادی",
        "prod_rebar": "میلگرد"
    }
    product_name = product_map.get(query.data)
    if not product_name:
        return
    user_data[query.from_user.id]["product"] = product_name
    await query.edit_message_text(
        f"📊 *محاسبه سود - {product_name}*\n\n💰 قیمت خرید خود را به *دلار* وارد کنید:\n(مثال: 95)",
        reply_markup=get_back_button("price"),
        parse_mode="Markdown"
    )
    return GET_PRICE

async def get_price(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        price = float(text)
        user_data[uid]["purchase"] = price
        nego_rate = get_usd_nego_rate_toman()
        free_rate = get_usd_free_rate_toman()
        await update.message.reply_text(
            f"💱 *نرخ دلار (تومان):*\n"
            f"   • مبادله‌ای (نیمایی): *{nego_rate:,}* تومان\n"
            f"   • بازار آزاد: *{free_rate:,}* تومان\n\n"
            f"0 = استفاده از نرخ مبادله‌ای\n"
            f"1 = استفاده از نرخ بازار آزاد\n"
            f"یا عدد دلخواه را وارد کنید:",
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
        text = update.message.text.replace(',', '').replace('،', '').strip()
        val = float(text)
        nego_rate = get_usd_nego_rate_toman()
        free_rate = get_usd_free_rate_toman()
        if val == 0:
            user_data[uid]["rate"] = nego_rate
            rate_type = "مبادله‌ای (نیمایی)"
        elif val == 1:
            user_data[uid]["rate"] = free_rate
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
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["tonnage"] = float(text)
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
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["freight"] = float(text)
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
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["port"] = float(text)
        d = user_data[uid]
        t = d["tonnage"]
        purchase = d["purchase"]
        freight = d["freight"]
        port = d["port"]
        rate = d["rate"]
        fob = purchase * 1.2
        revenue = fob * t
        total_cost = (purchase + freight + port) * t
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
⚓ پورت: ${port:,.0f}/تن
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
    product_name = user_data[uid]["product"]
    await query.edit_message_text(
        f"📊 *محاسبه سود - {product_name}*\n\n💰 قیمت خرید خود را به *دلار* وارد کنید:\n(مثال: 95)",
        reply_markup=get_back_button("price"),
        parse_mode="Markdown"
    )
    return GET_PRICE

async def back_to_rate(update: Update, context):
    query = update.callback_query
    await query.answer()
    nego_rate = get_usd_nego_rate_toman()
    free_rate = get_usd_free_rate_toman()
    await query.edit_message_text(
        f"💱 *نرخ دلار (تومان):*\n"
        f"   • مبادله‌ای: *{nego_rate:,}* تومان\n"
        f"   • بازار آزاد: *{free_rate:,}* تومان\n\n"
        f"0 = نرخ مبادله‌ای\n1 = نرخ بازار آزاد\nیا عدد دلخواه:",
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
async def scheduled_price_update(app):
    while True:
        try:
            await asyncio.sleep(21600)
            print("🔄 بروزرسانی خودکار قیمت‌های ایران...")
            await get_iran_prices()
            print("✅ بروزرسانی خودکار کامل شد")
        except Exception as e:
            print(f"❌ خطا در بروزرسانی خودکار: {e}")

# ========== اجرای اصلی ==========
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ توکن یافت نشد!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
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
    conv_handler = ConversationHandler(
        entry_points=[],
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
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    async def post_init(application):
        asyncio.create_task(scheduled_price_update(application))
        await get_iran_prices()
    
    app.post_init = post_init
    
    print("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
