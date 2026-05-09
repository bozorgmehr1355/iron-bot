from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
from datetime import datetime

# States
PRODUCT_SELECT, PURCHASE_PRICE, RATE_SELECT, TONNAGE_INPUT, FREIGHT_INPUT, PORT_INPUT = range(6)

user_data = {}

# نرخ دلار ثابت (برای تست)
def get_usd_rial_rate():
    return 1780000

# قیمت‌های جهانی
def get_global_prices():
    return {
        "concentrate": {"name": "کنسانتره سنگ آهن", "fob_pg": 85, "north": 130, "south": 131},
        "pellet": {"name": "گندله", "fob_pg": 105, "north": 155, "south": 156},
        "dri": {"name": "آهن اسفنجی", "fob_pg": 200, "north": 280, "south": 282},
        "billet": {"name": "شمش فولادی", "fob_pg": 480, "north": 520, "south": 515},
        "rebar": {"name": "میلگرد", "fob_pg": 550, "north": 600, "south": 595}
    }

def get_global_product_price(name):
    for data in get_global_prices().values():
        if data["name"] == name:
            return data
    return None

async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 محاسبه سود", callback_data="profit")],
        [InlineKeyboardButton("💰 قیمت جهانی", callback_data="global")]
    ]
    await update.message.reply_text("ربات محاسبه سود - نسخه تست", reply_markup=InlineKeyboardMarkup(keyboard))

async def buttons(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "global":
        text = "🌍 قیمت‌های جهانی 🌍\n"
        for key, d in get_global_prices().items():
            text += f"\n{d['name']}:\n   FOB خلیج فارس: ${d['fob_pg']}\n   CFR شمال چین: ${d['north']}\n   CFR جنوب چین: ${d['south']}"
        await query.edit_message_text(text)
    
    elif query.data == "profit":
        user_data[query.from_user.id] = {}
        await query.edit_message_text("📊 محاسبه سود\n\nمحصول را انتخاب کنید:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("کنسانتره", callback_data="p_concentrate")],
            [InlineKeyboardButton("گندله", callback_data="p_pellet")],
            [InlineKeyboardButton("آهن اسفنجی", callback_data="p_dri")],
            [InlineKeyboardButton("شمش فولادی", callback_data="p_billet")],
            [InlineKeyboardButton("میلگرد", callback_data="p_rebar")],
        ]))
        return PRODUCT_SELECT

async def product_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    product_map = {
        "p_concentrate": "کنسانتره سنگ آهن",
        "p_pellet": "گندله",
        "p_dri": "آهن اسفنجی",
        "p_billet": "شمش فولادی",
        "p_rebar": "میلگرد"
    }
    user_data[query.from_user.id]["product"] = product_map[query.data]
    await query.edit_message_text("💰 قیمت خرید (دلار/تن) را وارد کنید:\n(مثال: 95)")
    return PURCHASE_PRICE

async def get_price(update: Update, context):
    uid = update.effective_user.id
    try:
        # حذف ویرگول و فاصله
        text = update.message.text.replace(',', '').replace('،', '').strip()
        price = float(text)
        user_data[uid]["purchase"] = price
        await update.message.reply_text(f"💱 نرخ دلار: {get_usd_rial_rate():,} ریال\n\n0 = نرخ فعلی\nعدد دلخواه را وارد کنید:")
        return RATE_SELECT
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 95):")
        return PURCHASE_PRICE

async def get_rate(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        val = float(text)
        user_data[uid]["rate"] = val if val != 0 else get_usd_rial_rate()
        await update.message.reply_text("⚖️ تناژ (تن) را وارد کنید:\n(مثال: 5000)")
        return TONNAGE_INPUT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 5000):")
        return RATE_SELECT

async def get_tonnage(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["tonnage"] = float(text)
        await update.message.reply_text("🚢 هزینه حمل (دلار/تن) را وارد کنید:\n(مثال: 18)")
        return FREIGHT_INPUT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 18):")
        return TONNAGE_INPUT

async def get_freight(update: Update, context):
    uid = update.effective_user.id
    try:
        text = update.message.text.replace(',', '').replace('،', '').strip()
        user_data[uid]["freight"] = float(text)
        await update.message.reply_text("⚓ هزینه بارگیری (دلار/تن) را وارد کنید:\n(مثال: 4)")
        return PORT_INPUT
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید (مثال: 4):")
        return FREIGHT_INPUT

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
📦 محصول: {d['product']}
⚖️ تناژ: {t:,.0f} تن
💰 قیمت خرید: ${purchase:,.0f}/تن
💵 قیمت فروش: ${fob:,.0f}/تن
─────────────────
🚢 حمل: ${freight:,.0f}/تن
⚓ پورت: ${port:,.0f}/تن
─────────────────
✅ سود خالص:
🇺🇸 دلار: ${profit_usd:,.0f}
🇮🇷 ریال: {profit_rial:,.0f} ریال
💱 نرخ ارز: {rate:,} ریال
"""
        await update.message.reply_text(result)
        del user_data[uid]
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")
        return PORT_INPUT

async def cancel(update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("لغو شد.")

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("توکن ندارد")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(buttons, pattern="^profit$")],
        states={
            PRODUCT_SELECT: [CallbackQueryHandler(product_select, pattern="^p_")],
            PURCHASE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            RATE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate)],
            TONNAGE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tonnage)],
            FREIGHT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_freight)],
            PORT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_port)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons, pattern="^(global|profit)$"))
    app.add_handler(conv)
    
    print("ربات تست روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
