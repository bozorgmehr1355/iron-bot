import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context):
    await update.message.reply_text(
        "✅ ربات کار می‌کند!\n\n"
        "برای دریافت قیمت‌های جهانی: /global\n"
        "برای دریافت قیمت ایران: /iran\n"
        "برای محاسبه سود: /profit"
    )

async def global_price(update: Update, context):
    text = "🌍 قیمت‌های جهانی 🌍\n\n"
    text += "• کنسانتره سنگ آهن\n   FOB خلیج فارس: $85\n   CFR شمال چین: $130\n   CFR جنوب چین: $131\n\n"
    text += "• گندله\n   FOB خلیج فارس: $105\n   CFR شمال چین: $155\n   CFR جنوب چین: $156\n\n"
    text += "• آهن اسفنجی\n   FOB خلیج فارس: $200\n   CFR شمال چین: $280\n   CFR جنوب چین: $282\n\n"
    text += "• شمش فولادی\n   FOB خلیج فارس: $480\n   CFR شمال چین: $520\n   CFR جنوب چین: $515\n\n"
    text += "• میلگرد\n   FOB خلیج فارس: $550\n   CFR شمال چین: $600\n   CFR جنوب چین: $595"
    await update.message.reply_text(text)

async def iran_price(update: Update, context):
    text = "🇮🇷 قیمت‌های داخلی ایران 🇮🇷\n\n"
    text += "🔹 بورس کالا (ICE):\n"
    text += "   • میلگرد: ۱۵,۸۰۰ - ۱۶,۸۰۰ تومان/کیلو\n"
    text += "   • شمش: ۴۱,۰۰۰ - ۴۴,۰۰۰ تومان/تن\n"
    text += "   • آهن اسفنجی: ۱۴,۸۰۰ - ۱۵,۵۰۰ تومان/کیلو\n\n"
    text += "🔹 بازار آزاد:\n"
    text += "   • میلگرد: ۶۳,۰۰۰ - ۶۸,۰۰۰ تومان/کیلو\n"
    text += "   • شمش: ۵۴,۰۰۰ - ۵۷,۰۰۰ تومان/تن\n"
    text += "   • آهن اسفنجی: ۱۶,۵۰۰ - ۱۷,۵۰۰ تومان/کیلو"
    await update.message.reply_text(text)

async def profit(update: Update, context):
    await update.message.reply_text(
        "📊 محاسبه سود\n\n"
        "لطفاً قیمت خرید را به دلار وارد کنید.\n"
        "مثال: 95"
    )

def main():
    if not TOKEN:
        logger.error("BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("global", global_price))
    app.add_handler(CommandHandler("iran", iran_price))
    app.add_handler(CommandHandler("profit", profit))
    
    logger.info("ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
