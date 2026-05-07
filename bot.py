from telegram.ext import Application, CommandHandler
import os

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("ربات کار می‌کند!")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
print("ربات روشن شد")
app.run_polling()
