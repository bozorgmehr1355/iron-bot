from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
import requests
from datetime import datetime
import asyncio
from database import init_db, add_alert, get_active_alerts, deactivate_alert

# States for Conversation
PRODUCT_SELECT, PURCHASE_PRICE, RATE_SELECT, TONNAGE_INPUT, FREIGHT_INPUT, PORT_INPUT = range(6)

user_data = {}

# ========== نرخ دلار بازار آزاد ==========
def get_usd_rial_rate():
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
    return 1315000

# ========== قیمت‌های جهانی محصولات (به‌روز با ترتیب جدید) ==========
def get_global_prices():
    """قیمت‌های تقریبی تا زمان اتصال API معتبر"""
    return {
        "concentrate": {
            "name": "کنسانتره سنگ آهن",
            "fob_pg": 85, "north": 130, "south": 131,
            "icon": "⚙️"
        },
        "pellet": {
            "name": "گندله",
            "fob_pg": 105, "north": 155, "south": 156,
            "icon": "🟤"
        },
        "dri": {
            "name": "آهن اسفنجی",
            "fob_pg": 200, "north": 280, "south": 282,
            "icon": "🏭"
        },
        "billet": {
            "name": "شمش فولادی (بیلت)",
            "fob_pg": 480, "north": 520, "south": 515,
            "icon": "🔩"
        },
        "rebar": {
            "name": "میلگرد",
            "fob_pg": 550, "north": 600, "south": 595,
            "icon": "📏"
        }
    }

def get_global_product_price(product_name):
    for data in get_global_prices().values():
        if data["name"] == product_name:
            return data
    return None

# ========== منوی اصلی ==========
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="menu_profit")],
        [InlineKeyboardButton("📊 مقایسه قیمت", callback_data="menu_compare")],
        [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data="menu_alert")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="menu_global")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context):
    await update.message.reply_text(
        "🏭 *ربات تخصصی زنجیره آهن و فولاد* 🏭\n\n"
        "📌 محصولات تحت پوشش:\n"
        "1. کنسانتره سنگ آهن\n"
        "2. گندله\n"
        "3. آهن اسفنجی\n"
        "4. شمش فولادی\n"
        "5. میلگرد\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

async def back_to_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏭 *ربات تخصصی زنجیره آهن و فولاد* 🏭\n\n"
        "📌 محصولات تحت پوشش:\n"
        "1. کنسانتره سنگ آهن\n"
        "2. گندله\n"
        "3. آهن اسفنجی\n"
        "4. شمش فولادی\n"
        "5. میلگرد\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ========== قیمت جهانی (با محصولات جدید و ترتیب اصلاح شده) ==========
async def global_price_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    prices = get_global_prices()
    rate = get_usd_rial_rate()
    
    text = f"🌍 *قیمت‌های جهانی* 🌍\n🔄 {datetime.now().strftime('%Y/%m/%d - %H:%M')}\n💱 نرخ دلار: **{rate:,} ریال**\n\n"
    
    for key, data in prices.items():
        text += f"{data['icon']} *{data['name']}*\n"
        text += f"   🇮🇷 FOB خلیج فارس: *${data['fob_pg']}*\n"
        text += f"   🇨🇳 CFR شمال چین: *${data['north']}*\n"
        text += f"   🇨🇳 CFR جنوب چین: *${data['south']}*\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_menu")]]),
        parse_mode="Markdown"
    )

