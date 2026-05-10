import requests
import re

def get_usd_rial_rate():
    """دریافت نرخ دلار بازار آزاد از TGJU"""
    try:
        r = requests.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5)
        if r.status_code == 200:
            data = r.json()
            price_str = data.get("price", "0").replace(",", "")
            return int(price_str)
    except:
        pass
    return 1780000

def get_usd_toman_rate():
    """دریافت نرخ دلار به تومان"""
    rial = get_usd_rial_rate()
    return rial // 10
