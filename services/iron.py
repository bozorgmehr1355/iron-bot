import requests
from config import FRED_API_KEY

def get_iron_62():
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=PIORECRUSDM&api_key={FRED_API_KEY}&sort_order=desc&limit=1&file_type=json"
        r = requests.get(url, timeout=10)
        data = r.json()
        price = data["observations"][0]["value"]
        return round(float(price), 2)
    except:
        return 107.58

def get_fe65():
    base = get_iron_62()
    premium = 12
    return round(base + premium, 2)
