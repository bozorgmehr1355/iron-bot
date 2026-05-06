from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TOKEN
from commands.report import get_report
from commands.profit_cmd import profit_command

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Market Report", callback_data="report")],
        [InlineKeyboardButton("🧮 Profit Calculator", callback_data="profit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "report":
        msg = get_report()
        await query.edit_message_text(msg)
    elif query.data == "profit":
        await query.edit_message_text("Send: /profit <tonnage>\nExample: /profit 5000")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_report())

async def profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tonnage = int(context.args[0])
        result = profit_command(tonnage)
        await update.message.reply_text(result)
    except:
        await update.message.reply_text("Usage: /profit <tonnage>\nExample: /profit 5000")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("profit", profit))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot started...")
    app.run_polling()
