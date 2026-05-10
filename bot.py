import requests
import re
from bs4 import BeautifulSoup

def get_iran_billet_price():
    """دریافت قیمت شمش از آهن ملل (تومان/تن)"""
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
    except:
        pass
    return None

def get_iran_rebar_price():
    """دریافت قیمت میلگرد از آهن ملل (تومان/کیلو)"""
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

def get_iran_dri_price():
    """دریافت قیمت آهن اسفنجی (تومان/تن) - داده ثابت موقت"""
    try:
        url = "https://ahanmelal.com/sponge-iron/sponge-iron-price"
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
    return 15500  # fallback

def get_iran_concentrate_price():
    """دریافت قیمت کنسانتره - داده ثابت موقت"""
    return 4800000

def get_iran_pellet_price():
    """دریافت قیمت گندله - داده ثابت موقت"""
    return 6800000
