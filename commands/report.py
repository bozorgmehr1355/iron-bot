from services.iron import get_iron_62, get_fe65
from services.billet import get_billet_price
from services.forex import get_usd_free, get_eur_usd, get_aed_usd

def get_report():
    iron62 = get_iron_62()
    fe65 = get_fe65()
    billet = get_billet_price()
    usd = get_usd_free()
    eur = get_eur_usd()
    aed = get_aed_usd()

    text = f"""
📊 Market Report
━━━━━━━━━━━━━━━
💵 USD (Free Market): {usd} Rials
💶 USD/EUR: {eur}
🇦🇪 USD/AED: {aed}
━━━━━━━━━━━━━━━
⛏️ Iron Ore 62%: ${iron62}/ton
⛏️ Fe 65%: ${fe65}/ton
🔩 Billet: ${billet}/ton
━━━━━━━━━━━━━━━
"""
    return text
