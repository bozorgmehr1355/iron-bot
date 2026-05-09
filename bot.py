from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
import requests
from datetime import datetime
import asyncio
import database
from database import init_db, add_alert, get_active_alerts, deactivate_alert

PRODUCT, PURCHASE, RATE_RIAL, TONNAGE, FREIGHT, PORT = range(6)
user_data = {}

# ========== نرخ دقیق بازار آزاد (Free Market Rate) ==========
def get_usd_rial_rate():
    """دریافت نرخ دقیق دلار بازار آزاد از منابع معتبر."""
    # منبع اول: Nobitex
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price = float(data.get("stats", {}).get("USDT-IRT", {}).get("latest", 0))
            if price > 0:
                return int(price)
    except Exception as e:
        print(f"Nobitex API error: {e}")
    
    # منبع دوم: TGJU
    try:
        r = requests.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price_str = data.get("price", "0").replace(",", "")
            price = int(price_str)
            if price > 0:
                return price
    except Exception as e:
        print(f"TGJU API error: {e}")

    # Fallback: نرخ تخمینی روز (با توجه به اطلاعات جستجو شده، حدود 1,315,000)
    print("Warning: Could not fetch live rate, using fallback value.")
    return 1315000

# ========== قیمت‌های جهانی ==========
def get_global_prices():
    rate = get_usd_rial_rate()
    return {
        "iron_ore_62": {
            "name": "سنگ آهن ۶۲٪", "global": 112.8, "north": 111.5, "south": 112.0, "fob_pg": 89.5,
            "north_rial": int(111.5 * rate), "south_rial": int(112.0 * rate), "fob_rial": int(89.5 * rate)
        },
        "fe_65": {
            "name": "کنسانتره آهن ۶۵٪", "global": 136.0, "north": 135.0, "south": 135.5, "fob_pg": 95.0,
            "north_rial": int(135.0 * rate), "south_rial": int(135.5 * rate), "fob_rial": int(95.0 * rate)
        },
        "concentrate": {
            "name": "کنسانتره آهن", "global": 134.8, "north": 134.0, "south": 134.5, "fob_pg": 90.0,
            "north_rial": int(134.0 * rate), "south_rial": int(134.5 * rate), "fob_rial": int(90.0 * rate)
        },
        "pellet": {
            "name": "گندله", "global": 157.5, "north": 156.5, "south": 158.0, "fob_pg": 110.0,
            "north_rial": int(156.5 * rate), "south_rial": int(158.0 * rate), "fob_rial": int(110.0 * rate)
        },
        "billet": {
            "name": "بیلت", "global": 525.0, "north": 530.0, "south": 520.0, "fob_pg": 480.0,
            "north_rial": int(530.0 * rate), "south_rial": int(520.0 * rate), "fob_rial": int(480.0 * rate)
        }
    }

def get_global_product_price(product_name):
    for data in get_global_prices().values():
        if data["name"] == product_name:
            return data
    return None

# ========== دکمه "منوی اصلی" (Global) ==========
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="new_profit")],
        [InlineKeyboardButton("📊 مقایسه قیمت", callback_data="compare_price")],
        [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data="set_alert")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="global_price")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== شروع ==========
async def start(update: Update, context):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id] # پاک کردن داده‌های قبلی اگر کاربر نیمه‌کاره رها کرده باشد
    await update.message.reply_text(
        "🏭 *ربات تخصصی سنگ آهن و فلزات* 🏭\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

async def back_to_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏭 *ربات تخصصی سنگ آهن و فلزات* 🏭\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END # پایان هر مکالمه‌ای که در حال اجراست

# ========== قیمت جهانی ==========
async def global_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    prices = get_global_prices()
    rate = get_usd_rial_rate()
    
    text = f"🌍 *قیمت‌های جهانی* 🌍\n🔄 {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n💱 نرخ دلار بازار آزاد: **{rate:,} ریال**\n\n"
    for key, data in prices.items():
        icon = "🪨" if data["name"] == "سنگ آهن ۶۲٪" else "⚙️" if data["name"] == "کنسانتره آهن ۶۵٪" else "🟤" if data["name"] == "گندله" else "🔩"
        text += f"{icon} *{data['name']}*\n"
        text += f"   🇮🇷 FOB خلیج فارس: `${data['fob_pg']}` (~ {data['fob_rial']:,} ریال)\n"
        text += f"   🇨🇳 CFR شمال چین: `${data['north']}` (~ {data['north_rial']:,} ریال)\n"
        text += f"   🇨🇳 CFR جنوب چین: `${data['south']}` (~ {data['south_rial']:,} ریال)\n\n"
    
    text += "➖➖➖➖➖➖➖➖➖➖\n🔹 برای بازگشت به منو، دکمه زیر را بفشارید🔹",
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]]), parse_mode="Markdown")

