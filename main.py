from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from commands.profit_cmd import profit_start, profit_step, PRODUCT, PURCHASE, FOB, RATE, TONNAGE, FREIGHT, PORT, user_data
import os

# ========== /start command ==========
async def start(update: Update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("📊 Profit Calculation", callback_data="new_profit")],
        [InlineKeyboardButton("💰 Product Prices", callback_data="prices")],
        [InlineKeyboardButton("❓ Guide / Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 Welcome to Ironston Bot!\n\n"
        "Choose an option from the buttons below:",
        reply_markup=reply_markup
    )

# ========== Handle button clicks ==========
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "new_profit":
        # شروع محاسبه سود
        await profit_start(update, context)
        
    elif query.data == "prices":
        await query.message.reply_text(
            "📈 Current Iron Ore Prices:\n\n"
            "🔹 Iron Ore 62%: $118.5/ton\n"
            "🔹 Fe 65%: $135.2/ton\n"
            "🔹 Pellet: $156.8/ton\n"
            "🔹 Billet: $520/ton\n\n"
            "⏱️ Last update: Just now"
        )
        
    elif query.data == "help":
        await query.message.reply_text(
            "📖 Bot Guide:\n\n"
            "1️⃣ Press 'Profit Calculation' to start\n"
            "2️⃣ Answer questions step by step\n"
            "3️⃣ Enter numbers when asked\n\n"
            "🔧 Commands:\n"
            "/start - Main menu\n"
            "/cancel - Cancel current operation"
        )

# ========== Cancel operation ==========
async def cancel(update: Update, context):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("❌ Operation cancelled.\nPress /start to begin again.")
    return ConversationHandler.END

# ========== MAIN FUNCTION ==========
def main():
    # دریافت توکن از متغیر محیطی (برای امنیت)
    TOKEN = os.environ.get("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ Error: BOT_TOKEN not found in environment variables!")
        return
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Create conversation handler for profit calculation
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^new_profit$")],
        states={
            PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            PURCHASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            FOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            TONNAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            FREIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
            PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profit_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(new_profit|prices|help)$"))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Start the bot
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

