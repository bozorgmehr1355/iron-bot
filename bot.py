import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from price_fetcher.exchange_rate import get_usd_toman_rate
from price_fetcher.world_price import get_iron_ore_price, get_billet_price
from price_fetcher.iran_price import get_iran_billet_price, get_iran_rebar_price
from utils.helpers import to_persian_digits

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

# ========== منوی اصلی با دکمه ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🇮🇷 قیمت ایران", callback_data="iran")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 *ربات قیمت آهن و فولاد*\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ========== قیمت جهانی ==========
async def world_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    iron = get_iron_ore_price()
    billet = get_billet_price()
    
    text = "🌍 *قیمت‌های جهانی* 🌍\n\n"
    text += f"🪨 سنگ آهن ۶۲٪ (CFR چین): *${to_persian_digits(iron)}*/تن\n"
    text += f"🔩 بیلت (FOB چین): *${to_persian_digits(billet)}*/تن\n"
    text += "\n📌 منابع: Platts / Fastmarkets"
    
    await query.edit_message_text(text, parse_mode="Markdown")

# ========== قیمت ایران ==========
async def iran_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
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
    
    await query.edit_message_text(text, parse_mode="Markdown")

# ========== نرخ ارز ==========
async def rate(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    toman = get_usd_toman_rate()
    text = f"💱 *نرخ دلار بازار آزاد*\n\n🇺🇸 ۱ دلار = *{to_persian_digits(toman)}* تومان"
    
    await query.edit_message_text(text, parse_mode="Markdown")

# ========== اجرای اصلی ==========
def main():
    if not TOKEN:
        logger.error("BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # دستور start
    app.add_handler(CommandHandler("start", start))
    
    # دکمه‌ها
    app.add_handler(CallbackQueryHandler(world_price, pattern="^world$"))
    app.add_handler(CallbackQueryHandler(iran_price, pattern="^iran$"))
    app.add_handler(CallbackQueryHandler(rate, pattern="^rate$"))
    
    logger.info("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
