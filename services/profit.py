from services.iron import get_fe65

def calculate_profit(tonnage):
    price = get_fe65()
    freight = 25

    revenue = price * tonnage
    cost = freight * tonnage
    profit = revenue - cost

    return {
        "price": price,
        "revenue": revenue,
        "cost": cost,
        "profit": profit
    }

