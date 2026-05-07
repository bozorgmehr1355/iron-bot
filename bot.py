from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import os
import requests
from datetime import datetime

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

# ========== شروع ==========
async def start(update: Update, context):
    keyboard = [[InlineKeyboardButton("📊 محاسبه سود", callback_data="new_profit")]]
    await update.message.reply_text("ربات محاسبه سود سنگ آهن", reply_markup=InlineKeyboardMarkup(keyboard))

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
        await update.message.reply_text(f"نرخ دلار آزاد: {get_usd_rial_rate():,.0f} تومان\n0=همین نرخ، یا عدد دلخواه:")
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
        
        # سود 20 درصدی
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

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("توکن نداریم")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
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
    app.add_handler(conv)
    app.add_handler(CommandHandler("cancel", cancel))
    
    print("ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
