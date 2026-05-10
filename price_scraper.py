import requests
import re
import json
import time
import threading
from datetime import datetime

DATA_FILE = "prices.json"

# ========== دریافت قیمت از منابع ==========
def get_ahanmelal_price(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            # جستجوی ساده برای اعداد
            numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', r.text)
            if numbers:
                return int(numbers[0].replace(',', ''))
    except:
        pass
    return None

# ========== بروزرسانی همه قیمت‌ها ==========
def update_all_prices():
    print(f"[{datetime.now()}] بروزرسانی قیمت‌ها...")
    
    # قیمت‌های پیش‌فرض
    prices = {
        "ice_concentrate": "۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰",
        "ice_pellet": "۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰",
        "ice_dri": "۱۴,۸۰۰ - ۱۵,۵۰۰",
        "ice_billet": "۴۱,۰۰۰ - ۴۴,۰۰۰",
        "ice_rebar": "۵۰,۰۰۰ - ۶۵,۰۰۰",
        "free_concentrate": "۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰",
        "free_pellet": "۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰",
        "free_dri": "۱۶,۰۰۰ - ۱۶,۸۰۰",
        "free_billet": "۵۴,۰۰۰ - ۵۷,۰۰۰",
        "free_rebar": "۶۳,۰۰۰ - ۶۸,۰۰۰",
        "factory_billet": "اصفهان: ۴۳,۰۹۱ | یزد: ۴۳,۰۰۰ | قزوین: ۴۰,۴۰۹",
        "factory_rebar": "ذوب آهن: ۶۵,۰۰۰ | امیرکبیر: ۶۶,۰۰۰",
        "factory_dri": "میانه: ۱۶,۸۰۰ | نطنز: ۱۶,۵۰۰",
        "factory_pellet": "گل گهر: ۶,۴۰۰,۰۰۰ | چادرملو: ۶,۳۰۰,۰۰۰",
        "factory_concentrate": "گل گهر: ۴,۳۰۰,۰۰۰ | مرکزی: ۴,۶۰۰,۰۰۰",
        "last_update": datetime.now().isoformat()
    }
    
    # تلاش برای دریافت قیمت شمش از آهن ملل
    billet_price = get_ahanmelal_price("https://ahanmelal.com/steel-ingots/steel-ingot-price")
    if billet_price:
        prices["free_billet"] = f"{billet_price-2000:,} - {billet_price+2000:,}"
        prices["factory_billet"] = f"اصفهان: {billet_price} | یزد: {billet_price-100} | قزوین: {billet_price-3000}"
    
    # ذخیره در فایل
    with open(DATA_FILE, 'w') as f:
        json.dump(prices, f)
    
    print(f"[{datetime.now()}] بروزرسانی کامل شد")
    return prices

def start_price_updater():
    update_all_prices()
    def loop():
        while True:
            time.sleep(6 * 60 * 60)  # هر 6 ساعت
            update_all_prices()
    threading.Thread(target=loop, daemon=True).start()
