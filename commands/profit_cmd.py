from services.profit import calculate_profit

def profit_command(tonnage):
    data = calculate_profit(tonnage)

    return f"""
🧮 Profit Calculation
━━━━━━━━━━━━━━━
Tonnage: {tonnage} tons
Price (Fe65%): ${data['price']}/ton
Revenue: ${data['revenue']:,}
Freight Cost: ${data['cost']:,}
Net Profit: ${data['profit']:,}
━━━━━━━━━━━━━━━
"""
