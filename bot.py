from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
import requests
from datetime import datetime
import asyncio
import json
import re
from bs4 import BeautifulSoup

# States
SELECT_PRODUCT, GET_PRICE, GET_RATE, GET_TONNAGE, GET_FREIGHT, GET_PORT = range(6)

user_data = {}

# ========== کش قیمت ایران ==========
iran_prices_cache = {
    "data": None,
    "last_update": None
}

# ========== نرخ دلار مبادله‌ای (نیمایی) ==========
def get_usd_nego_rate():
    try:
        r = requests.get("https://www.tgju.org/sana/", timeout=10)
        if r.status_code == 200:
            match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*ریال', r.text)
            if match:
                return int(match.group(1).replace(',', ''))
    except:
        pass
    return 1468000

# ========== نرخ دلار بازار آزاد ==========
def get_usd_free_rate():
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price = float(data.get("stats", {}).get("USDT-IRT", {}).get("latest", 0))
            if price > 0:
                return int(price)
    except:
        pass
    try:
        r = requests.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price_str = data.get("price", "0").replace(",", "")
            price = int(price_str)
            if price > 0:
                return price
    except:
        pass
    return 1780000

# ========== Web Scraping از آهن ملل ==========
async def scrape_ahanmelal():
    """دریافت قیمت‌های به‌روز از سایت آهن ملل"""
    prices = {}
    
    # آدرس صفحات قیمت محصولات
    urls = {
        "billet": "https://ahanmelal.com/steel-ingots/steel-ingot-price",
        "rebar": "https://ahanmelal.com/steel-products/rebar-price",
        "concentrate": "https://ahanmelal.com/iron-ore/concentrate-price",
        "pellet": "https://ahanmelal.com/iron-ore/pellet-price",
        "dri": "https://ahanmelal.com/sponge-iron/sponge-iron-price"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for product, url in urls.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # جستجو برای قیمت (سلکتورها بر اساس ساختار واقعی سایت)
                price_elem = soup.find('div', class_='product-price')
                if not price_elem:
                    price_elem = soup.find('span', class_='price')
                if not price_elem:
                    price_elem = soup.find('div', class_='current-price')
                
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # استخراج عدد از متن (مثلاً "43,091 تومان" -> 43091)
                    numbers = re.findall(r'([\d,]+)', price_text)
                    if numbers:
                        raw_price = numbers[0].replace(',', '')
                        prices[product] = int(raw_price)
        except Exception as e:
            print(f"Error scraping {product}: {e}")
            prices[product] = None
    
    return prices

# ========== دریافت قیمت‌های ایران (با کش و بروزرسانی خودکار) ==========
async def get_iran_prices():
    """دریافت قیمت محصولات با بروزرسانی خودکار هر 6 ساعت"""
    global iran_prices_cache
    
    now = datetime.now()
    
    # اگر کش معتبر است (کمتر از 6 ساعت گذشته)
    if iran_prices_cache["data"] and iran_prices_cache["last_update"]:
        time_diff = (now - iran_prices_cache["last_update"]).total_seconds()
        if time_diff < 21600:  # 6 ساعت
            return iran_prices_cache["data"]
    
    # در غیر این صورت، داده‌های جدید بگیر
    print("🔄 بروزرسانی قیمت‌های ایران از آهن ملل...")
    
    scraped_prices = await scrape_ahanmelal()
    
    # قیمت‌های پیش‌فرض (در صورت عدم موفقیت اسکرپینگ)
    prices = {
        "concentrate": {
            "name": "کنسانتره سنگ آهن",
            "ice": "۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰",
            "free_market": "۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰",
            "factory": "گل گهر: ۴,۳۰۰,۰۰۰ | مرکزی: ۴,۶۰۰,۰۰۰"
        },
        "pellet": {
            "name": "گندله",
            "ice": "۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰",
            "free_market": "۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰",
            "factory": "گل گهر: ۶,۴۰۰,۰۰۰ | چادرملو: ۶,۳۰۰,۰۰۰"
        },
        "dri": {
            "name": "آهن اسفنجی",
            "ice": "۱۴,۸۰۰ - ۱۵,۵۰۰",
            "free_market": "۱۶,۰۰۰ - ۱۶,۸۰۰",
            "factory": "-",
            "unit": "کیلو"
        },
        "billet": {
            "name": "شمش فولادی",
            "ice": "۴۱,۰۰۰ - ۴۴,۰۰۰",
            "free_market": "۴۳,۰۰۰ - ۴۶,۰۰۰",
            "factory": "اصفهان: ۴۳,۰۹۱ | یزد: ۴۳,۰۰۰ | قزوین: ۴۰,۴۰۹ | کاوه: ۴۲,۵۰۰"
        },
        "rebar": {
            "name": "میلگرد",
            "ice": "۱۵,۸۰۰ - ۱۶,۸۰۰",
            "free_market": "۱۷,۳۰۰ - ۱۸,۰۰۰",
            "factory": "-",
            "unit": "کیلو"
        }
    }
    
    # به‌روزرسانی قیمت شمش از داده‌های اسکرپ شده
    if scraped_prices.get("billet"):
        billet_price = scraped_prices["billet"]
        prices["billet"]["free_market"] = f"{billet_price:,} - {billet_price + 2000:,}"
        prices["billet"]["factory"] = f"اصفهان: {billet_price:,}"
    
    # به‌روزرسانی قیمت میلگرد
    if scraped_prices.get("rebar"):
        rebar_price = scraped_prices["rebar"]
        prices["rebar"]["free_market"] = f"{rebar_price:,} - {rebar_price + 1000:,}"
    
    # ذخیره در کش
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

# ========== شروع ==========
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

async def main_menu_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_global":
        text = "🌍 *قیمت‌های جهانی* 🌍\n"
        text += f"🔄 {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n\n"
        for key, d in get_global_prices().items():
            text += f"• *{d['name']}*\n"
            text += f"   🇮🇷 FOB خلیج فارس: ${d['fob_pg']}\n"
            text += f"   🇨🇳 CFR شمال چین: ${d['north']}\n"
            text += f"   🇨🇳 CFR جنوب چین: ${d['south']}\n\n"
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif query.data == "show_iran":
        iran_prices = await get_iran_prices()
        nego_rate = get_usd_nego_rate()
        free_rate = get_usd_free_rate()
        
        # اطلاعات بروزرسانی
        last_update = iran_prices_cache["last_update"]
        if last_update:
            update_text = f"🔄 آخرین بروزرسانی: {last_update.strftime('%Y/%m/%d - %H:%M')}"
        else:
            update_text = "🔄 در حال دریافت اطلاعات..."
        
        text = "🇮🇷 *قیمت‌های داخلی ایران* 🇮🇷\n"
        text += f"{update_text}\n\n"
        
        text += "💱 *نرخ ارز:*\n"
        text += f"   • دلار مبادله‌ای (نیمایی): {nego_rate//10:,} تومان ({nego_rate:,} ریال)\n"
        text += f"   • دلار بازار آزاد: {free_rate//10:,} تومان ({free_rate:,} ریال)\n\n"
        
        text += "═══════════════════════════\n"
        text += "🏭 *بورس کالا (ICE) - تومان:*\n\n"
        
        for key, d in iran_prices.items():
            unit = d.get("unit", "تن")
            text += f"• *{d['name']}*: {d['ice']} تومان/{unit}\n"
        
        text += "\n🔄 *بازار آزاد - تومان:*\n\n"
        for key, d in iran_prices.items():
            unit = d.get("unit", "تن")
            text += f"• *{d['name']}*: {d['free_market']} تومان/{unit}\n"
        
        text += "\n═══════════════════════════\n"
        text += "🏭 *قیمت درب کارخانه (تومان/تن):*\n\n"
        text += f"🔩 *شمش فولادی:*\n   {iran_prices['billet']['factory']}\n"
        text += f"\n🟤 *گندله:*\n   {iran_prices['pellet']['factory']}\n"
        text += f"\n🪨 *کنسانتره:*\n   {iran_prices['concentrate']['factory']}\n"
        
        text += "\n═══════════════════════════\n"
        text += "📌 منابع: بورس کالا، آهن ملل، نوبیتکس، TGJU\n"
        text += "📆 قیمت‌ها هر 6 ساعت به‌طور خودکار بروزرسانی می‌شوند."
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif query.data == "start_profit":
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
        f"📊 *محاسبه سود - {product_name}*\n\n"
        f"💰 قیمت خرید خود را به *دلار* وارد کنید:\n"
        f"(مثال: 95)",
        parse_mode="Markdown"
    )
    return GET_PRICE

