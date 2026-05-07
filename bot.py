from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime

user_data = {}

# ========== پردازش دکمه‌های منوی اصلی ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("Profit Calculation", callback_data="profit")],
        [InlineKeyboardButton("Product Prices", callback_data="prices")],
        [InlineKeyboardButton("Guide / Help", callback_data="help")]
    ]
    await update.message.reply_text(
        "Welcome to Ironston Bot!\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== پردازش کلیه دکمه‌ها ==========
async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "profit":
        # شروع محاسبه سود
        user_data[user_id] = {}
        await query.message.reply_text("Step 1/7: Select product?\nExample: Iron Ore 62%")

    elif query.data == "prices":
        await query.message.reply_text(
            "Current Prices:\n\n"
            "Iron Ore 62%: $118.5/ton\n"
            "Fe 65%: $135.2/ton\n"
            "Pellet: $156.8/ton\n"
            "Billet: $520/ton"
        )

    elif query.data == "help":
        await query.message.reply_text(
            "How to use:\n\n"
            "1. Click 'Profit Calculation'\n"
            "2. Enter product name\n"
            "3. Enter numbers when asked\n\n"
            "Commands:\n/cancel - Cancel operation"
        )

# ========== پردازش متن‌های کاربر (ادامه محاسبه سود) ==========
async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text

    # اگر کاربر در حال محاسبه سود نباشد
    if user_id not in user_data:
        await update.message.reply_text("Press /start to begin")
        return

    data = user_data[user_id]

    # مرحله 1: محصول
    if "product" not in data:
        data["product"] = text
        await update.message.reply_text("Step 2/7: Purchase price (USD per ton)?\nExample: 105")

    # مرحله 2: قیمت خرید
    elif "purchase" not in data:
        try:
            data["purchase"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 3/7: FOB selling price (USD per ton)?\nExample: 118.5")

    # مرحله 3: قیمت فروش
    elif "fob" not in data:
        try:
            data["fob"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 4/7: Exchange rate (Rials per USD)?\nExample: 65000")

    # مرحله 4: نرخ ارز
    elif "rate" not in data:
        try:
            data["rate"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 5/7: Tonnage (tons)?\nExample: 5000")

    # مرحله 5: تناژ
    elif "tonnage" not in data:
        try:
            data["tonnage"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 6/7: Freight cost (USD per ton)?\nExample: 18")

    # مرحله 6: هزینه حمل
    elif "freight" not in data:
        try:
            data["freight"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text("Step 7/7: Port and loading cost (USD per ton)?\nExample: 4")

    # مرحله 7: هزینه بندر - محاسبه نهایی
    elif "port" not in data:
        try:
            data["port"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return

        #

محاسبات
        t = data["tonnage"]
        purchase = data["purchase"]
        fob = data["fob"]
        rate = data["rate"]
        freight = data["freight"]
        port = data["port"]

        revenue_usd = fob  t
        purchase_cost = purchase  t
        freight_cost = freight  t
        port_cost = port  t
        total_cost = purchase_cost + freight_cost + port_cost
        profit_usd = revenue_usd - total_cost
        profit_rials = profit_usd * rate

        now = datetime.now().strftime("%b %d, %Y - %H:%M")

        result = f"""
=== PROFIT CALCULATION ===
{now}
------------------------
Product: {data['product']}
Tonnage: {t:,.0f} tons
Purchase price: ${purchase}/ton
FOB price: ${fob}/ton
Exchange rate: {rate:,.0f} Rials
------------------------
Revenue: ${revenue_usd:,.0f}
Purchase cost: ${purchase_cost:,.0f}
Freight: ${freight_cost:,.0f}
Port costs: ${port_cost:,.0f}
Total Cost: ${total_cost:,.0f}
------------------------
Net Profit (USD): ${profit_usd:,.0f}
Net Profit (Rials): {profit_rials:,.0f}
------------------------
"""
        await update.message.reply_text(result)
        del user_data[user_id]

# ========== لغو عملیات ==========
async def cancel(update: Update, context):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Operation cancelled. Press /start to begin again.")

# ========== اجرای اصلی ==========
def main():
    TOKEN = "8742538592:AAEeT1DCoMUZWoM7zS3tds-k5YAAAC_ADpU

"  # توکن خود را وارد کنید

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