# ========== مقایسه قیمت (با محصولات جدید) ==========
async def compare_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("⚙️ کنسانتره سنگ آهن", callback_data="compare_concentrate")],
        [InlineKeyboardButton("🟤 گندله", callback_data="compare_pellet")],
        [InlineKeyboardButton("🏭 آهن اسفنجی", callback_data="compare_dri")],
        [InlineKeyboardButton("🔩 شمش فولادی", callback_data="compare_billet")],
        [InlineKeyboardButton("📏 میلگرد", callback_data="compare_rebar")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(
        "📊 *مقایسه قیمت*\nلطفاً محصول را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def compare_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    product_map = {
        "compare_concentrate": "کنسانتره سنگ آهن",
        "compare_pellet": "گندله",
        "compare_dri": "آهن اسفنجی",
        "compare_billet": "شمش فولادی (بیلت)",
        "compare_rebar": "میلگرد"
    }
    product_name = product_map.get(query.data)
    if not product_name:
        return
    
    data = get_global_product_price(product_name)
    if not data:
        return
    
    text = f"📊 *مقایسه قیمت {product_name}*\n\n"
    text += f"🇮🇷 *FOB خلیج فارس*: *${data['fob_pg']}*\n"
    text += f"🇨🇳 *CFR شمال چین*: *${data['north']}* (هزینه حمل: {data['north'] - data['fob_pg']:.1f} دلار)\n"
    text += f"🇨🇳 *CFR جنوب چین*: *${data['south']}* (هزینه حمل: {data['south'] - data['fob_pg']:.1f} دلار)\n\n"
    text += f"💡 *توصیه*: ارزان‌ترین مقصد {'شمال' if data['north'] < data['south'] else 'جنوب'} چین است."
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت به لیست محصولات", callback_data="compare_back")],
        [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def compare_back(update: Update, context):
    query = update.callback_query
    await query.answer()
    await compare_menu(update, context)

# ========== تنظیم هشدار (با محصولات جدید) ==========
async def alert_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("⚙️ کنسانتره سنگ آهن", callback_data="alert_concentrate")],
        [InlineKeyboardButton("🟤 گندله", callback_data="alert_pellet")],
        [InlineKeyboardButton("🏭 آهن اسفنجی", callback_data="alert_dri")],
        [InlineKeyboardButton("🔩 شمش فولادی", callback_data="alert_billet")],
        [InlineKeyboardButton("📏 میلگرد", callback_data="alert_rebar")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(
        "🔔 *تنظیم هشدار قیمتی*\nلطفاً محصول را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def alert_product_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    product_map = {
        "alert_concentrate": "کنسانتره سنگ آهن",
        "alert_pellet": "گندله",
        "alert_dri": "آهن اسفنجی",
        "alert_billet": "شمش فولادی (بیلت)",
        "alert_rebar": "میلگرد"
    }
    product_name = product_map.get(query.data)
    if not product_name:
        return
    
    context.user_data["alert_product"] = product_name
    
    keyboard = [
        [InlineKeyboardButton("🇮🇷 FOB خلیج فارس", callback_data="alert_fob_pg")],
        [InlineKeyboardButton("🇨🇳 CFR شمال چین", callback_data="alert_north")],
        [InlineKeyboardButton("🇨🇳 CFR جنوب چین", callback_data="alert_south")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="alert_back")]
    ]
    await query.edit_message_text(
        f"🔔 *تنظیم هشدار برای {product_name}*\n\nلطفاً بندر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def alert_port_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    port_map = {
        "alert_fob_pg": "fob_pg",
        "alert_north": "north",
        "alert_south": "south"
    }
    port = port_map.get(query.data)
    if not port:
        return
    
    context.user_data["alert_port"] = port
    
    keyboard = [
        [InlineKeyboardButton("⬇️ کمتر از (below)", callback_data="alert_below")],
        [InlineKeyboardButton("⬆️ بیشتر از (above)", callback_data="alert_above")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="alert_back_product")]
    ]
    await query.edit_message_text(
        f"🔔 *شرط هشدار* را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def alert_condition_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    condition_map = {
        "alert_below": "below",
        "alert_above": "above"
    }
    condition = condition_map.get(query.data)
    if not condition:
        return
    
    context.user_data["alert_condition"] = condition
    context.user_data["alert_step"] = "waiting_price"
    await query.edit_message_text(
        f"🔔 *تنظیم هشدار*\nمحصول: {context.user_data['alert_product']}\nشرط: {condition}\n\n💰 قیمت هدف را به *دلار* وارد کنید:",
        parse_mode="Markdown"
    )

async def alert_price_input(update: Update, context):
    try:
        target = float(update.message.text)
        user_id = update.effective_user.id
        product = context.user_data["alert_product"]
        port = context.user_data["alert_port"]
        condition = context.user_data["alert_condition"]
        
        add_alert(user_id, product, port, condition, target)
        
        await update.message.reply_text(
            f"✅ *هشدار ثبت شد!*\n\n📦 محصول: {product}\n📍 بندر: {port}\n🎯 شرط: {condition} {target} دلار",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
        del context.user_data["alert_step"]
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")

async def alert_back(update: Update, context):
    query = update.callback_query
    await query.answer()
    await alert_menu(update, context)

async def alert_back_product(update: Update, context):
    query = update.callback_query
    await query.answer()
    await alert_product_select(update, context)

# ========== محاسبه سود (با محصولات جدید) ==========
async def profit_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {}
    
    keyboard = [
        [InlineKeyboardButton("⚙️ کنسانتره سنگ آهن", callback_data="profit_concentrate")],
        [InlineKeyboardButton("🟤 گندله", callback_data="profit_pellet")],
        [InlineKeyboardButton("🏭 آهن اسفنجی", callback_data="profit_dri")],
        [InlineKeyboardButton("🔩 شمش فولادی", callback_data="profit_billet")],
        [InlineKeyboardButton("📏 میلگرد", callback_data="profit_rebar")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(
        "📊 *محاسبه سود*\nلطفاً محصول را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return PRODUCT_SELECT

async def profit_product_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    product_map = {
        "profit_concentrate": "کنسانتره سنگ آهن",
        "profit_pellet": "گندله",
        "profit_dri": "آهن اسفنجی",
        "profit_billet": "شمش فولادی (بیلت)",
        "profit_rebar": "میلگرد"
    }
    product_name = product_map.get(query.data)
    if not product_name:
        await query.edit_message_text("❌ خطا در انتخاب محصول. دوباره تلاش کنید.")
        return PRODUCT_SELECT
    
    user_data[user_id]["product"] = product_name
    product_data = get_global_product_price(product_name)
    
    text = f"📊 *محاسبه سود - {product_name}*\n\n"
    if product_data:
        text += f"💰 *قیمت جهانی:*\n"
        text += f"   └ FOB خلیج فارس: {product_data['fob_pg']} دلار\n"
        text += f"   └ CFR شمال چین: {product_data['north']} دلار\n"
        text += f"   └ CFR جنوب چین: {product_data['south']} دلار\n\n"
    text += f"✏️ *قیمت خرید خود* را به دلار وارد کنید:"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="back_to_menu")]]),
        parse_mode="Markdown"
    )
    return PURCHASE_PRICE

