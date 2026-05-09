import requests
from bs4 import BeautifulSoup
import re

def get_ice_price(product_name: str) -> dict:
    """
    دریافت قیمت یک محصول از وب‌سایت بورس کالای ایران (ice.ir)
    """
    # آدرس صفحه جستجوی محصولات (باید دقیقاً بررسی شود)
    url = f"https://www.ice.ir/Product/Index?name={product_name}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # پیدا کردن جدول قیمت‌ها (این سلکتور موقتی است و باید با بررسی صفحه دقیق شود)
        price_table = soup.find('table', class_='table table-striped')
        if not price_table:
            return None
        
        rows = price_table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                if product_name.lower() in cells[0].text.lower():
                    price_text = cells[1].text.strip()
                    # استخراج عدد (مثلاً 158,000)
                    match = re.search(r'([\d,]+)', price_text)
                    if match:
                        price = int(match.group(1).replace(',', ''))
                        return {
                            "product": product_name,
                            "price": price,
                            "unit": "ریال/کیلو",
                            "date": datetime.now().strftime("%Y/%m/%d"),
                            "source": "ICE"
                        }
        return None
    except Exception as e:
        print(f"ICE Scraper error: {e}")
        return None
