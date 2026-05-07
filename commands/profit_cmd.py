from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from datetime import datetime
import requests

# States
PRODUCT, PURCHASE, FOB, RATE_RIAL, RATE_DIRHAM, TONNAGE, FREIGHT, PORT = range(8)

# In-memory database
user_data = {}

# ========== دریافت نرخ ارز ==========
def get_usd_rial_rate():
    """دریافت نرخ دلار به ریال از بازار آزاد"""
    try:
        response = requests.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data.get("price", 65000))
    except:
        pass
    return 65000

def get_usd_dirham_rate():
    """دریافت نرخ دلار به درهم امارات"""
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data.get("rates", {}).get("AED", 3.67))
    except:
        pass
    return 3.67

# ========== تابع شروع - اصلاح شده ==========
async def profit_start(update: Update, context):
    """شروع فرآیند محاسبه سود - هم برای دکمه و هم برای پیام مستقیم کار میکنه"""
    
    # تشخیص نوع درخواست
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
        [InlineKeyboardButton("✏️ Custom price", callback_data="prod_5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "📊 *Step 1/8: Select Product*\n\n"
        "Choose one of the options below:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
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
        "prod_2": "Fe 65% Concentrate", 
        "prod_3": "Pellet",
        "prod_4": "Billet",
        "prod_5": "Custom"
    }
    
    product_name = products.get(query.data, "Unknown")
    user_data[user_id]["product"] = product_name
    
    await query.edit_message_text(
        f"✅ *Product Selected:* {product_name}\n\n"
        f"💰 *Step 2/8:* Purchase price (USD per ton)?\n"
        f"📝 Example: `105`",
        parse_mode="Markdown"
    )
    
    return PURCHASE

# ========== Step functions ==========
async def step1_product(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    user_data[user_id]["product"] = text
    await update.message.reply_text("💰 Step 2/8: Purchase price (USD per ton)?\nExample: 105")
    return PURCHASE

async def step2_purchase(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["purchase"] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Please enter a valid number")
        return PURCHASE
    
    await update.message.reply_text("📊 Fetching exchange rates...")
    usd_rial = get_usd_rial_rate()
    usd_dirham = get_usd_dirham_rate()
    
    user_data[user_id]["suggested_rial_rate"] = usd_rial
    user_data[user_id]["suggested_dirham_rate"] = usd_dirham
    
    await update.message.reply_text(
        f"💱 *Step 3/8:* USD to RIAL exchange rate?\n\n"
        f"💰 Current market rate: `{usd_rial:,.0f}` Rials/USD\n"
        f"📝 Send `0` to use market rate or enter custom:",
        parse_mode="Markdown"
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
        await update.message.reply_text("❌ Please enter a valid number")
        return RATE_RIAL
    
    usd_dirham = user_data[user_id]["suggested_dirham_rate"]
    await update.message.reply_text(
        f"💱 *Step 4/8:* USD to DIRHAM exchange rate?\n\n"
        f"💰 Current market rate: `{usd_dirham:.2f}` Dirhams/USD\n"
        f"📝 Send `0` to use market rate or enter custom:",
        parse_mode="Markdown"
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
        await update.message.reply_text("❌ Please enter a valid number")
        return RATE_DIRHAM
    
    await update.message.reply_text("⚖️ *Step 5/8:* Tonnage (tons)?\n📝 Example: `5000`", parse_mode="Markdown")
    return TONNAGE

async def step5_tonnage(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["tonnage"] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Please enter a valid number")
        return TONNAGE
    await update.message.reply_text("🚢 *Step 6/8:* Freight cost (USD per ton)?\n📝 Example: `18`", parse_mode="Markdown")
    return FREIGHT

async def step6_freight(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["freight"] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Please enter a valid number")
        return FREIGHT
    await update.message.reply_text("⚓ *Step 7/8:* Port and loading cost (USD per ton)?\n📝 Example: `4`", parse_mode="Markdown")
    return PORT

async def step7_port(update: Update, context):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["port"] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Please enter a valid number")
        return PORT

    # Calculate profit
    data = user_data[user_id]
    t = data["tonnage"]
    purchase = data["purchase"]
    rate_rial = data["rate_rial"]
    rate_dirham = data["rate_dirham"]
    freight = data.get("freight", 0)
    port = data.get("port", 0)
    
    # FOB = purchase + 20% profit margin
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
        f"📊 *=== PROFIT CALCULATION ===* 📊\n"
        f"📅 {now}\n"
        f"{'─' * 35}\n"
        f"📦 *Product:* {data['product']}\n"
        f"⚖️ *Tonnage:* {t:,.0f} tons\n"
        f"💰 *Purchase:* ${purchase:.2f}/ton\n"
        f"💵 *FOB:* ${fob:.2f}/ton\n"
        f"{'─' * 35}\n"
        f"💲 *Revenue:* ${revenue_usd:,.0f}\n"
        f"📥 *Purchase cost:* ${purchase_cost:,.0f}\n"
        f"🚢 *Freight:* ${freight_cost:,.0f}\n"
        f"⚓ *Port costs:* ${port_cost:,.0f}\n"
        f"📊 *Total Cost:* ${total_cost:,.0f}\n"
        f"{'─' * 35}\n"
        f"✅ *Net Profit (USD):* ${profit_usd:,.0f}\n"
        f"✅ *Net Profit (RIALS):* {profit_rial:,.0f} Rials\n"
        f"✅ *Net Profit (DIRHAM):* {profit_dirham:,.0f} Dirhams\n"
        f"{'─' * 35}"
    )

    await update.message.reply_text(result, parse_mode="Markdown")
    del user_data[user_id]
    return ConversationHandler.END

# ========== تابع مرحله - برای main.py ==========
async def profit_step(update: Update, context):
    """پردازش مرحله به مرحله"""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("❌ Please start over with /start")
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
        await update.message.reply_text("✅ Calculation complete! Start again with /start")
        return ConversationHandler.END
