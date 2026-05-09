async def fetch_global_prices(price_arbiter: PriceArbiter) -> dict:
    """
    دریافت قیمت‌های جهانی سنگ آهن از چند منبع و اعتبارسنجی با PriceArbiter
    Returns:
        dict: شامل قیمت نهایی CFR Qingdao (دلار/تن) و Billet FOB China (دلار/تن)
    """
    sources_iron = {}
    sources_billet = {}

    # منبع 1: وب‌اسکرپینگ از سایت Mysteel Index (پایدارترین شاخص)
    try:
        # توجه: URL دقیق صفحه شاخص باید با بررسی واقعی سایت Mysteel به‌روز شود
        url = "https://tks.mysteel.com/price/list-iron-ore-index.html"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    # این سلکتور با بررسی واقعی صفحه Mysteel تعیین می‌شود
                    price_elem = soup.select_one('.index-price .price-value')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        prices = re.findall(r'(\d+\.?\d*)', price_text)
                        if prices and len(prices) > 0:
                            price = float(prices[0])
                            if 80 < price < 150:  # اعتبارسنجی محدوده منطقی
                                sources_iron["mysteel_index"] = price
    except Exception as e:
        logger.error(f"Mysteel Index scrape error: {e}")

    # منبع 2: وب‌اسکرپینگ از SMM (Shanghai Metals Market) - پشتیبان
    try:
        url = "https://www.metal.com/news/price/iron-ore"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    price_elem = soup.select_one('.current-price')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        numbers = re.findall(r'(\d+\.?\d*)', price_text)
                        if numbers:
                            price = float(numbers[0])
                            if 80 < price < 150:
                                sources_iron["smm_index"] = price
    except Exception as e:
        logger.error(f"SMM scrape error: {e}")

    # منبع 3: API جایگزین (در صورت وجود کلید)
    api_key = os.environ.get("METALS_API_KEY")
    if api_key:
        try:
            url = f"https://api.metals-api.com/v1/latest?access_key={api_key}&base=USD&symbols=IRON62"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            price = data["rates"].get("IRON62")
                            if price and 80 < price < 150:
                                sources_iron["metals_api"] = price
        except Exception as e:
            logger.error(f"Metals-API error: {e}")

    # اعتبارسنجی قیمت سنگ آهن با PriceArbiter
    result_iron = price_arbiter.resolve_price(sources_iron, default=108.0)

    # دریافت قیمت بیلت (FOB China)
    try:
        url = "https://www.mysteel.net/daily-prices/7009318-billet-export-prices-fob-china"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    price_rows = soup.select('table tr')
                    for row in price_rows:
                        cells = row.find_all('td')
                        if len(cells) >= 6 and '3SP' in cells[1].get_text(strict=False, separator=' '):
                            price_text = cells[6].get_text(strict=False, separator=' ')
                            numbers = re.findall(r'(\d+\.?\d*)', price_text)
                            if numbers and 400 < float(numbers[0]) < 600:
                                sources_billet["mysteel_export"] = float(numbers[0])
                                break
    except Exception as e:
        logger.error(f"Billet FOB scrape error: {e}")

    result_billet = price_arbiter.resolve_price(sources_billet, default=480.0)

    return {
        "iron_ore": {
            "price": result_iron["price"],
            "unit": "USD/ton",
            "method": result_iron["method"],
            "source_details": result_iron["details"]
        },
        "billet": {
            "price": result_billet["price"],
            "unit": "USD/ton FOB China",
            "method": result_billet["method"],
            "source_details": result_billet["details"]
        }
    }
