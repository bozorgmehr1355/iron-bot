import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "data.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product TEXT,
        port TEXT,
        condition TEXT,
        target_price REAL,
        created_at TEXT,
        is_active INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        port TEXT,
        price REAL,
        recorded_at TEXT
    )''')
    conn.commit()
    conn.close()
    print("✅ دیتابیس راه‌اندازی شد")

def add_alert(user_id, product, port, condition, target_price):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO alerts (user_id, product, port, condition, target_price, created_at) VALUES (?, ?, ?, ?, ?, ?)',
              (user_id, product, port, condition, target_price, datetime.now().isoformat()))
    conn.commit()
    alert_id = c.lastrowid
    conn.close()
    return alert_id

def get_active_alerts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, user_id, product, port, condition, target_price FROM alerts WHERE is_active = 1')
    alerts = c.fetchall()
    conn.close()
    return alerts

def deactivate_alert(alert_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE alerts SET is_active = 0 WHERE id = ?', (alert_id,))
    conn.commit()
    conn.close()

def save_price(product, port, price):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO price_history (product, port, price, recorded_at) VALUES (?, ?, ?, ?)',
              (product, port, price, datetime.now().isoformat()))
    conn.commit()
    conn.close()
