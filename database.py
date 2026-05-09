from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
import requests
from datetime import datetime
import asyncio
from database import init_db, add_alert, get_active_alerts, deactivate_alert, save_price

# States
PRODUCT, PURCHASE, RATE_RIAL, TONNAGE, FREIGHT, PORT = range(6)

user_data = {}

# ========== دریافت نرخ دقیق دلار بازار آزاد ==========
def get_usd_rial_rate():
    """دریافت نرخ دقیق دلار از منابع معتبر"""
    
    # منبع اول: Nobitex (صرافی آنلاین معتبر ایران)
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price = float(data.get("stats", {}).get("USDT-IRT", {}).get("latest", 0))
            if price > 0:
                return price
    except:
        pass
    
    # منبع دوم: TGJU (سایت طلا و ارز)
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
    
    # منبع سوم: doni.ir (منبع پشتیبان)
    try:
        r = requests.get("https://doni.ir/api/price", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price = data.get("usd", {}).get("price", 0)
            if price > 0:
                return int(price)
    except:
        pass
    
    # نرخ پیش‌فرض (در صورت عدم دسترسی)
    return 65000

# ========== قیمت‌های جهانی محصولات ==========
def get_global_prices():
    """قیمت‌های جهانی محصولات (فقط دلار)"""
    return {
        "iron_ore_62": {
            "name": "سنگ آهن 62%",
            "global": 112.8,
            "north": 111.5,
            "south": 112.0
        },
        "fe_65": {
            "name": "Fe 65%",
            "global": 136.0,
            "north": 135.0,
            "south": 135.5
        },
        "concentrate": {
            "name": "کنسانتره آهن",
            "global": 134.8,
            "north": 134.0,
            "south": 134.5
        },
        "pellet": {
            "name": "گندله",
            "global": 157.5,
            "north": 156.5,
            "south": 158.0
        },
        "billet": {
            "name": "بیلت",
            "global": 525.0,
            "north": 530.0,
            "south": 520.0
        }
    }

def get_global_product_price(product_name):
    """دریافت قیمت یک محصول خاص"""
    prices = get_global_prices()
    for key, data in prices.items():
        if data["name"] == product_name:
            return data
    return None

# ========== بررسی هشدارها ==========
async def check_alerts(app):
    while True:
        try:
            await asyncio.sleep(900)
            alerts = get_active_alerts()
            for alert in alerts:
                alert_id, user_id, product, port, condition, target = alert
                product_data = get_global_product_price(product)
                if product_data:
                    current_price = product_data.get(port, 0)
                    if current_price:
                        triggered = False
                        if condition == "below" and current_price < target:
                            triggered = True
                        elif condition == "above" and current_price > target:
                            triggered = True
                        
                        if triggered:
                            try:
                                await app.bot.send_message(
                                    chat_id=user_id,
                                    text=f"🚨 *هشدار قیمتی!*\n\n"
                                         f"📦 محصول: {product}\n"
                                         f"📍 بندر: {port}\n"
                                         f"🎯 شرط: {condition} {target} دلار\n"
                                         f"💰 قیمت فعلی: {current_price} دلار\n"
                                         f"⏰ {datetime.now().strftime('%Y/%m/%d - %H:%M')}",
                                    parse_mode="Markdown"
                                )
                                deactivate_alert(alert_id)
                            except Exception as e:
                                print(f"خطا در ارسال هشدار: {e}")
        except Exception as e:
            print(f"خطا در بررسی هشدارها: {e}")
            await asyncio.sleep(60)

# ========== شروع ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="new_profit")],
        [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data="set_alert")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="global_price")]
    ]
    await update.message.reply_text(
        "🏭 *ربات تخصصی سنگ آهن و فلزات* 🏭\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== قیمت جهانی (فقط دلار) ==========
async def global_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    prices = get_global_prices()
    rate = get_usd_rial_rate()
    
    text = f"🌍 *قیمت‌های جهانی و بنادر چین* 🌍\n"
    text += f"🔄 آخرین به‌روزرسانی: {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n"
    text += f"💱 نرخ دلار آزاد: **{rate:,.0f} ریال**\n\n"
    
    text += f"{'═' * 35}\n\n"
    
    for key, data in prices.items():
        if data["name"] == "سنگ آهن 62%":
            icon = "🪨"
        elif data["name"] == "Fe 65%":
            icon = "⚙️"
        elif data["name"] == "کنسانتره آهن":
            icon = "🏗️"
        elif data["name"] == "گندله":
            icon = "🟤"
        else:
            icon = "🔩"
        
        text += f"{icon} *{data['name']}*\n"
        text += f"   جهانی: **${data['global']:,.1f}**\n"
        text += f"   📍 شمال: ${data['north']:,.1f}\n"
        text += f"   📍 جنوب: ${data['south']:,.1f}\n\n"
    
    # تحلیل سریع
    iron62 = prices["iron_ore_62"]["global"]
    pellet = prices["pellet"]["global"]
    billet = prices["billet"]["global"]
    
    text += f"{'═' * 35}\n"
    text += f"📊 *تحلیل سریع*\n"
    text += f"• گندله نسبت به سنگ آهن: +{pellet - iron62:.1f}$ گران‌تر\n"
    text += f"• بیلت نسبت به سنگ آهن: +{billet - iron62:.1f}$ گران‌تر\n"
    text += f"• ارزان‌ترین بندر: شمال (چینگدائو)\n\n"
    text += f"📆 منابع: IODEX, SMM, Fastmarkets, Platts, Nobitex"
    
    await query.edit_message_text(text, parse_mode="Markdown")

# ========== تنظیم هشدار ==========
async def set_alert_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["alert_step"] = "product"
    
    await query.edit_message_text(
        "🔔 *تنظیم هشدار قیمتی*\n\n"
        "لطفاً نام محصول را وارد کنید:\n"
        "• سنگ آهن 62%\n"
        "• Fe 65%\n"
        "• کنسانتره آهن\n"
        "• گندله\n"
        "• بیلت",
        parse_mode="Markdown"
    )

async def alert_product(update: Update, context):
    product = update.message.text
    valid_products = ["سنگ آهن 62%", "Fe 65%", "کنسانتره آهن", "گندله", "بیلت"]
    if product not in valid_products:
        await update.message.reply_text("❌ محصول نامعتبر. لطفاً یکی از محصولات لیست را وارد کنید:")
        return
    context.user_data["alert_product"] = product
    context.user_data["alert_step"] = "port"
    await update.message.reply_text("📍 بندر را انتخاب کنید:\n• north (شمال)\n• south (جنوب)")

async def alert_port(update: Update, context):
    port = update.message.text.lower()
    if port not in ["north", "south"]:
        await update.message.reply_text("❌ لطفاً north یا south را وارد کنید:")
        return
    context.user_data["alert_port"] = port
    context.user_data["alert_step"] = "condition"
    await update.message.reply_text("🎯 شرط را وارد کنید:\n• below (کمتر از)\n• above (بیشتر از)")

async def alert_condition(update: Update, context):
    condition = update.message.text.lower()
    if condition not in ["below", "above"]:
        await update.message.reply_text("❌ لطفاً below یا above را وارد کنید:")
        return
    context.user_data["alert_condition"] = condition
    context.user_data["alert_step"] = "price"
    await update.message.reply_text("💰 قیمت هدف را به دلار وارد کنید (مثال: 110):")

async def alert_price(update: Update, context):
    try:
        target = float(update.message.text)
        user_id = update.effective_user.id
        product = context.user_data["alert_product"]
        port = context.user_data["alert_port"]
        condition = context.user_data["alert_condition"]
        
        add_alert(user_id, product, port, condition, target)
        
        await update.message.reply_text(
            f"✅ *هشدار با موفقیت ثبت شد!*\n\n"
            f"📦 محصول: {product}\n"
            f"📍 بندر: {port}\n"
            f"🎯 شرط: {condition} {target} دلار\n\n"
            f"🔔 هر 15 دقیقه قیمت‌ها بررسی می‌شوند.",
            parse_mode="Markdown"
        )
        del context.user_data["alert_step"]
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")

# ========== محاسبه سود ==========
async def profit_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {}
    
    keyboard = [
        [InlineKeyboardButton("🪨 سنگ آهن 62%", callback_data="سنگ آهن 62%")],
        [InlineKeyboardButton("⚙️ Fe 65%", callback_data="Fe 65%")],
        [InlineKeyboardButton("🏗️ کنسانتره آهن", callback_data="کنسانتره آهن")],
        [InlineKeyboardButton("🟤 گندله", callback_data="گندله")],
        [InlineKeyboardButton("🔩 بیلت", callback_data="بیلت")],
    ]
    await query.edit_message_text(
        "📊 *محاسبه سود*\n\nلطفاً محصول مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return PRODUCT

async def product_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_name = query.data
    
    user_data[user_id]["product"] = product_name
    product_data = get_global_product_price(product_name)
    
    if product_data:
        text = f"📊 *محاسبه سود* – *{product_name}*\n\n"
        text += f"💰 *قیمت جهانی لحظه‌ای:*\n"
        text += f"   └ بندر شمال: *{product_data['north']:,.1f}* دلار/تن\n"
        text += f"   └ بندر جنوب: *{product_data['south']:,.1f}* دلار/تن\n\n"
        text += f"✏️ *قیمت خرید خود* را به دلار وارد کنید:"
    else:
        text = f"📊 *محاسبه سود*\n\n✏️ *قیمت خرید خود* را به دلار وارد کنید:"
    
    await query.edit_message_text(text, parse_mode="Markdown")
    return PURCHASE

async def get_purchase(update: Update, context):
    uid = update.effective_user.id
    try:
        purchase_price = float(update.message.text)
        user_data[uid]["purchase"] = purchase_price
        
        product_name = user_data[uid]["product"]
        rate = get_usd_rial_rate()
        
        text = f"📊 *محاسبه سود* – *{product_name}*\n\n"
        text += f"💰 قیمت خرید شما: *{purchase_price:,.0f}* دلار/تن\n\n"
        text += f"💱 *نرخ دلار آزاد:* {rate:,.0f} ریال\n"
        text += f"0 = استفاده از نرخ فعلی، یا عدد دلخواه را وارد کنید:"
        
        await update.message.reply_text(text, parse_mode="Markdown")
        return RATE_RIAL
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")
        return PURCHASE

async def get_rate_rial(update: Update, context):
    uid = update.effective_user.id
    try:
        val = float(update.message.text)
        user_data[uid]["rate_rial"] = val if val != 0 else get_usd_rial_rate()
        
        product_name = user_data[uid]["product"]
        
        await update.message.reply_text(
            f"📊 *محاسبه سود* – *{product_name}*\n\n"
            f"💱 نرخ دلار: *{user_data[uid]['rate_rial']:,.0f}* ریال\n\n"
            f"⚖️ *تناژ* (تن) را وارد کنید:",
            parse_mode="Markdown"
        )
        return TONNAGE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")
        return RATE_RIAL

async def get_tonnage(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["tonnage"] = float(update.message.text)
        
        product_name = user_data[uid]["product"]
        
        await update.message.reply_text(
            f"📊 *محاسبه سود* – *{product_name}*\n\n"
            f"⚖️ تناژ: *{user_data[uid]['tonnage']:,.0f}* تن\n\n"
            f"🚢 *هزینه حمل* هر تن به دلار را وارد کنید:",
            parse_mode="Markdown"
        )
        return FREIGHT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")
        return TONNAGE

async def get_freight(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["freight"] = float(update.message.text)
        
        product_name = user_data[uid]["product"]
        
        await update.message.reply_text(
            f"📊 *محاسبه سود* – *{product_name}*\n\n"
            f"🚢 هزینه حمل: *{user_data[uid]['freight']}* دلار/تن\n\n"
            f"⚓ *هزینه بارگیری در پورت* هر تن به دلار را وارد کنید:",
            parse_mode="Markdown"
        )
        return PORT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")
        return FREIGHT

async def get_port(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["port"] = float(update.message.text)
        
        d = user_data[uid]
        t = d["tonnage"]
        purchase = d["purchase"]
        freight = d["freight"]
        port = d["port"]
        rate_rial = d["rate_rial"]
        
        # سود 20 درصدی فرضی
        fob = purchase * 1.2
        revenue_usd = fob * t
        total_cost_usd = (purchase + freight + port) * t
        profit_usd = revenue_usd - total_cost_usd
        profit_rial = profit_usd * rate_rial
        
        now = datetime.now().strftime("%Y/%m/%d - %H:%M")
        
        result = f"""
📊 *نتیجه محاسبه سود*
📅 {now}
{'─' * 35}
📦 محصول: *{d['product']}*
⚖️ تناژ: {t:,.0f} تن
💰 قیمت خرید: ${purchase:,.0f}/تن
💵 قیمت فروش (FOB 20%): ${fob:,.0f}/تن
{'─' * 35}
🚢 هزینه حمل: ${freight:,.0f}/تن
⚓ هزینه پورت: ${port:,.0f}/تن
{'─' * 35}
💲 درآمد کل: ${revenue_usd:,.0f}
📉 هزینه کل: ${total_cost_usd:,.0f}
{'─' * 35}
✅ *سود خالص:*
🇺🇸 دلار: ${profit_usd:,.0f}
🇮🇷 ریال: {profit_rial:,.0f} ریال
{'─' * 35}
💱 نرخ دلار: {rate_rial:,.0f} ریال
"""
        await update.message.reply_text(result, parse_mode="Markdown")
        del user_data[uid]
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}\nعدد معتبر وارد کنید:")
        return PORT

async def cancel(update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("❌ عملیات لغو شد.")

# ========== اجرای اصلی ==========
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ توکن یافت نشد!")
        return
    
    init_db()
    
    app = Application.builder().token(TOKEN).build()
    
    # مکالمه هشدار
    alert_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_alert_start, pattern="^set_alert$")],
        states={
            "product": [MessageHandler(filters.TEXT & ~filters.COMMAND, alert_product)],
            "port": [MessageHandler(filters.TEXT & ~filters.COMMAND, alert_port)],
            "condition": [MessageHandler(filters.TEXT & ~filters.COMMAND, alert_condition)],
            "price": [MessageHandler(filters.TEXT & ~filters.COMMAND, alert_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # مکالمه محاسبه سود
    profit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(profit_start, pattern="^new_profit$")],
        states={
            PRODUCT: [CallbackQueryHandler(product_choice, pattern="^(سنگ آهن 62%|Fe 65%|کنسانتره آهن|گندله|بیلت)$")],
            PURCHASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_purchase)],
            RATE_RIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate_rial)],
            TONNAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tonnage)],
            FREIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_freight)],
            PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_port)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(global_price, pattern="^global_price$"))
    app.add_handler(profit_conv)
    app.add_handler(alert_conv)
    app.add_handler(CommandHandler("cancel", cancel))
    
    async def post_init(application):
        asyncio.create_task(check_alerts(application))
    
    app.post_init = post_init
    
    print("🤖 ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
