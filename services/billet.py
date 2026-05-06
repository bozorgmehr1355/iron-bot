import requests

def get_billet_price():
    try:
        url = "https://api.tgju.org/v1/market/indicator/summary-table-data/steel-billet-export"
        r = requests.get(url, timeout=10)
        data = r.json()
        price = data["data"][0][1]
        return price
    except:
        return 510