# ========== مقایسه قیمت ==========
async def compare_price_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🪨 سنگ آهن ۶۲٪", callback_data="compare_iron_ore_62")],
        [InlineKeyboardButton("⚙️ کنسانتره آهن ۶۵٪", callback_data="compare_fe_65")],
        [InlineKeyboardButton("🟤 گندله", callback_data="compare_pellet")],
        [InlineKeyboardButton("🔩 بیلت", callback_data="compare_billet")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
    ]
    await query.edit_message_text("📊 *مقایسه قیمت*\nلطفاً محصول را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def compare_price_product(update: Update, context):
    query = update.callback_query
    await query.answer()
    product_map = {"compare_iron_ore_62": "سنگ آهن ۶۲٪", "compare_fe_65": "کنسانتره آهن ۶۵٪", "compare_pellet": "گندله", "compare_billet": "بیلت"}
    product_name = product_map.get(query.data)
    if not product_name:
        return
    data = get_global_product_price(product_name)
    if not data: return
    
    rate = get_usd_rial_rate()
    text = f"📊 *مقایسه قیمت {product_name}*\n\n"
    text += f"🇮🇷 *FOB خلیج فارس*: `${data['fob_pg']}` ≈ {int(data['fob_pg'] * rate):,} ریال\n"
    text += f"🇨🇳 *CFR شمال چین*: `${data['north']}` ≈ {int(data['north'] * rate):,} ریال (هزینه حمل: {data['north'] - data['fob_pg']:.1f} دلار)\n"
    text += f"🇨🇳 *CFR جنوب چین*: `${data['south']}` ≈ {int(data['south'] * rate):,} ریال (هزینه حمل: {data['south'] - data['fob_pg']:.1f} دلار)\n\n"
    text += f"💡 *توصیه صادراتی*: ارزان‌ترین مقصد {'شمال' if data['north'] < data['south'] else 'جنوب'} چین است.\n\n🔹 برای بازگشت، از دکمه زیر استفاده کنید:"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]]), parse_mode="Markdown")

# ========== تنظیم هشدار (بدون تغییر در منطق، فقط اضافه شدن منوی بازگشت) ==========
async def set_alert_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["alert_step"] = "product"
    await query.edit_message_text("🔔 *تنظیم هشدار*\nنام محصول را ارسال کنید:\n(سنگ آهن ۶۲٪, کنسانتره آهن ۶۵٪, گندله, بیلت)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚫 انصراف", callback_data="back_to_menu")]]), parse_mode="Markdown")

async def alert_product(update: Update, context): # ... (این توابع بدون تغییر می‌مانند، فقط در انتها دکمه بازگشت دارند)
    product = update.message.text
    valid_products = ["سنگ آهن ۶۲٪", "کنسانتره آهن ۶۵٪", "کنسانتره آهن", "گندله", "بیلت"]
    if product not in valid_products:
        await update.message.reply_text("❌ محصول نامعتبر.")
        return
    context.user_data["alert_product"] = product
    context.user_data["alert_step"] = "port"
    await update.message.reply_text("📍 بندر را انتخاب کنید:\nnorth (شمال) / south (جنوب) / fob_pg (خلیج فارس)")

async def alert_port(update: Update, context):
    port = update.message.text.lower()
    if port not in ["north", "south", "fob_pg"]:
        await update.message.reply_text("نامعتبر.")
        return
    context.user_data["alert_port"] = port
    context.user_data["alert_step"] = "condition"
    await update.message.reply_text("🎯 شرط:\nbelow (کمتر از) / above (بیشتر از)")

async def alert_condition(update: Update, context):
    cond = update.message.text.lower()
    if cond not in ["below", "above"]:
        await update.message.reply_text("نامعتبر.")
        return
    context.user_data["alert_condition"] = cond
    context.user_data["alert_step"] = "price"
    await update.message.reply_text("💰 قیمت هدف (دلار):")

async def alert_price(update: Update, context):
    try:
        target = float(update.message.text)
        add_alert(update.effective_user.id, context.user_data["alert_product"], context.user_data["alert_port"], context.user_data["alert_condition"], target)
        await update.message.reply_text("✅ هشدار ثبت شد!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]]))
        del context.user_data["alert_step"]
    except: await update.message.reply_text("عدد معتبر وارد کن")

# ========== محاسبه سود (با اضافه شدن دکمه بازگشت در تمام مراحل) ==========
async def profit_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {}
    keyboard = [[InlineKeyboardButton(p["name"], callback_data=p["name"])] for p in get_global_prices().values()]
    keyboard.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")])
    await query.edit_message_text("📊 *محاسبه سود*\nمحصول را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return PRODUCT

async def product_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id]["product"] = query.data
    await query.edit_message_text("💰 قیمت خرید (دلار/تن) را وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚫 لغو", callback_data="back_to_menu")]]))
    return PURCHASE

