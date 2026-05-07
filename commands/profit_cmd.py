from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from datetime import datetime
import requests

# States
PRODUCT, PURCHASE, RATE_RIAL, RATE_DIRHAM, TONNAGE, FREIGHT, PORT = range(7)

# In-memory database
user_data = {}

# ========== دریافت نرخ ارز ==========
def get_usd_rial_rate():
    """دریافت نرخ دلار به ریال از بازار آزاد"""
    try:
        response = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        if response.status_code == 200:
            data = response.json()
            usdt_irt = data.get("stats", {}).get("USDT-IRT", {})
            price = float(usdt_irt.get("latest", 0))
            if price > 0:
                return price
    except:
        pass
    
    try:
        response = requests.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5)
        if response.status_code == 200:
            data = response.json()
            price = float(data.get("price", 0))
            if price > 0:
                return price
    except:
        pass
    
    return 65000

def get_usd_dirham_rate():
    """دریافت نرخ دلار به درهم"""
    try:
        response = requests.get("https://api.exchangerate.fun/latest?base=USD", timeout=5)
        if response.status_code == 200:
            data = response.json()
            aed_rate = data.get("rates", {}).get("AED")
            if aed_rate:
                return float(aed_rate)
    except:
        pass
    return 3.67

# ========== تابع شروع ==========
async def profit_start(update: Update, context):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        message = query.message
    elif update.message:
        user_id = update.message.from_user.id
        message = update.message
    else:
        return PRODUCT
    
    user_data[user_id] = {}
    
    keyboard = [
        [InlineKeyboardButton("🪨 Iron Ore 62%", callback_data="prod_1"),
         InlineKeyboardButton("🪨 Fe 65%", callback_data="prod_2")],
        [InlineKeyboardButton("🟤 Pellet", callback_data="prod_3"),
         InlineKeyboardButton("🔩 Billet", callback_data="prod_4")],
        [InlineKeyboardButton("✏️ Custom", callback_data="prod_5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "📊 Step 1: Select Product:",
        reply_markup=reply_markup
    )
    
    return PRODUCT

# ========== انتخاب محصول ==========
async def product_selection(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    products = {
        "prod_1": "Iron Ore 62%",
        "prod_2": "Fe 65%", 
        "prod_3": "Pellet",
        "prod_4": "Billet",
        "prod_5": "Custom"
    }
    
    user_data[user_id]["product"] = products.get(query.data, "Unknown")
    
    await query.edit_message_text(
        f"✅ Product: {user_data[user_id]['product']}\n\n"
        f"💰 Step 2: Purchase price (USD/ton)?\nExample: 105"
    )
    
    return PURCHASE

# ========== Step 2 ==========
async def step1_product(update: Update, context):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["product"] = update.message.text
    await update.message.reply_text("💰 Step 2: Purchase price (USD/ton)?\nExample: 105")
    return PURCHASE

async def step2_purchase(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["purchase"] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Please enter a valid number")
        return PURCHASE
    
    usd_rial = get_usd_rial_rate()
    usd_dirham = get_usd_dirham_rate()
    
    user_data[user_id]["suggested_rial_rate"] = usd_rial
    user_data[user_id]["suggested_dirham_rate"] = usd_dirham
    
    await update.message.reply_text(
        f"💱 Step 3: USD to RIAL rate?\n"
        f"Current: {usd_rial:,.0f}\n"
        f"Send 0 to use current:"
    )
    return RATE_RIAL

async def step3_rate_rial(update: Update, context):
    user_id = update.effective_user.id
    try:
        val = float(update.message.text)
        if val == 0:
            user_data[user_id]["rate_rial"] = user_data[user_id]["suggested_rial_rate"]
        else:
            user_data[user_id]["rate_rial"] = val
    except:
        await update.message.reply_text("❌ Invalid number")
        return RATE_RIAL
    
    usd_dirham = user_data[user_id]["suggested_dirham_rate"]
    await update.message.reply_text(
        f"💱 Step 4: USD to DIRHAM rate?\n"
        f"Current: {usd_dirham:.2f}\n"
        f"Send 0 to use current:"
    )
    return RATE_DIRHAM

async def step4_rate_dirham(update: Update, context):
    user_id = update.effective_user.id
    try:
        val = float(update.message.text)
        if val == 0:
            user_data[user_id]["rate_dirham"] = user_data[user_id]["suggested_dirham_rate"]
        else:
            user_data[user_id]["rate_dirham"] = val
    except:
        await update.message.reply_text("❌ Invalid number")
        return RATE_DIRHAM
    
    await update.message.reply_text("⚖️ Step 5: Tonnage (tons)?\nExample: 5000")
    return TONNAGE

async def step5_tonnage(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["tonnage"] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Invalid number")
        return TONNAGE
    await update.message.reply_text("🚢 Step 6: Freight cost (USD/ton)?\nExample: 18")
    return FREIGHT

async def step6_freight(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["freight"] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Invalid number")
        return FREIGHT
    await update.message.reply_text("⚓ Step 7: Port cost (USD/ton)?\nExample: 4")
    return PORT

async def step7_port(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["port"] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Invalid number")
        return PORT

    # Calculate
    data = user_data[user_id]
    t = data["tonnage"]
    purchase = data["purchase"]
    rate_rial = data["rate_rial"]
    rate_dirham = data["rate_dirham"]
    freight = data.get("freight", 0)
    port = data.get("port", 0)
    
    fob = purchase * 1.2
    revenue_usd = fob * t
    purchase_cost = purchase * t
    freight_cost = freight * t
    port_cost = port * t
    total_cost = purchase_cost + freight_cost + port_cost
    profit_usd = revenue_usd - total_cost
    profit_rial = profit_usd * rate_rial
    profit_dirham = profit_usd * rate_dirham
    
    now = datetime.now().strftime("%b %d, %Y - %H:%M")

    result = (
        f"📊 PROFIT CALCULATION 📊\n"
        f"{now}\n"
        f"{'-'*30}\n"
        f"Product: {data['product']}\n"
        f"Tonnage: {t:,.0f} tons\n"
        f"Purchase: ${purchase:.2f}/ton\n"
        f"FOB: ${fob:.2f}/ton\n"
        f"{'-'*30}\n"
        f"Revenue: ${revenue_usd:,.0f}\n"
        f"Cost: ${total_cost:,.0f}\n"
        f"{'-'*30}\n"
        f"Profit USD: ${profit_usd:,.0f}\n"
        f"Profit RIALS: {profit_rial:,.0f}\n"
        f"Profit DIRHAM: {profit_dirham:,.0f}"
    )

    await update.message.reply_text(result)
    del user_data[user_id]
    return ConversationHandler.END

# ========== Main step handler ==========
async def profit_step(update: Update, context):
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("❌ Start over with /start")
        return ConversationHandler.END
    
    data = user_data[user_id]
    
    if "product" not in data:
        return await step1_product(update, context)
    elif "purchase" not in data:
        return await step2_purchase(update, context)
    elif "rate_rial" not in data:
        return await step3_rate_rial(update, context)
    elif "rate_dirham" not in data:
        return await step4_rate_dirham(update, context)
    elif "tonnage" not in data:
        return await step5_tonnage(update, context)
    elif "freight" not in data:
        return await step6_freight(update, context)
    elif "port" not in data:
        return await step7_port(update, context)
    else:
        await update.message.reply_text("✅ Done! Start again with /start")
        return ConversationHandler.END
