from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
import os

PRODUCT, PRICE = range(2)
user_data = {}

async def start(update: Update, context):
    keyboard = [[InlineKeyboardButton("محاسبه سود", callback_data="profit")]]
    await update.message.reply_text("ربات محاسبه سود", reply_markup=InlineKeyboardMarkup(keyboard))

async def profit_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {}
    await query.edit_message_text("اسم محصول رو بنویس:")
    return PRODUCT

async def get_product(update: Update, context):
    uid = update.effective_user.id
    user_data[uid]["product"] = update.message.text
    await update.message.reply_text("قیمت خرید هر تن به دلار؟")
    return PRICE

async def get_price(update: Update, context):
    uid = update.effective_user.id
    try:
        price = float(update.message.text)
        product = user_data[uid]["product"]
        await update.message.reply_text(f"محصول: {product}\nقیمت: {price} دلار\nسود تقریبی: {price * 0.2:.0f} دلار")
        del user_data[uid]
        return ConversationHandler.END
    except:
        await update.message.reply_text("عدد وارد کن")
        return PRICE

async def cancel(update, context):
    uid = update.effective_user.id
    if uid in user_data:
        del user_data[uid]
    await update.message.reply_text("لغو شد")

def main():
    app = Application.builder().token(os.environ.get("BOT_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(profit_start, pattern="^profit$")],
        states={
            PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    
    print("ربات روشن شد")
    app.run_polling()

if __name__ == "__main__":
    main()