async def get_purchase(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["purchase"] = float(update.message.text)
        await update.message.reply_text(f"💱 نرخ دلار آزاد: {get_usd_rial_rate():,} ریال\n0=نرخ لحظه‌ای، یا عدد دلخواه را وارد کنید:")
        return RATE_RIAL
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return PURCHASE

async def get_rate_rial(update: Update, context):
    uid = update.effective_user.id
    try:
        val = float(update.message.text)
        user_data[uid]["rate_rial"] = val if val != 0 else get_usd_rial_rate()
        await update.message.reply_text("⚖️ تناژ (تن) را وارد کنید:")
        return TONNAGE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return RATE_RIAL

async def get_tonnage(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["tonnage"] = float(update.message.text)
        await update.message.reply_text("🚢 هزینه حمل (دلار/تن):")
        return FREIGHT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return TONNAGE

async def get_freight(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["freight"] = float(update.message.text)
        await update.message.reply_text("⚓ هزینه بارگیری در پورت (دلار/تن):")
        return PORT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return FREIGHT

async def get_port(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["port"] = float(update.message.text)
        d = user_data[uid]; t = d["tonnage"]; purchase = d["purchase"]; freight = d["freight"]; port = d["port"]; rate = d["rate_rial"]
        fob = purchase * 1.2
        revenue_usd, total_cost_usd = fob * t, (purchase + freight + port) * t
        profit_usd, profit_rial = revenue_usd - total_cost_usd, (revenue_usd - total_cost_usd) * rate
        
        result = f"📊 *نتیجه سود*\n📅 {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n{'─'*30}\n📦 {d['product']}\n⚖️ {t:,} تن\n💰 خرید: ${purchase:,.0f}/تن\n💵 فروش (FOB): ${fob:,.0f}/تن\n{'─'*30}\n🚢 حمل: ${freight}/تن\n⚓ پورت: ${port}/تن\n{'─'*30}\n✅ سود خالص:\n🇺🇸 ${profit_usd:,.0f}\n🇮🇷 {profit_rial:,.0f} ریال\n{'─'*30}\n💱 نرخ ارز: {rate:,} ریال"
        
        await update.message.reply_text(result, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]]))
        del user_data[uid]
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}\nعدد معتبر وارد کن.")
        return PORT

async def cancel(update, context):
    uid = update.effective_user.id
    if uid in user_data: del user_data[uid]
    await update.message.reply_text("❌ لغو شد.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

# ========== بررسی دوره‌ای هشدارها ==========
async def check_alerts(app):
    while True:
        try:
            await asyncio.sleep(900)
            for alert in get_active_alerts():
                pid, uid, product, port, cond, target = alert
                pdata = get_global_product_price(product)
                if pdata:
                    current = pdata.get(port, 0)
                    if (cond == "below" and current < target) or (cond == "above" and current > target):
                        await app.bot.send_message(uid, f"🚨 *هشدار!*\nمحصول: {product}\n💰 قیمت فعلی: {current} دلار", parse_mode="Markdown")
                        deactivate_alert(pid)
        except: pass

# ========== اجرای اصلی ==========
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN: return print("❌ Token not found!")
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    # هندلرهای عمومی
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(global_price, pattern="^global_price$"))
    app.add_handler(CallbackQueryHandler(compare_price_start, pattern="^compare_price$"))
    app.add_handler(CallbackQueryHandler(compare_price_product, pattern="^compare_"))
    app.add_handler(CallbackQueryHandler(set_alert_start, pattern="^set_alert$"))
    
    # مکالمات
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(profit_start, pattern="^new_profit$")],
        states={PRODUCT: [CallbackQueryHandler(product_choice, pattern=f"^({'|'.join(get_global_prices().keys())})$")],
                PURCHASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_purchase)],
                RATE_RIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate_rial)],
                TONNAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tonnage)],
                FREIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_freight)],
                PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_port)]},
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$")])
    
    app.add_handler(conv_handler)
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(alert_product, pattern="^set_alert$")], states={}, fallbacks=[])) # Placeholder
    
    async def post_init(application): asyncio.create_task(check_alerts(application))
    app.post_init = post_init
    print("🤖 Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