async def purchase_input(update: Update, context):
    uid = update.effective_user.id
    try:
        purchase_price = float(update.message.text)
        user_data[uid]["purchase"] = purchase_price
        rate = get_usd_rial_rate()
        await update.message.reply_text(
            f"💱 *نرخ دلار آزاد:* {rate:,} ریال\n\n0 = استفاده از نرخ فعلی\nیا عدد دلخواه را وارد کنید:",
            parse_mode="Markdown"
        )
        return RATE_SELECT
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید (مثال: 95):")
        return PURCHASE_PRICE
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: لطفاً یک عدد معتبر وارد کنید.")
        return PURCHASE_PRICE

async def rate_input(update: Update, context):
    uid = update.effective_user.id
    try:
        val = float(update.message.text)
        user_data[uid]["rate"] = val if val != 0 else get_usd_rial_rate()
        await update.message.reply_text("⚖️ *تناژ* (تن) را وارد کنید:\n(مثال: 5000)", parse_mode="Markdown")
        return TONNAGE_INPUT
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید (مثال: 5000):")
        return RATE_SELECT

async def tonnage_input(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["tonnage"] = float(update.message.text)
        await update.message.reply_text("🚢 *هزینه حمل* هر تن به دلار را وارد کنید:\n(مثال: 18)", parse_mode="Markdown")
        return FREIGHT_INPUT
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید (مثال: 18):")
        return TONNAGE_INPUT

async def freight_input(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["freight"] = float(update.message.text)
        await update.message.reply_text("⚓ *هزینه بارگیری در پورت* هر تن به دلار را وارد کنید:\n(مثال: 4)", parse_mode="Markdown")
        return PORT_INPUT
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید (مثال: 4):")
        return FREIGHT_INPUT

async def port_input(update: Update, context):
    uid = update.effective_user.id
    try:
        user_data[uid]["port"] = float(update.message.text)
        
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
🇮🇷 ریال: {profit_rial:,.0f} ریال
{'─' * 30}
💱 نرخ ارز: {rate:,} ریال
"""
        await update.message.reply_text(result, reply_markup=get_main_menu(), parse_mode="Markdown")
        del user_data[uid]
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: لطفاً یک عدد معتبر وارد کنید.")
        return PORT_INPUT

async def cancel(update: Update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=get_main_menu())
    return ConversationHandler.END

# ========== بررسی هشدارها ==========
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
                        await app.bot.send_message(
                            uid,
                            f"🚨 *هشدار قیمتی!*\n\n📦 محصول: {product}\n📍 بندر: {port}\n💰 قیمت فعلی: {current} دلار\n🎯 هدف: {cond} {target} دلار",
                            parse_mode="Markdown"
                        )
                        deactivate_alert(pid)
        except:
            await asyncio.sleep(60)

# ========== اجرای اصلی ==========
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ Token not found!")
        return
    
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    # هندلرهای منو
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(global_price_handler, pattern="^menu_global$"))
    app.add_handler(CallbackQueryHandler(compare_menu, pattern="^menu_compare$"))
    app.add_handler(CallbackQueryHandler(compare_handler, pattern="^compare_"))
    app.add_handler(CallbackQueryHandler(compare_back, pattern="^compare_back$"))
    app.add_handler(CallbackQueryHandler(alert_menu, pattern="^menu_alert$"))
    app.add_handler(CallbackQueryHandler(alert_product_select, pattern="^alert_concentrate|alert_pellet|alert_dri|alert_billet|alert_rebar$"))
    app.add_handler(CallbackQueryHandler(alert_port_select, pattern="^alert_fob_pg|alert_north|alert_south$"))
    app.add_handler(CallbackQueryHandler(alert_condition_select, pattern="^alert_below|alert_above$"))
    app.add_handler(CallbackQueryHandler(alert_back, pattern="^alert_back$"))
    app.add_handler(CallbackQueryHandler(alert_back_product, pattern="^alert_back_product$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, alert_price_input))
    
    # مکالمه محاسبه سود
    profit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(profit_menu, pattern="^menu_profit$")],
        states={
            PRODUCT_SELECT: [CallbackQueryHandler(profit_product_select, pattern="^profit_concentrate|profit_pellet|profit_dri|profit_billet|profit_rebar$")],
            PURCHASE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, purchase_input)],
            RATE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rate_input)],
            TONNAGE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tonnage_input)],
            FREIGHT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, freight_input)],
            PORT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, port_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$")],
    )
    
    app.add_handler(profit_conv)
    
    async def post_init(application):
        asyncio.create_task(check_alerts(application))
    
    app.post_init = post_init
    
    print("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
