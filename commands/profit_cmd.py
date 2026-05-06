from services.iron import get_iron_62, get_fe65
from services.billet import get_billet_price

user_data = {}

async def profit_start(update, context):
    user_id = update.message.from_user.id
    user_data[user_id] = {}
    await update.message.reply_text(
        "Step 1/6: Product type?\n"
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
        if fn:
            price = fn()
            data["suggested_price"] = price
            await update.message.reply_text(
                f"Product: {name}\n"
                f"Current market price: ${price}/ton\n\n"
                "Step 2/6: Confirm or enter custom FOB Price ($/ton)?\n"
                f"Press Enter to use ${price} or type custom price:"
            )
        else:
            await update.message.reply_text("Step 2/6: Enter FOB Price ($/ton):")

    elif "fob" not in data:
        if text == "" and "suggested_price" in data:
            data["fob"] = data["suggested_price"]
        else:
            try:
                data["fob"] = float(text)
            except:
                data["fob"] = data.get("suggested_price", 0)
        await update.message.reply_text("Step 3/6: Tonnage (tons)?\nExample: 5000")

    elif "tonnage" not in data:
        data["tonnage"] = float(text)
        await update.message.reply_text("Step 4/6: Freight cost ($/ton)?\nExample: 18")

    elif "freight" not in data:
        data["freight"] = float(text)
        await update.message.reply_text("Step 5/6: Port and loading cost ($/ton)?\nExample: 4")

    elif "port" not in data:
        data["port"] = float(text)
        await update.message.reply_text("Step 6/6: Inland transport ($/ton)?\nExample: 3")

    elif "transport" not in data:
        data["transport"] = float(text)
        t = data["tonnage"]
        revenue = data["fob"] * t
        freight = data["freight"] * t
        port = data["port"] * t
        transport = data["transport"] * t
        total_cost = freight + port + transport
        profit = revenue - total_cost
        await update.message.reply_text(
            "Profit Calculation\n"
            "-------------------\n"
            f"Product: {data['product']}\n"
            f"Tonnage: {t:,.0f} tons\n"
            f"FOB Price: ${data['fob']}/ton\n"
            "-------------------\n"
            f"Revenue: ${revenue:,.0f}\n"
            f"Freight: ${freight:,.0f}\n"
            f"Port costs: ${port:,.0f}\n"
            f"Transport: ${transport:,.0f}\n"
            f"Total Cost: ${total_cost:,.0f}\n"
            "-------------------\n"
            f"Net Profit: ${profit:,.0f}\n"
        )
        del user_data[user_id]

