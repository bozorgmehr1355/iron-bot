import json
import time
import threading
import requests
import re
from datetime import datetime

# فایل ذخیره قیمت‌ها
DATA_FILE = "prices.json"

def get_usd_free():
    try:
        r = requests.get("https://api.nobitex.ir/v2/trades", timeout=5)
        if r.status_code == 200:
            return int(r.json()["stats"]["USDT-IRT"]["latest"]) // 10
    except:
        pass
    return 178000

def get_usd_secondary():
    try:
        r = requests.get("https://www.tgju.org/sana/", timeout=5)
        match = re.search(r'(\d{1,3}(?:,\d{3})*)', r.text)
        if match:
            return int(match.group(1).replace(',', '')) // 10
    except:
        pass
    return 28500

def load_prices():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            "usd_free": 178000,
            "usd_secondary": 28500,
            "last_update": None
        }

def save_prices(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def update_exchange_rates():
    """بروزرسانی نرخ ارز (هر 15 دقیقه)"""
    data = load_prices()
    data["usd_free"] = get_usd_free()
    data["usd_secondary"] = get_usd_secondary()
    data["last_update"] = datetime.now().isoformat()
    save_prices(data)
    print(f"[{datetime.now()}] نرخ ارز بروز شد: آزاد={data['usd_free']}, مبادله‌ای={data['usd_secondary']}")

def start_updater():
    """اجرای بروزرسانی خودکار در پس‌زمینه"""
    # بروزرسانی اولیه
    update_exchange_rates()
    
    # هر 15 دقیقه نرخ ارز
    def rate_loop():
        while True:
            time.sleep(15 * 60)
            update_exchange_rates()
    
    thread = threading.Thread(target=rate_loop, daemon=True)
    thread.start()
