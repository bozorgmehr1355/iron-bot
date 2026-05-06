from services.iron import get_iron_62, get_fe65
from services.billet import get_billet_price
from services.forex import get_usd_free

user_data = {}

async def profit_start(update, context):
    user_id = update.message.from_user.id
    user_data[user_id] = {}
    await update.message.reply_text(
        "Step 1/7: Product type?\n"
        "1. Iron Ore 62%\n"
        "2. Fe 65% Concentrate\n"
        "3. Pellet\n"
        "4. Billet\n"
        "5. Custom price\n\n"
        "Send the number (1-5):"
    )

async def profit_step(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id not in user_data:
        return

    data = user_data[user_id]

    if "product" not in data:
        products = {
            "1": ("Iron Ore 62%", get_iron_62),
            "2": ("Fe 65% Concentrate", get_fe65),
            "3": ("Pellet", lambda: round(get_iron_62() + 15, 2)),
            "4": ("Billet", get_billet_price),
            "5": ("Custom", None)
        }
        if text not in products:
            await update.message.reply_text("Please send a number between 1-5")
            return
        name, fn = products[text]
        data["product"] = name
        data["price_fn"] = fn
        await update.message.reply_text(
            "Step 2/7: Purchase price in Iran ($/ton)?\n"
            "(Price you buy the product)\n"
            "Example: 95"
        )

    elif "purchase" not in data:
        try:
            data["purchase"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        fn = data.get("price_fn")
        if fn:
            price = fn()
            data["suggested_fob"] = price
            await update.message.reply_text(
                f"Step 3/7: FOB selling price ($/ton)?\n"
                f"Current market: ${price}/ton\n"
                f"Press 0 to use market price or enter custom:"
            )
        else:
            await update.message.reply_text(
                "Step 3/7: FOB selling price ($/ton)?\n"
                "Example: 119"
            )

    elif "fob" not in data:
        try:
            val = float(text)
            if val == 0 and "suggested_fob" in data:
                data["fob"] = data["suggested_fob"]
            else:
                data["fob"] = val
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        rate = get_usd_free()
        if rate:
            clean = rate.replace(",", "")
            data["suggested_rate"] = clean
            await update.message.reply_text(
                f"Step 4/7: Exchange rate (Rials/USD)?\n"
                f"Current rate: {rate}\n"
                f"Press 0 to use current rate or enter custom:"
            )
        else:
            await update.message.reply_text(
                "Step 4/7: Exchange rate (Rials/USD)?\n"
                "Example: 1798800"
            )

    elif "rate" not in data:
        try:
            val = float(text)
            if val == 0 and "suggested_rate" in data:
                data["rate"] = float(data["suggested_rate"])
            else:
                data["rate"] = val
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text(
            "Step 5/7: Tonnage (tons)?\n"
            "Example: 5000"
        )

    elif "tonnage" not in data:
        try:
            data["tonnage"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text(
            "Step 6/7: Freight cost ($/ton)?\n"
            "Example: 18"
        )

    elif "freight" not in data:
        try:
            data["freight"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return
        await update.message.reply_text(
            "Step 7/7: Port and loading cost ($/ton)?\n"

"Example: 4"
        )

    elif "port" not in data:
        try:
            data["port"] = float(text)
        except:
            await update.message.reply_text("Please enter a valid number")
            return

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

        await update.message.reply_text(
            "Profit Calculation\n"
            "-------------------\n"
            f"Product: {data['product']}\n"
            f"Tonnage: {t:,.0f} tons\n"
            f"Purchase price: ${purchase}/ton\n"
            f"FOB price: ${fob}/ton\n"
            f"Exchange rate: {rate:,.0f}\n"
            "-------------------\n"
            f"Revenue: ${revenue_usd:,.0f}\n"
            f"Purchase cost: ${purchase_cost:,.0f}\n"
            f"Freight: ${freight_cost:,.0f}\n"
            f"Port costs: ${port_cost:,.0f}\n"
            f"Total Cost: ${total_cost:,.0f}\n"
            "-------------------\n"
            f"Net Profit (USD): ${profit_usd:,.0f}\n"
            f"Net Profit (Rials): {profit_rials:,.0f}\n"
        )
        del user_data[user_id]