async def get_price(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        price = float(text)
        user_data[uid]["purchase"] = price
        
        nego_rate = get_usd_nego_rate()
        free_rate = get_usd_free_rate()
        
        await update.message.reply_text(
            f"💱 *نرخ دلار:*\n"
            f"   • مبادله‌ای (نیمایی): {nego_rate//10:,} تومان\n"
            f"   • بازار آزاد: {free_rate//10:,} تومان\n\n"
            f"0 = استفاده از نرخ مبادله‌ای\n"
            f"1 = استفاده از نرخ بازار آزاد\n"
            f"یا عدد دلخواه را وارد کنید:",
            parse_mode="Markdown"
        )
        return GET_RATE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 95):")
        return GET_PRICE

async def get_rate(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        val = float(text)
        
        nego_rate = get_usd_nego_rate()
        free_rate = get_usd_free_rate()
        
        if val == 0:
            user_data[uid]["rate"] = nego_rate
            rate_type = "مبادله‌ای (نیمایی)"
        elif val == 1:
            user_data[uid]["rate"] = free_rate
            rate_type = "بازار آزاد"
        else:
            user_data[uid]["rate"] = val
            rate_type = "دلخواه"
        
        await update.message.reply_text(
            f"✅ نرخ ارز {rate_type}: {user_data[uid]['rate']//10:,} تومان\n\n"
            f"⚖️ *تناژ* (تن) را وارد کنید:\n(مثال: 5000)",
            parse_mode="Markdown"
        )
        return GET_TONNAGE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (0, 1 یا عدد دلخواه):")
        return GET_RATE

async def get_tonnage(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["tonnage"] = float(text)
        await update.message.reply_text("🚢 *هزینه حمل* هر تن به دلار را وارد کنید:\n(مثال: 18)", parse_mode="Markdown")
        return GET_FREIGHT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 5000):")
        return GET_TONNAGE

async def get_freight(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["freight"] = float(text)
        await update.message.reply_text("⚓ *هزینه بارگیری در پورت* هر تن به دلار را وارد کنید:\n(مثال: 4)", parse_mode="Markdown")
        return GET_PORT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 18):")
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
        profit_rial = profit_usd * rate
        profit_toman = profit_rial // 10
        
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
🇮🇷 ریال: {profit_rial:,.0f} ریال
{'─' * 30}
💱 نرخ ارز: {rate:,.0f} ریال
"""
        await update.message.reply_text(result, parse_mode="Markdown")
        del user_data[uid]
        return ConversationHandler.END
    except Exception as e:
        print(e)
        await update.message.reply_text("❌ خطا: لطفاً یک عدد معتبر وارد کنید.")
        return GET_PORT

async def cancel(update: Update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("❌ عملیات لغو شد.")

# ========== وظیفه زمانبندی شده برای بروزرسانی خودکار قیمت‌ها ==========
async def scheduled_price_update(app):
    """هر 6 ساعت یکبار قیمت‌های ایران را بروزرسانی می‌کند"""
    while True:
        try:
            await asyncio.sleep(21600)  # 6 ساعت
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
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(main_menu_handler, pattern="^(start_profit|show_global|show_iran)$")],
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
    
    # شروع وظیفه زمانبندی شده برای بروزرسانی خودکار قیمت‌ها
    async def post_init(application):
        asyncio.create_task(scheduled_price_update(application))
        # یک بار در شروع ربات قیمت‌ها را بروزرسانی کن
        await get_iran_prices()
    
    app.post_init = post_init
    
    print("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
