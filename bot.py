from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
import requests
from datetime import datetime
import asyncio
from database import init_db, add_alert, get_active_alerts, deactivate_alert, save_price

# States
PRODUCT, PURCHASE, RATE_RIAL, RATE_DIRHAM, TONNAGE, FREIGHT, PORT = range(7)

user_data = {}

# ========== نرخ ارز ==========
def get_usd_rial_rate():
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        if r.status_code == 200:
            price = float(r.json().get("stats", {}).get("USDT-IRT", {}).get("latest", 0))
            if price > 0:
                return price
    except:
        pass
    return 65000

def get_usd_dirham_rate():
    try:
        r = requests.get("https://api.exchangerate.fun/latest?base=USD", timeout=5)
        if r.status_code == 200:
            return float(r.json().get("rates", {}).get("AED", 3.67))
    except:
        pass
    return 3.67

# ========== قیمت‌های جهانی ==========
def get_global_prices():
    prices = {
        "iron_ore_62": {"name": "سنگ آهن 62%", "north": 111.5, "south": 112.0},
        "fe_65": {"name": "Fe 65%", "north": 135.0, "south": 135.5},
        "pellet": {"name": "گندله", "north": 156.5, "south": 158.0},
        "billet": {"name": "بیلت", "north": 530, "south": 520}
    }
    
    for key, data in prices.items():
        save_price(data["name"] + " شمال", "north", data["north"])
        save_price(data["name"] + " جنوب", "south", data["south"])
    
    return prices

# ========== بررسی هشدارها ==========
async def check_alerts(app):
    """بررسی دوره‌ای هشدارها"""
    while True:
        try:
            await asyncio.sleep(900)  # 15 دقیقه
            prices = get_global_prices()
            alerts = get_active_alerts()
            
            for alert in alerts:
                alert_id, user_id, product, port, condition, target = alert
                
                current_price = None
                for key, data in prices.items():
                    if data["name"] == product:
                        current_price = data[port]
                        break
                
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
                                     f"محصول: {product}\n"
                                     f"بندر: {port}\n"
                                     f"شرط: {condition} {target}\n"
                                     f"💰 قیمت فعلی: {current_price} دلار\n\n"
                                     f"⏰ {datetime.now().strftime('%Y/%m/%d - %H:%M')}",
                                parse_mode="Markdown"
                            )
                            deactivate_alert(alert_id)
                        except Exception as e:
                            print(f"خطا در ارسال هشدار به {user_id}: {e}")
        except Exception as e:
            print(f"خطا در بررسی هشدارها: {e}")

