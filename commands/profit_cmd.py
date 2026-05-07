from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from datetime import datetime

# States
PRODUCT, PURCHASE, FOB, RATE, TONNAGE, FREIGHT, PORT = range(7)

# In-memory database
user_data = {}

# ========== تابع شروع - مورد نیاز main.py ==========
async def profit_start(update: Update, context):
    """شروع فرآیند محاسبه سود - این تابع توسط main.py فراخوانی میشه"""
    user_id = update.message.from_user.id
    user_data[user_id] = {}
    
    keyboard = [
        [InlineKeyboardButton("Iron Ore 62%", callback_data="prod_1"),
         InlineKeyboardButton("Fe 65%", callback_data="prod_2")],
        [InlineKeyboardButton("Pellet", callback_data="prod_3"),
         InlineKeyboardButton("Billet", callback_data="prod_4")],
        [InlineKeyboardButton("Custom price", callback_data="prod_5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Step 1/7: Select product:", reply_markup=reply_markup)
    return PRODUCT

# ========== Step functions ==========
async def step1_product(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    user_data[user_id]["product"] = text
    await update.message.reply_text("Step 2/7: Purchase price (USD per ton)?\nExample: 105")
    return PURCHASE

async def step2_purchase(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["purchase"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return PURCHASE
    await update.message.reply_text("Step 3/7: FOB selling price (USD per ton)?\nExample: 118.5")
    return FOB

async def step3_fob(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["fob"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return FOB
    await update.message.reply_text("Step 4/7: Exchange rate (Rials per USD)?\nExample: 65000")
    return RATE

async def step4_rate(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["rate"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return RATE
    await update.message.reply_text("Step 5/7: Tonnage (tons)?\nExample: 5000")
    return TONNAGE

async def step5_tonnage(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["tonnage"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return TONNAGE
    await update.message.reply_text("Step 6/7: Freight cost (USD per ton)?\nExample: 18")
    return FREIGHT

async def step6_freight(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["freight"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return FREIGHT
    await update.message.reply_text("Step 7/7: Port and loading cost (USD per ton)?\nExample: 4")
    return PORT

async def step7_port(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["port"] = float(update.message.text)
    except:
        await update.message.reply_text("Please enter a valid number")
        return PORT

    # Calculate profit
    data = user_data[user_id]
    t = data["tonnage"]
    purchase = data["purchase"]
    fob = data["fob"]
    rate = data["rate"]
    freight = data["freight"]
    port = data["port"]

    revenue_usd = fob * t
    purchase_cost = purchase * t
    freight_cost = freight * t
    port_cost = port * t
    total_cost = purchase_cost + freight_cost + port_cost
    profit_usd = revenue_usd - total_cost
    profit_rials = profit_usd * rate

    now = datetime.now().strftime("%b %d, %Y - %H:%M")

    result = (
        f"=== PROFIT CALCULATION ===\n"
        f"{now}\n"
        f"------------------------\n"
        f"Product: {data['product']}\n"
        f"Tonnage: {t:,.0f} tons\n"
        f"Purchase price: ${purchase}/ton\n"
        f"FOB price: ${fob}/ton\n"
        f"Exchange rate: {rate:,.0f} Rials\n"
        f"------------------------\n"
        f"Revenue: ${revenue_usd:,.0f}\n"
        f"Purchase cost: ${purchase_cost:,.0f}\n"
        f"Freight: ${freight_cost:,.0f}\n"
        f"Port costs: ${port_cost:,.0f}\n"
        f"Total Cost: ${total_cost:,.0f}\n"
        f"------------------------\n"
        f"Net Profit (USD): ${profit_usd:,.0f}\n"
        f"Net Profit (Rials): {profit_rials:,.0f}\n"
        f"------------------------"
    )

    await update.message.reply_text(result)
    del user_data[user_id]
    return ConversationHandler.END

# ========== تابع مرحله - مورد نیاز main.py ==========
async def profit_step(update: Update, context):
    """پردازش مرحله به مرحله - این تابع توسط main.py فراخوانی میشه"""
    # این تابع به عنوان یک تابع wrapper عمل میکنه
    # بسته به اینکه کاربر در چه مرحله‌ای هست، تابع مناسب رو صدا میزنه
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("Please start over with /start")
        return ConversationHandler.END
    
    data = user_data[user_id]
    
    # تشخیص مرحله فعلی بر اساس داده‌های موجود
    if "product" not in data:
        return await step1_product(update, context)
    elif "purchase" not in data:
        return await step2_purchase(update, context)
    elif "fob" not in data:
        return await step3_fob(update, context)
    elif "rate" not in data:
        return await step4_rate(update, context)
    elif "tonnage" not in data:
        return await step5_tonnage(update, context)
    elif "freight" not in data:
        return await step6_freight(update, context)
    elif "port" not in data:
        return await step7_port(update, context)
    else:
        await update.message.reply_text("Calculation complete! Start again with /start")
        return ConversationHandler.END
