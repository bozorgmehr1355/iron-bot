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

# ========== قیمت‌های جهانی محصولات ==========
def get_global_product_price(product_name):
    """دریافت قیمت جهانی محصول بر اساس نام محصول"""
    prices = {
        "Iron Ore 62%": {"north": 111.5, "south": 112.0},
        "Fe 65%": {"north": 135.0, "south": 135.5},
        "Pellet": {"north": 156.5, "south": 158.0},
        "Billet": {"north": 530, "south": 520}
    }
    return prices.get(product_name, {"north": 0, "south": 0})

# ========== نرخ ارز دقیق (چند منبع) ==========
def get_usd_rial_rate():
    """دریافت نرخ دقیق دلار از چند منبع معتبر"""
    
    # منبع اول: nobitex
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        if r.status_code == 200:
            price = float(r.json().get("stats", {}).get("USDT-IRT", {}).get("latest", 0))
            if price > 0:
                return price
    except:
        pass
    
    # منبع دوم: tgju
    try:
        r = requests.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5)
        if r.status_code == 200:
            price = float(r.json().get("price", 0))
            if price > 0:
                return price
    except:
        pass
    
    # منبع سوم: نرخ پیش‌فرض
    return 65000

# ========== بررسی هشدارها ==========
async def check_alerts(app):
    while True:
        try:
            await asyncio.sleep(900)
            alerts = get_active_alerts()
            for alert in alerts:
                alert_id, user_id, product, port, condition, target = alert
                prices = get_global_product_price(product)
                current_price = prices.get(port, 0)
                
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
                                text=f"🚨 *هشدار قیمتی!*\n\nمحصول: {product}\nبندر: {port}\nشرط: {condition} {target}\n💰 قیمت فعلی: {current_price} دلار\n⏰ {datetime.now().strftime('%Y/%m/%d - %H:%M')}",
                                parse_mode="Markdown"
                            )
                            deactivate_alert(alert_id)
                        except Exception as e:
                            print(f"خطا: {e}")
        except Exception as e:
            print(f"خطا: {e}")

