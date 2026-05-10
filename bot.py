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
        [InlineKeyboardButton("⚓ قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 قیمت بورس", callback_data="ice")],
        [InlineKeyboardButton("⚙️ قیمت بازار آزاد", callback_data="free_market")],
        [InlineKeyboardButton("🔧 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.message.reply_text(
        "🏭 *ربات صنعتی آهن و فولاد* 🏭\n\n"
        "📊 *محصولات تحت پوشش:*\n"
        "   ⚙️ کنسانتره سنگ آهن\n"
        "   🔩 گندله\n"
        "   ⛏️ آهن اسفنجی\n"
        "   📏 شمش فولادی\n"
        "   🔗 میلگرد\n\n"
        "🎯 *لطفاً یکی از گزینه‌ها را انتخاب کنید:*",
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
    
    text = "⚓ *قیمت‌های جهانی* ⚓\n"
    text += "━" * 35 + "\n\n"
    
    text += "⚙️ *کنسانتره سنگ آهن*\n"
    text += "   🏭 FOB خلیج فارس: *$85*/تن\n"
    text += "   🚢 CFR شمال چین: *$130*/تن\n"
    text += "   🚢 CFR جنوب چین: *$131*/تن\n\n"
    
    text += "🔩 *گندله*\n"
    text += "   🏭 FOB خلیج فارس: *$105*/تن\n"
    text += "   🚢 CFR شمال چین: *$155*/تن\n"
    text += "   🚢 CFR جنوب چین: *$156*/تن\n\n"
    
    text += "⛏️ *آهن اسفنجی*\n"
    text += "   🏭 FOB خلیج فارس: *$200*/تن\n"
    text += "   🚢 CFR شمال چین: *$280*/تن\n"
    text += "   🚢 CFR جنوب چین: *$282*/تن\n\n"
    
    text += "📏 *شمش فولادی*\n"
    text += "   🏭 FOB خلیج فارس: *$480*/تن\n"
    text += "   🚢 CFR شمال چین: *$520*/تن\n"
    text += "   🚢 CFR جنوب چین: *$515*/تن\n\n"
    
    text += "🔗 *میلگرد*\n"
    text += "   🏭 FOB خلیج فارس: *$550*/تن\n"
    text += "   🚢 CFR شمال چین: *$600*/تن\n"
    text += "   🚢 CFR جنوب چین: *$595*/تن\n"
    
    text += "\n━" * 35 + "\n"
    text += "📌 *منابع:* Platts, Fastmarkets, SMM"
    
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ========== قیمت بورس کالا (ICE) ==========
async def ice_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    text = "🏭 *قیمت بورس کالا (ICE)* 🏭\n"
    text += "━" * 35 + "\n\n"
    
    text += "⚙️ کنسانتره سنگ آهن: *۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰* تومان/تن\n"
    text += "🔩 گندله: *۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰* تومان/تن\n"
    text += "⛏️ آهن اسفنجی: *۱۴,۸۰۰ - ۱۵,۵۰۰* تومان/تن\n"
    text += "📏 شمش فولادی: *۴۱,۰۰۰ - ۴۴,۰۰۰* تومان/تن\n"
    text += "🔗 میلگرد: *۱۵,۸۰۰ - ۱۶,۸۰۰* تومان/تن\n"
    
    text += "\n━" * 35 + "\n"
    text += "📌 *منبع:* بورس کالای ایران"
    
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ========== قیمت بازار آزاد ==========
async def free_market_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    text = "⚙️ *قیمت بازار آزاد ایران* ⚙️\n"
    text += "━" * 35 + "\n\n"
    
    text += "⚙️ کنسانتره سنگ آهن: *۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰* تومان/تن\n"
    text += "🔩 گندله: *۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰* تومان/تن\n"
    text += "⛏️ آهن اسفنجی: *۱۶,۰۰۰ - ۱۶,۸۰۰* تومان/تن\n"
    text += "📏 شمش فولادی: *۵۴,۰۰۰ - ۵۷,۰۰۰* تومان/تن\n"
    text += "🔗 میلگرد: *۶۳,۰۰۰ - ۶۸,۰۰۰* تومان/تن\n"
    
    text += "\n━" * 35 + "\n"
    text += "📌 *منابع:* آهن ملل، آهن آنلاین"
    
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ========== قیمت درب کارخانه ==========
async def factory_price(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    text = "🔧 *قیمت درب کارخانه* 🔧\n"
    text += "━" * 35 + "\n\n"
    
    text += "📏 *شمش فولادی (تومان/تن)*\n"
    text += "   🏭 فولاد اصفهان: *۴۳,۰۹۱*\n"
    text += "   🏭 فولاد یزد: *۴۳,۰۰۰*\n"
    text += "   🏭 فولاد قزوین: *۴۰,۴۰۹*\n"
    text += "   🏭 فولاد کاوه: *۴۲,۵۰۰*\n\n"
    
    text += "🔗 *میلگرد (تومان/کیلو)*\n"
    text += "   🏭 ذوب آهن اصفهан: *۶۵,۰۰۰*\n"
    text += "   🏭 امیرکبیر کاشان: *۶۶,۰۰۰*\n"
    text += "   🏭 فولاد کاوه: *۶۴,۰۰۰*\n\n"
    
    text += "⛏️ *آهن اسفنجی (تومان/تن)*\n"
    text += "   🏭 فولاد میانه: *۱۶,۸۰۰*\n"
    text += "   🏭 فولاد نطنز: *۱۶,۵۰۰*\n"
    text += "   🏭 فولاد کاویان: *۱۶,۲۰۰*\n\n"
    
    text += "🔩 *گندله (تومان/تن)*\n"
    text += "   🏭 گل گهر: *۶,۴۰۰,۰۰۰*\n"
    text += "   🏭 چادرملو: *۶,۳۰۰,۰۰۰*\n\n"
    
    text += "⚙️ *کنسانتره (تومان/تن)*\n"
    text += "   🏭 گل گهر: *۴,۳۰۰,۰۰۰*\n"
    text += "   🏭 سنگ آهن مرکزی: *۴,۶۰۰,۰۰۰*\n"
    
    text += "\n━" * 35 + "\n"
    text += "📌 *منابع:* شاهراهان، آهن ملل"
    
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ========== نرخ ارز (آزاد + نیمایی) ==========
async def rate(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    text = "💱 *نرخ ارز بازار ایران* 💱\n"
    text += "━" * 35 + "\n\n"
    
    text += "🏦 *نرخ مبادله‌ای (نیمایی)*\n"
    text += "   🇺🇸 دلار آمریکا: *۴۲,۰۰۰* تومان\n"
    text += "   🇪🇺 یورو: *۴۵,۵۰۰* تومان\n"
    text += "   🇦🇪 درهم امارات: *۱۱,۵۰۰* تومان\n\n"
    
    text += "🔄 *نرخ بازار آزاد*\n"
    text += "   🇺🇸 دلار آمریکا: *۱۷۸,۰۰۰* تومان\n"
    text += "   🇪🇺 یورو: *۱۹۲,۰۰۰* تومان\n"
    text += "   🇦🇪 درهم امارات: *۴۸,۵۰۰* تومان\n"
    
    text += "\n━" * 35 + "\n"
    text += "📌 *منابع:* بانک مرکزی، نوبیتکس، TGJU"
    
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ========== بازگشت به منو ==========
async def back_to_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⚓ قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 قیمت بورس", callback_data="ice")],
        [InlineKeyboardButton("⚙️ قیمت بازار آزاد", callback_data="free_market")],
        [InlineKeyboardButton("🔧 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await query.edit_message_text(
        "🏭 *ربات صنعتی آهن و فولاد* 🏭\n\n"
        "📊 *محصولات تحت پوشش:*\n"
        "   ⚙️ کنسانتره سنگ آهن\n"
        "   🔩 گندله\n"
        "   ⛏️ آهن اسفنجی\n"
        "   📏 شمش فولادی\n"
        "   🔗 میلگرد\n\n"
        "🎯 *لطفاً یکی از گزینه‌ها را انتخاب کنید:*",
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
    app.add_handler(CallbackQueryHandler(ice_price, pattern="^ice$"))
    app.add_handler(CallbackQueryHandler(free_market_price, pattern="^free_market$"))
    app.add_handler(CallbackQueryHandler(factory_price, pattern="^factory$"))
    app.add_handler(CallbackQueryHandler(rate, pattern="^rate$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
    
    logger.info("🏭 ربات صنعتی آهن و فولاد روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