# ========== شروع ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="new_profit")],
        [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data="set_alert")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="global_price")]
    ]
    await update.message.reply_text(
        "ربات تخصصی سنگ آهن و فلزات\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== قیمت جهانی ==========
async def global_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    prices = get_global_prices()
    text = "🌍 *قیمت‌های لحظه‌ای* 🌍\n\n"
    
    for key, data in prices.items():
        text += f"📌 {data['name']}:\n"
        text += f"   شمال: {data['north']} دلار\n"
        text += f"   جنوب: {data['south']} دلار\n\n"
    
    text += f"💱 نرخ دلار: {get_usd_rial_rate():,.0f} ریال\n"
    text += f"📆 {datetime.now().strftime('%Y/%m/%d - %H:%M')}"
    
    await query.edit_message_text(text, parse_mode="Markdown")

# ========== تنظیم هشدار ==========
async def set_alert_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["alert_step"] = "product"
    await query.edit_message_text(
        "🔔 *تنظیم هشدار قیمتی*\n\n"
        "لطفاً محصول را وارد کنید:\n"
        "گزینه‌ها: سنگ آهن 62% , Fe 65% , گندله , بیلت",
        parse_mode="Markdown"
    )

async def alert_product(update: Update, context):
    product = update.message.text
    context.user_data["alert_product"] = product
    context.user_data["alert_step"] = "port"
    await update.message.reply_text("بندر را انتخاب کنید:\nگزینه‌ها: north , south")

async def alert_port(update: Update, context):
    port = update.message.text.lower()
    if port not in ["north", "south"]:
        await update.message.reply_text("لطفاً north یا south را وارد کنید:")
        return
    context.user_data["alert_port"] = port
    context.user_data["alert_step"] = "condition"
    await update.message.reply_text("شرط را وارد کنید:\nگزینه‌ها: below (کمتر از) , above (بیشتر از)")

async def alert_condition(update: Update, context):
    condition = update.message.text.lower()
    if condition not in ["below", "above"]:
        await update.message.reply_text("لطفاً below یا above را وارد کنید:")
        return
    context.user_data["alert_condition"] = condition
    context.user_data["alert_step"] = "price"
    await update.message.reply_text("قیمت هدف را به دلار وارد کنید (مثال: 110):")

async def alert_price(update: Update, context):
    try:
        target = float(update.message.text)
        user_id = update.effective_user.id
        product = context.user_data["alert_product"]
        port = context.user_data["alert_port"]
        condition = context.user_data["alert_condition"]
        
        alert_id = add_alert(user_id, product, port, condition, target)
        
        await update.message.reply_text(
            f"✅ *هشدار با موفقیت ثبت شد!*\n\n"
            f"شناسه: {alert_id}\n"
            f"محصول: {product}\n"
            f"بندر: {port}\n"
            f"شرط: {condition} {target} دلار\n\n"
            f"🔔 هر 15 دقیقه قیمت‌ها بررسی می‌شوند.",
            parse_mode="Markdown"
        )
        del context.user_data["alert_step"]
    except:
        await update.message.reply_text("عدد معتبر وارد کنید:")

# ========== محاسبه سود ==========
async def profit_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {}
    
    keyboard = [
        [InlineKeyboardButton("Iron Ore 62%", callback_data="prod_1")],
        [InlineKeyboardButton("Fe 65%", callback_data="prod_2")],
        [InlineKeyboardButton("Pellet", callback_data="prod_3")],
        [InlineKeyboardButton("Billet", callback_data="prod_4")],
    ]
    await query.edit_message_text("محصول را انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PRODUCT

async def product_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    products = {"prod_1": "Iron Ore 62%", "prod_2": "Fe 65%", "prod_3": "Pellet", "prod_4": "Billet"}
    user_data[query.from_user.id]["product"] = products[query.data]
    await query.edit_message_text("قیمت خرید هر تن به دلار؟ (مثال: 95)")
    return PURCHASE

async def get_purchase(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["purchase"] = float(update.message.text)
        await update.message.reply_text(f"نرخ دلار آزاد: {get_usd_rial_rate():,.0f} ریال\n0=همین نرخ، یا عدد دلخواه:")
        return RATE_RIAL
    except:
        await update.message.reply_text("عدد وارد کن")
        return PURCHASE

async def get_rate_rial(update: Update, context):
    uid = update.effective_user.id
    try:
        val = float(update.message.text)
        user_data[uid]["rate_rial"] = val if val != 0 else get_usd_rial_rate()
        await update.message.reply_text(f"نرخ درهم: {get_usd_dirham_rate():.2f}\n0=همین نرخ، یا عدد دلخواه:")
        return RATE_DIRHAM
    except:
        await update.message.reply_text("عدد وارد کن")
        return RATE_RIAL

async def get_rate_dirham(update: Update, context):
    uid = update.effective_user.id
    try:
        val = float(update.message.text)
        user_data[uid]["rate_dirham"] = val if val != 0 else get_usd_dirham_rate()
        await update.message.reply_text("چند تن؟ (مثال: 5000)")
        return TONNAGE
    except:
        await update.message.reply_text("عدد وارد کن")
        return RATE_DIRHAM

async def get_tonnage(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["tonnage"] = float(update.message.text)
        await update.message.reply_text("هزینه حمل هر تن به دلار؟ (مثال: 18)")
        return FREIGHT
    except:
        await update.message.reply_text("عدد وارد کن")
        return TONNAGE

async def get_freight(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["freight"] = float(update.message.text)
        await update.message.reply_text("هزینه بارگیری در پورت هر تن به دلار؟ (مثال: 4)")
        return PORT
    except:
        await update.message.reply_text("عدد وارد کن")
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
        rate_dirham = d["rate_dirham"]
        
        fob = purchase * 1.2
        revenue_usd = fob * t
        total_cost_usd = (purchase + freight + port) * t
        profit_usd = revenue_usd - total_cost_usd
        profit_rial = profit_usd * rate_rial
        profit_dirham = profit_usd * rate_dirham
        
        now = datetime.now().strftime("%Y/%m/%d - %H:%M")
        
        result = f"""
📊 **نتیجه محاسبه سود**
📅 {now}
─────────────────
📦 محصول: {d['product']}
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
✅ **سود خالص:**
🇺🇸 دلار: ${profit_usd:,.0f}
🇮🇷 ریال: {profit_rial:,.0f}
🇦🇪 درهم: {profit_dirham:,.0f}
─────────────────
💱 نرخ دلار آزاد: {rate_rial:,.0f} ریال
💱 نرخ دلار به درهم: {rate_dirham:.2f}
"""
        await update.message.reply_text(result, parse_mode="Markdown")
        del user_data[uid]
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}\nعدد وارد کن")
        return PORT

async def cancel(update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("لغو شد.")

# ========== اجرای اصلی ==========
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("توکن نداریم")
        return
    
    # راه‌اندازی دیتابیس
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
            PRODUCT: [CallbackQueryHandler(product_choice, pattern="^prod_")],
            PURCHASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_purchase)],
            RATE_RIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate_rial)],
            RATE_DIRHAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate_dirham)],
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
    
    # ✅ راه‌اندازی صحیح تسک بررسی هشدارها
    async def post_start():
        asyncio.create_task(check_alerts(app))
    
    app.post_init = post_start
    
    print("ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
