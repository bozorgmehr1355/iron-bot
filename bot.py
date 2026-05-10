import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

# ========== منوی اصلی ==========
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🇮🇷 قیمت ایران", callback_data="iran")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.message.reply_text(
        "🤖 *ربات قیمت آهن و فولاد*\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== دکمه بازگشت ==========
def get_back_button():
    keyboard = [[InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]]
    return InlineKeyboardMarkup(keyboard)

# ========== قیمت جهانی ==========
async def world_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    text = "🌍 *قیمت‌های جهانی* 🌍\n\n"
    text += "🪨 کنسانتره سنگ آهن: *$85*/تن\n"
    text += "🟤 گندله: *$105*/تن\n"
    text += "🏭 آهن اسفنجی: *$200*/تن\n"
    text += "🔩 شمش فولادی: *$480*/تن\n"
    text += "📏 میلگرد: *$550*/تن\n"
    text += "\n📌 منابع: Platts / Fastmarkets"
    
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ========== قیمت ایران ==========
async def iran_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    text = "🇮🇷 *قیمت‌های داخلی ایران* 🇮🇷\n\n"
    text += "🪨 کنسانتره سنگ آهن: *۴,۸۰۰,۰۰۰* تومان/تن\n"
    text += "🟤 گندله: *۶,۸۰۰,۰۰۰* تومان/تن\n"
    text += "🏭 آهن اسفنجی: *۱۵,۵۰۰* تومان/تن\n"
    text += "🔩 شمش فولادی: *۵۵,۰۰۰* تومان/تن\n"
    text += "📏 میلگرد: *۶۵,۰۰۰* تومان/تن\n"
    text += "\n📌 منبع: آهن ملل"
    
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ========== نرخ ارز ==========
async def rate(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    text = "💱 *نرخ دلار بازار آزاد*\n\n🇺🇸 ۱ دلار = *۱۷۸,۰۰۰* تومان"
    
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ========== بازگشت به منو ==========
async def back_to_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🇮🇷 قیمت ایران", callback_data="iran")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await query.edit_message_text(
        "🤖 *ربات قیمت آهن و فولاد*\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== اجرای اصلی ==========
def main():
    if not TOKEN:
        logger.error("BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(world_price, pattern="^world$"))
    app.add_handler(CallbackQueryHandler(iran_price, pattern="^iran$"))
    app.add_handler(CallbackQueryHandler(rate, pattern="^rate$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
    
    logger.info("🤖 ربات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
