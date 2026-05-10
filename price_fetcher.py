import aiohttp
import asyncio
import logging
import re
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)

# ========== کش قیمت ایران ==========
iran_prices_cache = {"data": None, "last_update": None}

# ========== نرخ ارز ==========
async def get_usd_nego_rate_toman() -> int:
    """نرخ دلار مبادله‌ای (نیمایی) – تومان"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.tgju.org/sana/", timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*ریال', html)
                    if match:
                        return int(match.group(1).replace(',', '')) // 10
    except Exception as e:
        logger.error(f"Error fetching nego rate: {e}")
    return 146800

async def get_usd_free_rate_toman() -> int:
    """نرخ دلار بازار آزاد – تومان"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.nobitex.ir/v2/trades", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = float(data.get("stats", {}).get("USDT-IRT", {}).get("latest", 0))
                    if price > 0:
                        return int(price) // 10
    except:
        pass
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.tgju.org/v1/price/price_dollar_rl", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price_str = data.get("price", "0").replace(",", "")
                    price = int(price_str)
                    if price > 0:
                        return price // 10
    except:
        pass
    return 178000

# ========== آهن‌ملل (قیمت بازار آزاد) ==========
async def fetch_ahanmelal_price(product_key: str):
    urls = {
        "billet": "https://ahanmelal.com/steel-ingots/steel-ingot-price",
        "rebar": "https://ahanmelal.com/steel-products/rebar-price",
        "ibeam": "https://ahanmelal.com/steel-products/ibeam-price",
        "dri": "https://ahanmelal.com/sponge-iron/sponge-iron-price"
    }
    if product_key not in urls:
        return None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(urls[product_key], headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    selectors = ['.product-price', '.price', '.current-price', '.price-value']
                    for sel in selectors:
                        elem = soup.select_one(sel)
                        if elem:
                            txt = elem.get_text(strip=True)
                            nums = re.findall(r'(\d{1,3}(?:,\d{3})*)', txt)
                            if nums:
                                raw = nums[0].replace(',', '')
                                if raw.isdigit():
                                    return int(raw)
    except Exception as e:
        logger.error(f"Scrape {product_key} error: {e}")
    return None

# ========== بورس کالا (IME) ==========
async def scrape_ime_prices() -> dict:
    """دریافت قیمت پایه محصولات از بورس کالای ایران"""
    url = "https://www.ime.co.ir/Product/Index"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    result = {"concentrate": None, "pellet": None, "billet": None, "rebar": None}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    # جستجوی جدول قیمت‌ها (ممکن است کلاس متفاوت باشد)
                    table = soup.find('table', class_='table') or soup.find('table', class_='table-striped')
                    if not table:
                        logger.warning("جدول قیمت در بورس کالا یافت نشد")
                        return result
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 6:
                            name = cells[1].get_text(strip=True)
                            price_text = cells[5].get_text(strip=True).replace(',', '')
                            if not price_text.isdigit():
                                continue
                            price = int(price_text)
                            if "کنسانتره" in name or "Concentrate" in name:
                                result["concentrate"] = price
                            elif "گندله" in name or "Pellet" in name:
                                result["pellet"] = price
                            elif "شمش" in name or "Billet" in name or "Slab" in name:
                                result["billet"] = price
                            elif "میلگرد" in name or "Rebar" in name:
                                result["rebar"] = price
    except Exception as e:
        logger.error(f"IME scrape error: {e}")
    return result

# ========== جمع‌آوری همه قیمت‌های ایران ==========
async def get_iran_prices():
    global iran_prices_cache
    now = datetime.now()
    if iran_prices_cache["data"] and iran_prices_cache["last_update"]:
        if (now - iran_prices_cache["last_update"]).total_seconds() < 21600:  # 6 ساعت
            return iran_prices_cache["data"]

    logger.info("Fetching Iran prices...")
    # دریافت از آهن‌ملل (بازار آزاد)
    billet = await fetch_ahanmelal_price("billet") or 55000
    rebar = await fetch_ahanmelal_price("rebar") or 65000
    ibeam = await fetch_ahanmelal_price("ibeam") or 62000
    dri = await fetch_ahanmelal_price("dri") or 15500

    # دریافت از بورس کالا (قیمت پایه)
    ime = await scrape_ime_prices()

    # ساخت دیکشنری نهایی
    prices = {
        "concentrate": {
            "name": "کنسانتره سنگ آهن",
            "ice": f"{ime['concentrate']:,}" if ime['concentrate'] else "۴,۲۰۰,۰۰۰ - ۴,۸۰۰,۰۰۰",
            "free_market": "۵,۴۰۰,۰۰۰ - ۵,۸۰۰,۰۰۰",
            "factory": "گل گهر: ۴,۳۰۰,۰۰۰ | مرکزی: ۴,۶۰۰,۰۰۰",
            "unit": "تن"
        },
        "pellet": {
            "name": "گندله",
            "ice": f"{ime['pellet']:,}" if ime['pellet'] else "۶,۲۰۰,۰۰۰ - ۶,۸۰۰,۰۰۰",
            "free_market": "۶,۸۰۰,۰۰۰ - ۷,۵۰۰,۰۰۰",
            "factory": "گل گهر: ۶,۴۰۰,۰۰۰ | چادرملو: ۶,۳۰۰,۰۰۰",
            "unit": "تن"
        },
        "dri": {
            "name": "آهن اسفنجی",
            "ice": f"{int(dri*0.95):,} - {int(dri*1.02):,}",
            "free_market": f"{int(dri*0.98):,} - {int(dri*1.05):,}",
            "factory": f"میانگین: {int(dri):,}",
            "unit": "کیلو"
        },
        "billet": {
            "name": "شمش فولادی",
            "ice": f"{ime['billet']:,}" if ime['billet'] else f"{int(billet*0.95):,} - {int(billet*1.02):,}",
            "free_market": f"{int(billet*0.98):,} - {int(billet*1.05):,}",
            "factory": f"اصفهان: {billet:,} | یزد: {billet-500:,} | قزوین: {billet-1500:,}",
            "unit": "کیلو"
        },
        "rebar": {
            "name": "میلگرد",
            "ice": f"{ime['rebar']:,}" if ime['rebar'] else f"{int(rebar*0.95):,} - {int(rebar*1.02):,}",
            "free_market": f"{int(rebar*0.98):,} - {int(rebar*1.05):,}",
            "factory": f"ذوب آهن: {rebar:,} | امیرکبیر: {rebar+1000:,}",
            "unit": "کیلو"
        },
        "ibeam": {
            "name": "تیرآهن",
            "ice": f"{int(ibeam*0.95):,} - {int(ibeam*1.02):,}",
            "free_market": f"{int(ibeam*0.98):,} - {int(ibeam*1.05):,}",
            "factory": f"ذوب آهن: {ibeam:,}",
            "unit": "کیلو"
        }
    }

    iran_prices_cache["data"] = prices
    iran_prices_cache["last_update"] = now
    return prices
