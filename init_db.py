#!/usr/bin/env python3
"""
Database Initialization Script
Creates all necessary tables for the AI Dropshipping ERP System
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

# ============================================================================
# CRITICAL: Use absolute path for DB (same as app.py)
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'dropship.db')

print(f"[INIT_DB] ========================================")
print(f"[INIT_DB] Script: {__file__}")
print(f"[INIT_DB] Base directory: {BASE_DIR}")
print(f"[INIT_DB] Database path (ABSOLUTE): {DB_PATH}")
print(f"[INIT_DB] Database exists: {os.path.exists(DB_PATH)}")
print(f"[INIT_DB] ========================================")

# Verify DB path is absolute
if not os.path.isabs(DB_PATH):
    raise RuntimeError(f"CRITICAL: DB_PATH must be absolute! Got: {DB_PATH}")

def init_database():
    """Initialize SQLite database with all required tables"""
    
    # Remove existing database if present
    if os.path.exists(DB_PATH):
        print(f"Removing existing database: {DB_PATH}")
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Admin Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # System Configuration Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sourced Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sourced_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT NOT NULL,
            title_cn TEXT,
            title_kr TEXT,
            description_cn TEXT,
            description_kr TEXT,
            marketing_copy TEXT,
            price_cny REAL,
            price_krw INTEGER,
            profit_margin REAL,
            estimated_profit INTEGER,
            traffic_score INTEGER,
            safety_status TEXT,
            images_json TEXT,
            processed_images_json TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            registered_at TIMESTAMP
        )
    ''')
    
    # Marketplace Listings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marketplace_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            marketplace TEXT NOT NULL,
            external_product_id TEXT,
            listing_url TEXT,
            current_stock INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES sourced_products (id)
        )
    ''')
    
    # Orders Table (with PCCC and exchange rate)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            marketplace TEXT NOT NULL,
            product_id INTEGER,
            customer_name TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            pccc TEXT NOT NULL,
            pccc_validated BOOLEAN DEFAULT 0,
            quantity INTEGER DEFAULT 1,
            sale_price INTEGER NOT NULL,
            purchase_price_cny REAL,
            purchase_price_krw INTEGER,
            applied_exchange_rate REAL NOT NULL,
            shipping_cost INTEGER,
            customs_tax INTEGER,
            marketplace_fee INTEGER,
            net_profit INTEGER,
            original_product_url TEXT,
            tracking_number TEXT,
            order_status TEXT DEFAULT 'pending',
            payment_status TEXT DEFAULT 'paid',
            shipping_deadline TIMESTAMP,
            ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            shipped_at TIMESTAMP,
            delivered_at TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES sourced_products (id)
        )
    ''')
    
    # Stock Monitor Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_monitor_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            original_url TEXT,
            check_status TEXT,
            action_taken TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES sourced_products (id)
        )
    ''')
    
    # Activity Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            description TEXT,
            status TEXT,
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tax Records Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            order_number TEXT,
            sale_date DATE,
            sale_amount INTEGER,
            purchase_amount INTEGER,
            shipping_cost INTEGER,
            marketplace_fee INTEGER,
            net_profit INTEGER,
            applied_exchange_rate REAL,
            exported BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')
    
    # Insert default admin user
    default_password = 'admin123'
    password_hash = generate_password_hash(default_password, method='pbkdf2:sha256')
    cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                   ('admin', password_hash))
    
    # Insert default configuration
    default_configs = [
        ('target_margin_rate', '30'),
        ('cny_exchange_rate', '190'),
        ('exchange_rate_buffer', '1.05'),
        ('shipping_cost_base', '5000'),
        ('customs_tax_rate', '0.10'),
        ('naver_fee_rate', '0.06'),
        ('coupang_fee_rate', '0.11'),
        ('auto_register', 'false'),
        ('scrapingant_api_key', ''),
        ('openai_api_key', ''),
        ('naver_client_id', ''),
        ('naver_client_secret', ''),
        ('coupang_access_key', ''),
        ('coupang_secret_key', ''),
        ('server_static_ip', ''),
        ('debug_mode_ignore_filters', 'false'),  # NEW: Debug mode for diagnostics
    ]
    
    cursor.executemany('INSERT INTO config (key, value) VALUES (?, ?)', default_configs)
    
    conn.commit()
    conn.close()
    
    print("✅ Database initialized successfully!")
    print(f"📁 Database file: {DB_PATH}")
    print(f"👤 Default admin credentials:")
    print(f"   Username: admin")
    print(f"   Password: {default_password}")
    print(f"\n⚠️  Please change the default password after first login!")

if __name__ == '__main__':
    init_database()
