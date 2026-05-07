from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import os

async def start(update: Update, context):
    keyboard = [[InlineKeyboardButton("✅ کلیک کن", callback_data="test")]]
    await update.message.reply_text("روی دکمه کلیک کن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ دکمه کار می‌کند!")

def main():
    app = Application.builder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="test"))
    print("ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