# ========== شروع ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="new_profit")],
        [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data="set_alert")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="global_price")]
    ]
    await update.message.reply_text(
        "🏭 *ربات تخصصی سنگ آهن و فلزات* 🏭\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== قیمت جهانی ==========
async def global_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    prices = {
        "سنگ آهن 62%": get_global_product_price("Iron Ore 62%"),
        "Fe 65%": get_global_product_price("Fe 65%"),
        "گندله": get_global_product_price("Pellet"),
        "بیلت": get_global_product_price("Billet"),
    }
    
    text = "🌍 *قیمت‌های لحظه‌ای جهانی* 🌍\n\n"
    for name, data in prices.items():
        text += f"📌 *{name}*:\n"
        text += f"   └ بندر شمال: {data['north']} دلار/تن\n"
        text += f"   └ بندر جنوب: {data['south']} دلار/تن\n\n"
    
    text += f"💱 *نرخ دلار آزاد:* {get_usd_rial_rate():,.0f} ریال\n"
    text += f"📅 *بروزرسانی:* {datetime.now().strftime('%H:%M - %Y/%m/%d')}"
    
    await query.edit_message_text(text, parse_mode="Markdown")

# ========== تنظیم هشدار ==========
async def set_alert_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["alert_step"] = "product"
    await query.edit_message_text(
        "🔔 *تنظیم هشدار قیمتی*\n\nلطفاً نام محصول را وارد کنید:\nگزینه‌ها: Iron Ore 62% , Fe 65% , Pellet , Billet",
        parse_mode="Markdown"
    )

async def alert_product(update: Update, context):
    product = update.message.text
    context.user_data["alert_product"] = product
    context.user_data["alert_step"] = "port"
    await update.message.reply_text("بندر را انتخاب کنید:\n north (شمال) یا south (جنوب)")

async def alert_port(update: Update, context):
    port = update.message.text.lower()
    if port not in ["north", "south"]:
        await update.message.reply_text("لطفاً north یا south را وارد کنید:")
        return
    context.user_data["alert_port"] = port
    context.user_data["alert_step"] = "condition"
    await update.message.reply_text("شرط را وارد کنید:\n below (کمتر از) یا above (بیشتر از)")

async def alert_condition(update: Update, context):
    condition = update.message.text.lower()
    if condition not in ["below", "above"]:
        await update.message.reply_text("لطفاً below یا above را وارد کنید:")
        return
    context.user_data["alert_condition"] = condition
    context.user_data["alert_step"] = "price"
    await update.message.reply_text("قیمت هدف را به دلار وارد کنید:")

async def alert_price(update: Update, context):
    try:
        target = float(update.message.text)
        user_id = update.effective_user.id
        product = context.user_data["alert_product"]
        port = context.user_data["alert_port"]
        condition = context.user_data["alert_condition"]
        
        add_alert(user_id, product, port, condition, target)
        
        await update.message.reply_text(
            f"✅ *هشدار ثبت شد!*\n\nمحصول: {product}\nبندر: {port}\nشرط: {condition} {target} دلار\n\n🔔 هر 15 دقیقه بررسی می‌شود.",
            parse_mode="Markdown"
        )
        del context.user_data["alert_step"]
    except:
        await update.message.reply_text("عدد معتبر وارد کنید:")

# ========== محاسبه سود (اصلاح شده) ==========
async def profit_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {}
    
    keyboard = [
        [InlineKeyboardButton("🪨 Iron Ore 62%", callback_data="Iron Ore 62%")],
        [InlineKeyboardButton("⚙️ Fe 65%", callback_data="Fe 65%")],
        [InlineKeyboardButton("🟤 Pellet", callback_data="Pellet")],
        [InlineKeyboardButton("🔩 Billet", callback_data="Billet")],
    ]
    await query.edit_message_text(
        "📊 *محاسبه سود* - مرحله 1/6\n\nلطفاً محصول را انتخاب کنید:",
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
    
    # نمایش قیمت جهانی محصول
    global_price = get_global_product_price(product_name)
    
    await query.edit_message_text(
        f"📊 *محاسبه سود* - مرحله 2/6\n\n"
        f"📦 محصول انتخاب شده: *{product_name}*\n\n"
        f"💰 *قیمت جهانی:*\n"
        f"   └ بندر شمال: {global_price['north']} دلار/تن\n"
        f"   └ بندر جنوب: {global_price['south']} دلار/تن\n\n"
        f"✏️ حالا *قیمت خرید خود* را به دلار وارد کنید:",
        parse_mode="Markdown"
    )
    return PURCHASE

async def get_purchase(update: Update, context):
    uid = update.effective_user.id
    try:
        purchase_price = float(update.message.text)
        user_data[uid]["purchase"] = purchase_price
        
        product_name = user_data[uid]["product"]
        global_price = get_global_product_price(product_name)
        
        await update.message.reply_text(
            f"📊 *محاسبه سود* - مرحله 3/6\n\n"
            f"📦 محصول: *{product_name}*\n"
            f"💰 قیمت خرید شما: *{purchase_price}* دلار/تن\n"
            f"🌍 قیمت جهانی: {global_price['north']} دلار/تن (شمال)\n\n"
            f"💱 *نرخ دلار آزاد:* {get_usd_rial_rate():,.0f} ریال\n"
            f"0 = استفاده از نرخ فعلی، یا عدد دلخواه را وارد کنید:",
            parse_mode="Markdown"
        )
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
            f"📊 *محاسبه سود* - مرحله 4/6\n\n"
            f"📦 محصول: *{product_name}*\n"
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
            f"📊 *محاسبه سود* - مرحله 5/6\n\n"
            f"📦 محصول: *{product_name}*\n"
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
            f"📊 *محاسبه سود* - مرحله 6/6\n\n"
            f"📦 محصول: *{product_name}*\n"
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
        
        # محاسبه سود (20% سود فرضی روی قیمت خرید)
        fob = purchase * 1.2
        revenue_usd = fob * t
        total_cost_usd = (purchase + freight + port) * t
        profit_usd = revenue_usd - total_cost_usd
        profit_rial = profit_usd * rate_rial
        
        now = datetime.now().strftime("%Y/%m/%d - %H:%M")
        
        result = f"""
📊 *نتیجه محاسبه سود*
📅 {now}
─────────────────
📦 محصول: *{d['product']}*
⚖️ تناژ: {t:,.0f} تن
💰 قیمت خرید: ${purchase:,.0f}/تن
💵 قیمت فروش (FOB): ${fob:,.0f}/تن
─────────────────
🚢 هزینه حمل: ${freight:,.0f}/تن
⚓ هزینه پورت: ${port:,.0f}/تن
─────────────────
💲 درآمد کل: ${revenue_usd:,.0f}
📉 هزینه کل: ${total_cost_usd:,.0f}
─────────────────
✅ *سود خالص:*
🇺🇸 دلار: ${profit_usd:,.0f}
🇮🇷 ریال: {profit_rial:,.0f} ریال
─────────────────
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
        print("توکن نداریم")
        return
    
    init_db()
    
    app = Application.builder().token(TOKEN).build()
    
    # هشدار
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
    
    # محاسبه سود
    profit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(profit_start, pattern="^new_profit$")],
        states={
            PRODUCT: [CallbackQueryHandler(product_choice, pattern="^(Iron Ore 62%|Fe 65%|Pellet|Billet)$")],
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
    
    print("ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
