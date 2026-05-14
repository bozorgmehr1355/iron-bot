
def update_all_prices():
    current = load_json(PRICE_FILE, {
        "concentrate": 4800000, "pellet": 6500000,
        "dri": 14166, "billet": 42500, "rebar": 58000
    })
    
    print("🔄 شروع بروزرسانی قیمت‌های داخلی...")

    rebar = scrape_rebar()
    billet = scrape_billet()
    dri = scrape_dri()

    if rebar:
        current["rebar"] = rebar
    if billet:
        current["billet"] = billet
    if dri:
        current["dri"] = dri

    current["last_update"] = datetime.now().isoformat()
    save_json(PRICE_FILE, current)
    
    print(f"✅ بروزرسانی داخلی تمام شد | میلگرد={rebar or 'بدون تغییر'}")
