import requests
import re
from bs4 import BeautifulSoup

def get_iran_billet_price():
    """دریافت قیمت شمش از آهن ملل"""
    try:
        url = "https://ahanmelal.com/steel-ingots/steel-ingot-price"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for sel in ['.product-price', '.price', '.current-price']:
                elem = soup.select_one(sel)
                if elem:
                    txt = elem.get_text(strip=True)
                    nums = re.findall(r'(\d{1,3}(?:,\d{3})*)', txt)
                    if nums:
                        return int(nums[0].replace(',', ''))
    except Exception as e:
        print(f"Error: {e}")
    return None

def get_iran_rebar_price():
    """دریافت قیمت میلگرد از آهن ملل"""
    try:
        url = "https://ahanmelal.com/steel-products/rebar-price"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for sel in ['.product-price', '.price', '.current-price']:
                elem = soup.select_one(sel)
                if elem:
                    txt = elem.get_text(strip=True)
                    nums = re.findall(r'(\d{1,3}(?:,\d{3})*)', txt)
                    if nums:
                        return int(nums[0].replace(',', ''))
    except:
        pass
    return None
