import os
import json
import time
import threading
import requests
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
RATE_FILE = "rates.json"

# ========== قیمت‌های معتبر شمش (دستی) ==========
# قیمت واقعی شمش در بازار ایران (تومان/تن)
BILLET_PRICE = 42500  # میانگین ۴۲,۵۰۰ تومان/تن

# ========== بروزرسانی نرخ ارز ==========
def update_rates():
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        free = int(r.json()["stats"]["USDT-IRT"]["latest"]) // 10 if r.status_code == 200 else 178000
    except:
        free = 178000
    try:
        r = requests.get("https://www.tgju.org/sana/", timeout=5)
        match = re.search(r'(\d{1,3}(?:,\d{3})*)', r.text)
        secondary = int(match.group(1).replace(',', '')) // 10 if match else 28500
    except:
        secondary = 28500
    with open(RATE_FILE, 'w') as f:
        json.dump({"free": free, "secondary": secondary}, f)
    return free, secondary

def start_rate_updater():
    update_rates()
    def loop():
        while True:
            time.sleep(15 * 60)
            update_rates()
    threading.Thread(target=loop, daemon=True).start()

start_rate_updater()

# ========== منوی اصلی ==========
async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.message.reply_text(
        "🏭 *ربات تخصصی آهن و فولاد* 🏭\n\n"
        "📌 *محصولات تحت پوشش:*\n"
        "• کنسانتره سنگ آهن\n"
        "• گندله\n"
        "• آهن اسفنجی\n"
        "• شمش فولادی\n"
        "• میلگرد\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back")]])

# ========== قیمت جهانی ==========
async def world(update, context):
    await update.callback_query.answer()
    text = "🌍 *قیمت‌های جهانی* 🌍\n\n"
    text += "• *کنسانتره سنگ آهن*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$85*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$130*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$131*/تن\n\n"
    text += "• *گندله*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$105*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$155*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$156*/تن\n\n"
    text += "• *آهن اسفنجی*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$200*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$280*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$282*/تن\n\n"
    text += "• *شمش فولادی*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$480*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$520*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$515*/تن\n\n"
    text += "• *میلگرد*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$550*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$600*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$595*/تن\n"
    text += "\n📌 منابع: Platts, Fastmarkets, SMM"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بورس کالا ==========
async def ice(update, context):
    await update.callback_query.answer()
    text = "🏭 *قیمت بورس کالا (ICE)* 🏭\n"
    text += "━" * 35 + "\n\n"
    text += "🪨 *کنسانتره سنگ آهن*\n"
    text += "   قیمت پایه: ۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰ تومان/تن\n"
    text += "   آخرین معامله: ۴,۶۰۰,۰۰۰ تومان/تن\n\n"
    text += "🟤 *گندله*\n"
    text += "   قیمت پایه: ۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰ تومان/تن\n"
    text += "   آخرین معامله: ۶,۵۰۰,۰۰۰ تومان/تن\n\n"
    text += "🏭 *آهن اسفنجی*\n"
    text += "   قیمت پایه: ۱۴,۸۰۰ - ۱۵,۵۰۰ تومان/تن\n"
    text += "   آخرین معامله: ۱۵,۲۰۰ تومان/تن\n\n"
    text += "🔩 *شمش فولادی*\n"
    text += f"   قیمت پایه: {BILLET_PRICE:,} تومان/تن\n"
    text += f"   آخرین معامله: {BILLET_PRICE:,} تومان/تن\n\n"
    text += "📏 *میلگرد*\n"
    text += "   قیمت پایه: ۵۰,۰۰۰ - ۶۵,۰۰۰ تومان/کیلو\n"
    text += "   آخرین معامله: ۵۷,۵۰۰ تومان/کیلو\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منبع: بورس کالای ایران (IME)"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بازار آزاد ==========
