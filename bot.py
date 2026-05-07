from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from commands.profit_cmd import (
    profit_start, profit_step, product_selection,
    PRODUCT, PURCHASE, RATE_RIAL, RATE_DIRHAM, TONNAGE, FREIGHT, PORT, user_data,
    get_usd_rial_rate, get_usd_dirham_rate
)
import os

async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 Profit Calculation", callback_data="new_profit")],
        [InlineKeyboardButton("💰 Product Prices", callback_data="prices")],
        [InlineKeyboardButton("💱 Exchange Rates", callback_data="rates")],
        [InlineKeyboardButton("❓ Guide / Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 Ironston Bot\nChoose an option:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "new_profit":
        await profit_start(update, context)
    elif query.data == "prices":
        await query.message.reply_text(
            "📈 Iron Ore 62%: $118.5/ton\n"
            "Fe 65%: $135.2/ton\n"
            "Pellet: $156.8/ton\n"
            "Billet: $520/ton"
        )
    elif query.data == "rates":
        rial = get_usd_rial_rate()
        dirham = get_usd_dirham_rate()
        await query.message.reply_text(
            f"💱 USD → RIAL: {rial:,.0f}\n"
            f"USD → DIRHAM: {dirham:.2f}"
        )
    elif query.data == "help":
        await query.message.reply_text(
            "📖 /start - Main menu\n"
            "/cancel - Cancel"
        )

async def cancel(update: Update, context):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("❌ Cancelled.")

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ BOT_TOKEN not found!")
        return

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^new_profit$")],
        states={
            PRODUCT: [
                CallbackQueryHandler(product_selection, pattern="^(prod_1|prod_2|prod_3|prod_4|prod_5)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)
            ],
            PURCHASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            RATE_RIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            RATE_DIRHAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            TONNAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            FREIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(new_profit|prices|rates|help)$"))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))

    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
