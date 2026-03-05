#!/usr/bin/env python3
"""
Blue Ocean Cache 테이블 마이그레이션 스크립트
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'dropship.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print('[Migration] Creating blue_ocean_cache table...')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS blue_ocean_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL,
        blue_ocean_score REAL NOT NULL,
        trend_score REAL,
        competition_score REAL,
        market_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print('✅ Migration complete')

if __name__ == '__main__':
    migrate()