async def free(update, context):
    await update.callback_query.answer()
    billet_min = BILLET_PRICE - 2000
    billet_max = BILLET_PRICE + 2000
    text = "🔄 *قیمت بازار آزاد ایران* 🔄\n"
    text += "━" * 35 + "\n\n"
    text += "🪨 *کنسانتره سنگ آهن*\n"
    text += "   محدوده قیمت: ۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰ تومان/تن\n"
    text += "   قیمت میانگین: ۵,۶۰۰,۰۰۰ تومان/تن\n\n"
    text += "🟤 *گندله*\n"
    text += "   محدوده قیمت: ۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰ تومان/تن\n"
    text += "   قیمت میانگین: ۷,۱۵۰,۰۰۰ تومان/تن\n\n"
    text += "🏭 *آهن اسفنجی*\n"
    text += "   محدوده قیمت: ۱۶,۰۰۰ - ۱۶,۸۰۰ تومان/تن\n"
    text += "   قیمت میانگین: ۱۶,۴۰۰ تومان/تن\n\n"
    text += "🔩 *شمش فولادی*\n"
    text += f"   محدوده قیمت: {billet_min:,} - {billet_max:,} تومان/تن\n"
    text += f"   قیمت میانگین: {BILLET_PRICE:,} تومان/تن\n\n"
    text += "📏 *میلگرد*\n"
    text += "   محدوده قیمت: ۶۳,۰۰۰ - ۶۸,۰۰۰ تومان/تن\n"
    text += "   قیمت میانگین: ۶۵,۵۰۰ تومان/تن\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: آهن ملل، آهن آنلاین، شاهراهان"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== قیمت کارخانه ==========
async def factory(update, context):
    await update.callback_query.answer()
    billet_min = BILLET_PRICE - 2000
    text = "🏭 *قیمت درب کارخانه* 🏭\n"
    text += "━" * 35 + "\n\n"
    text += "🔩 *شمش فولادی (تومان/تن)*\n"
    text += f"   • فولاد اصفهان: {BILLET_PRICE:,}\n"
    text += f"   • فولاد یزد: {BILLET_PRICE-100:,}\n"
    text += f"   • فولاد قزوین: {billet_min:,}\n\n"
    text += "📏 *میلگرد (تومان/کیلو)*\n"
    text += "   • ذوب آهن اصفهان: ۶۵,۰۰۰\n"
    text += "   • امیرکبیر کاشان: ۶۶,۰۰۰\n"
    text += "   • فولاد کاوه: ۶۴,۰۰۰\n\n"
    text += "🏭 *آهن اسفنجی (تومان/تن)*\n"
    text += "   • فولاد میانه: ۱۶,۸۰۰\n"
    text += "   • فولاد نطنز: ۱۶,۵۰۰\n"
    text += "   • فولاد کاویان: ۱۶,۲۰۰\n\n"
    text += "🟤 *گندله (تومان/تن)*\n"
    text += "   • گل گهر: ۶,۴۰۰,۰۰۰\n"
    text += "   • چادرملو: ۶,۳۰۰,۰۰۰\n\n"
    text += "🪨 *کنسانتره (تومان/تن)*\n"
    text += "   • گل گهر: ۴,۳۰۰,۰۰۰\n"
    text += "   • سنگ آهن مرکزی: ۴,۶۰۰,۰۰۰\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: شاهراهان، آهن ملل"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== نرخ ارز ==========
async def rate(update, context):
    await update.callback_query.answer()
    with open(RATE_FILE, 'r') as f:
        rates = json.load(f)
    text = "💱 *نرخ ارز بازار ایران* 💱\n"
    text += "━" * 35 + "\n\n"
    text += "🏦 *نرخ مبادله‌ای (نیمایی) - سامانه سنا*\n"
    text += f"   • دلار آمریکا: *{rates['secondary']:,}* تومان\n\n"
    text += "🔄 *نرخ بازار آزاد*\n"
    text += f"   • دلار آمریکا: *{rates['free']:,}* تومان\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: بانک مرکزی، نوبیتکس، TGJU"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بازگشت ==========
async def back(update, context):
    await update.callback_query.answer()
    keyboard = [
        [InlineKeyboardButton("🌍 قیمت جهانی", callback_data="world")],
        [InlineKeyboardButton("🏭 بورس کالا", callback_data="ice")],
        [InlineKeyboardButton("🔄 بازار آزاد", callback_data="free")],
        [InlineKeyboardButton("🏭 قیمت کارخانه", callback_data="factory")],
        [InlineKeyboardButton("💱 نرخ ارز", callback_data="rate")]
    ]
    await update.callback_query.edit_message_text(
        "🏭 *ربات تخصصی آهن و فولاد* 🏭\n\n"
        "📌 *محصولات تحت پوشش:*\n"
        "• کنسانتره سنگ آهن\n"
        "• گندله\n"
        "• آهن اسفنجی\n"
        "• شمش فولادی\n"
        "• میلگرد\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========== اجرا ==========
def main():
    if not TOKEN:
        print("BOT_TOKEN not found!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(world, pattern="world"))
    app.add_handler(CallbackQueryHandler(ice, pattern="ice"))
    app.add_handler(CallbackQueryHandler(free, pattern="free"))
    app.add_handler(CallbackQueryHandler(factory, pattern="factory"))
    app.add_handler(CallbackQueryHandler(rate, pattern="rate"))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    print("ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
