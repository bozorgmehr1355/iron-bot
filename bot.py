from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
from datetime import datetime

# States
SELECT_PRODUCT, GET_PRICE, GET_RATE, GET_TONNAGE, GET_FREIGHT, GET_PORT = range(6)

user_data = {}

def get_usd_rial_rate():
    return 1780000

def get_global_prices():
    return {
        "concentrate": {"name": "کنسانتره سنگ آهن", "fob_pg": 85, "north": 130, "south": 131},
        "pellet": {"name": "گندله", "fob_pg": 105, "north": 155, "south": 156},
        "dri": {"name": "آهن اسفنجی", "fob_pg": 200, "north": 280, "south": 282},
        "billet": {"name": "شمش فولادی", "fob_pg": 480, "north": 520, "south": 515},
        "rebar": {"name": "میلگرد", "fob_pg": 550, "north": 600, "south": 595}
    }

async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="start_profit")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="show_global")]
    ]
    await update.message.reply_text(
        "ربات محاسبه سود سنگ آهن و فولاد\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def main_menu_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_global":
        text = "🌍 قیمت‌های جهانی 🌍\n"
        for key, d in get_global_prices().items():
            text += f"\n{d['name']}:\n   FOB خلیج فارس: ${d['fob_pg']}\n   CFR شمال چین: ${d['north']}\n   CFR جنوب چین: ${d['south']}"
        await query.edit_message_text(text)
    
    elif query.data == "start_profit":
        user_data[query.from_user.id] = {}
        keyboard = [
            [InlineKeyboardButton("کنسانتره سنگ آهن", callback_data="prod_concentrate")],
            [InlineKeyboardButton("گندله", callback_data="prod_pellet")],
            [InlineKeyboardButton("آهن اسفنجی", callback_data="prod_dri")],
            [InlineKeyboardButton("شمش فولادی", callback_data="prod_billet")],
            [InlineKeyboardButton("میلگرد", callback_data="prod_rebar")],
        ]
        await query.edit_message_text("📊 محاسبه سود\n\nلطفاً محصول را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
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
        f"📊 محاسبه سود - {product_name}\n\n"
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
        rate = get_usd_rial_rate()
        await update.message.reply_text(
            f"💱 نرخ دلار آزاد: {rate:,} ریال\n\n"
            f"0 = استفاده از نرخ فعلی\n"
            f"یا عدد دلخواه را وارد کنید:"
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
        user_data[uid]["rate"] = val if val != 0 else get_usd_rial_rate()
        await update.message.reply_text("⚖️ *تناژ* (تن) را وارد کنید:\n(مثال: 5000)", parse_mode="Markdown")
        return GET_TONNAGE
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 5000):")
        return GET_RATE

async def get_tonnage(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["tonnage"] = float(text)
        await update.message.reply_text("🚢 *هزینه حمل* هر تن به دلار را وارد کنید:\n(مثال: 18)", parse_mode="Markdown")
        return GET_FREIGHT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 18):")
        return GET_TONNAGE

async def get_freight(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["freight"] = float(text)
        await update.message.reply_text("⚓ *هزینه بارگیری در پورت* هر تن به دلار را وارد کنید:\n(مثال: 4)", parse_mode="Markdown")
        return GET_PORT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 4):")
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

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ توکن یافت نشد!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(main_menu_handler, pattern="^(start_profit|show_global)$")],
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
    
    print("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
