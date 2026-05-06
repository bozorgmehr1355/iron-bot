import requests

def get_usd_free():
    try:
        url = "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl"
        r = requests.get(url, timeout=10)
        data = r.json()
        price = data["data"][0][1]
        return price
    except:
        return None

def get_eur_usd():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        r = requests.get(url, timeout=10)
        data = r.json()
        return round(data["rates"]["EUR"], 4)
    except:
        return None

def get_aed_usd():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        r = requests.get(url, timeout=10)
        data = r.json()
        return round(data["rates"]["AED"], 4)
    except:
        return None

