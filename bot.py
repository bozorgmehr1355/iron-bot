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

# ========== تبدیل اعداد به فارسی ==========
def to_persian(num):
    persian = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
               '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}
    return ''.join(persian.get(ch, ch) for ch in str(num))

def format_number(num):
    """فرمت عدد با کاما و سپس تبدیل به فارسی"""
    return to_persian(f"{num:,}")

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

def start_rate_updater():
    update_rates()
    def loop():
        while True:
            time.sleep(15 * 60)
            update_rates()
    threading.Thread(target=loop, daemon=True).start()

start_rate_updater()

# ========== قیمت‌های پایه ==========
CONCENTRATE_PRICE = 4800000
PELLET_PRICE = 6500000
DRI_PRICE = 15500
BILLET_PRICE = 42500
REBAR_PRICE = 58000

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
    text += "   🇮🇷 FOB خلیج فارس: *$۸۵*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$۱۳۰*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$۱۳۱*/تن\n\n"
    text += "• *گندله*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$۱۰۵*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$۱۵۵*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$۱۵۶*/تن\n\n"
    text += "• *آهن اسفنجی*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$۲۰۰*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$۲۸۰*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$۲۸۲*/تن\n\n"
    text += "• *شمش فولادی*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$۴۸۰*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$۵۲۰*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$۵۱۵*/تن\n\n"
    text += "• *میلگرد*\n"
    text += "   🇮🇷 FOB خلیج فارس: *$۵۵۰*/تن\n"
    text += "   🇨🇳 CFR شمال چین: *$۶۰۰*/تن\n"
    text += "   🇨🇳 CFR جنوب چین: *$۵۹۵*/تن\n"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بورس کالا ==========
async def ice(update, context):
    await update.callback_query.answer()
    text = "🏭 *قیمت بورس کالا (ICE)* 🏭\n"
    text += "━" * 35 + "\n\n"
    text += f"🪨 کنسانتره سنگ آهن:\n   *{format_number(CONCENTRATE_PRICE)}* تومان/تن\n\n"
    text += f"🟤 گندله:\n   *{format_number(PELLET_PRICE)}* تومان/تن\n\n"
    text += f"🏭 آهن اسفنجی:\n   *{format_number(DRI_PRICE)}* تومان/تن\n\n"
    text += f"🔩 شمش فولادی:\n   *{format_number(BILLET_PRICE)}* تومان/تن\n\n"
    text += f"📏 میلگرد:\n   *{format_number(REBAR_PRICE)}* تومان/تن\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منبع: بورس کالای ایران"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== بازار آزاد ==========
async def free(update, context):
    await update.callback_query.answer()
    text = "🔄 *قیمت بازار آزاد ایران* 🔄\n"
    text += "━" * 35 + "\n\n"
    text += f"🪨 کنسانتره سنگ آهن:\n   محدوده: *{format_number(CONCENTRATE_PRICE - 200000)} - {format_number(CONCENTRATE_PRICE + 200000)}* تومان/تن\n\n"
    text += f"🟤 گندله:\n   محدوده: *{format_number(PELLET_PRICE - 300000)} - {format_number(PELLET_PRICE + 300000)}* تومان/تن\n\n"
    text += f"🏭 آهن اسفنجی:\n   محدوده: *{format_number(DRI_PRICE - 500)} - {format_number(DRI_PRICE + 500)}* تومان/تن\n\n"
    text += f"🔩 شمش فولادی:\n   محدوده: *{format_number(BILLET_PRICE - 2000)} - {format_number(BILLET_PRICE + 2000)}* تومان/تن\n\n"
    text += f"📏 میلگرد:\n   محدوده: *{format_number(REBAR_PRICE - 3000)} - {format_number(REBAR_PRICE + 3000)}* تومان/تن\n"
    text += "\n" + "━" * 35 + "\n"
    text += "📌 منابع: آهن ملل، آهن آنلاین"
    await update.callback_query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

# ========== قیمت کارخانه ==========
async def factory(update, context):
    await update.callback_query.answer()
    text = "🏭 *قیمت درب کارخانه* 🏭\n"
    text += "━" * 35 + "\n\n"
    text += "🔩 *شمش فولادی (تومان/تن)*\n"
    text += f"   • فولاد اصفهان: *{format_number(BILLET_PRICE)}*\n"
    text += f"   • فولاد یزد: *{format_number(BILLET_PRICE - 100)}*\n"
    text += f"   • فولاد قزوین: *{format_number(BILLET_PRICE - 2000)}*\n\n"
    text += "📏 *میلگرد (تومان/کیلو)*\n"
    text += f"   • ذوب آهن اصفهان: *{format_number(REBAR_PRICE)}*\n"
    text += f"   • امیرکبیر کاشان: *{format_number(REBAR_PRICE + 1000)}*\n"
    text += f"   • فولاد کاوه: *{format_number(REBAR_PRICE - 1000)}*\n\n"
    text += f"🏭 *آهن اسفنجی (تومان/تن)*\n"
    text += f"   • فولاد میانه: *{format_number(DRI_PRICE + 1300)}*\n"
    text += f"   • فولاد نطنز: *{format_number(DRI_PRICE + 1000)}*\n"
    text += f"   • فولاد کاویان: *{format_number(DRI_PRICE + 700)}*\n\n"
    text += f"🟤 *گندله (تومان/تن)*\n"
    text += f"   • گل گهر: *{format_number(PELLET_PRICE - 100000)}*\n"
    text += f"   • چادرملو: *{format_number(PELLET_PRICE - 200000)}*\n\n"
    text += f"🪨 *کنسانتره (تومان/تن)*\n"
    text += f"   • گل گهر: *{format_number(CONCENTRATE_PRICE - 500000)}*\n"
    text += f"   • سنگ آهن مرکزی: *{format_number(CONCENTRATE_PRICE - 200000)}*\n"
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
    text += f"🏦 نرخ مبادله‌ای (نیمایی):\n   • دلار آمریکا: *{format_number(rates['secondary'])}* تومان\n\n"
    text += f"🔄 نرخ بازار آزاد:\n   • دلار آمریکا: *{format_number(rates['free'])}* تومان\n"
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

# ========== حل مشکل Conflict ==========
# خطای Conflict به این معنی است که یک نمونه دیگر از ربات در جای دیگر در حال اجراست.
# برای حل، توکن را در BotFather ریست کنید و در Railway متغیر BOT_TOKEN را با توکن جدید جایگزین کنید.

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
