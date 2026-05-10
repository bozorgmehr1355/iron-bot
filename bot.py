import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context):
    keyboard = [[InlineKeyboardButton("✅ تست", callback_data="test")]]
    await update.message.reply_text(
        "ربات کار می‌کند! روی دکمه کلیک کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("✅ دکمه کار کرد!")  # استفاده از reply_text به جای edit

def main():
    if not TOKEN:
        logger.error("BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="test"))
    
    logger.info("ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
