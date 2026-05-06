user_data = {}

async def profit_start(update, context):
    user_id = update.message.from_user.id
    user_data[user_id] = {}
    await update.message.reply_text("Step 1/5: Tonnage (tons)?\nExample: 5000")

async def profit_step(update, context):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_data:
        await update.message.reply_text("Send /profit to start")
        return

    data = user_data[user_id]

    if "tonnage" not in data:
        data["tonnage"] = float(text)
        await update.message.reply_text("Step 2/5: FOB Price ($/ton)?\nExample: 119.58")

    elif "fob" not in data:
        data["fob"] = float(text)
        await update.message.reply_text("Step 3/5: Freight cost ($/ton)?\nExample: 18")

    elif "freight" not in data:
        data["freight"] = float(text)
        await update.message.reply_text("Step 4/5: Port & loading cost ($/ton)?\nExample: 4")

    elif "port" not in data:
        data["port"] = float(text)
        await update.message.reply_text("Step 5/5: Inland transport ($/ton)?\nExample: 3")

    elif "transport" not in data:
        data["transport"] = float(text)

        t = data["tonnage"]
        revenue = data["fob"]  t
        freight = data["freight"]  t
        port = data["port"]  t
        transport = data["transport"]  t
        total_cost = freight + port + transport
        profit = revenue - total_cost

        await update.message.reply_text(f"""
🧮 Profit Calculation
━━━━━━━━━━━━━━━
Tonnage: {t:,.0f} tons
FOB Price: ${data['fob']}/ton
━━━━━━━━━━━━━━━
Revenue: ${revenue:,.0f}
Freight: ${freight:,.0f}
Port costs: ${port:,.0f}
Transport: ${transport:,.0f}
Total Cost: ${total_cost:,.0f}
━━━━━━━━━━━━━━━
Net Profit: ${profit:,.0f}
━━━━━━━━━━━━━━━
""")
        del user_data[user_id]

