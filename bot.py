import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

from price_fetcher.exchange_rate import get_usd_toman_rate
from price_fetcher.world_price import get_iron_ore_price, get_billet_price
from price_fetcher.iran_price import get_iran_billet_price, get_iran_rebar_price
from utils.helpers import to_persian_digits

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context):
    await update.message.reply_text(
        "🤖 ربات قیمت آهن و فولاد\n\n"
        "📊 /world - قیمت جهانی\n"
        "🇮🇷 /iran - قیمت ایران\n"
        "💱 /rate - نرخ ارز"
    )

async def world_price(update: Update, context):
    iron = get_iron_ore_price()
    billet = get_billet_price()
    
    text = "🌍 *قیمت‌های جهانی* 🌍\n\n"
    text += f"🪨 سنگ آهن ۶۲٪ (CFR چین): *${to_persian_digits(iron)}*/تن\n"
    text += f"🔩 بیلت (FOB چین): *${to_persian_digits(billet)}*/تن\n"
    text += "\n📌 منابع: Platts / Fastmarkets"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def iran_price(update: Update, context):
    billet = get_iran_billet_price()
    rebar = get_iran_rebar_price()
    
    text = "🇮🇷 *قیمت‌های داخلی ایران* 🇮🇷\n\n"
    if billet:
        text += f"🔩 شمش فولادی: *{to_persian_digits(billet)}* تومان/کیلو\n"
    else:
        text += "🔩 شمش فولادی: در حال دریافت...\n"
    
    if rebar:
        text += f"📏 میلگرد: *{to_persian_digits(rebar)}* تومان/کیلو\n"
    else:
        text += "📏 میلگرد: در حال دریافت...\n"
    
    text += "\n📌 منبع: آهن ملل"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def rate(update: Update, context):
    toman = get_usd_toman_rate()
    text = f"💱 *نرخ دلار بازار آزاد*\n\n🇺🇸 ۱ دلار = *{to_persian_digits(toman)}* تومان"
    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    if not TOKEN:
        logger.error("BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("world", world_price))
    app.add_handler(CommandHandler("iran", iran_price))
    app.add_handler(CommandHandler("rate", rate))
    
    logger.info("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
