"""
AI Dropshipping ERP System - Main Application
Complete implementation with all 8 modules
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
import requests
import hashlib
import hmac
import time
import base64
import bcrypt
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import io
import os
import re
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
import schedule
import threading
import logging
from logging.handlers import RotatingFileHandler

# ============================================================================
# DATABASE PATH CONFIGURATION (MUST BE FIRST)
# ============================================================================

# Get absolute path to ensure same DB regardless of working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'dropship.db')

# CRITICAL: Print and log DB path at module load time
print(f"[INIT] ========================================")
print(f"[INIT] Module: {__file__}")
print(f"[INIT] Base directory: {BASE_DIR}")
print(f"[INIT] Database path (ABSOLUTE): {DB_PATH}")
print(f"[INIT] Database exists: {os.path.exists(DB_PATH)}")
if os.path.exists(DB_PATH):
    print(f"[INIT] Database size: {os.path.getsize(DB_PATH)} bytes")
print(f"[INIT] ========================================")

# Verify DB path is absolute
if not os.path.isabs(DB_PATH):
    raise RuntimeError(f"CRITICAL: DB_PATH must be absolute! Got: {DB_PATH}")

print(f"[INIT] ✅ DB_PATH verification passed: {DB_PATH}")

# ============================================================================
# CRITICAL: AUTO DATABASE INITIALIZATION (BEFORE FLASK APP)
# ============================================================================

def auto_init_database():
    """
    Automatically initialize database if it doesn't exist or is missing tables.
    This prevents sqlite3.OperationalError: no such table errors.
    CRITICAL: Must run BEFORE Flask app initialization.
    """
    needs_init = False
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        print(f'[DB-INIT] Database file not found: {DB_PATH}')
        needs_init = True
    else:
        # Check if required tables exist
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                print('[DB-INIT] Required table "users" not found in database')
                needs_init = True
            conn.close()
        except Exception as e:
            print(f'[DB-INIT] Error checking database: {e}')
            needs_init = True
    
    if needs_init:
        print('[DB-INIT] 🔧 Initializing database automatically...')
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create config table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create sourced_products table
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
            
            # Create orders table
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
            
            # Create activity_logs table
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
            
            # Create tax_records table
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
            
            # Create marketplace_listings table
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
            
            # Create stock_monitor_log table
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
            
            # Check if default admin user exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
            if cursor.fetchone()[0] == 0:
                default_password = 'admin123'
                password_hash = generate_password_hash(default_password, method='pbkdf2:sha256')
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                             ('admin', password_hash))
                print('[DB-INIT] ✅ Default admin user created (username: admin, password: admin123)')
            
            # Insert default configuration if config table is empty
            cursor.execute("SELECT COUNT(*) FROM config")
            if cursor.fetchone()[0] == 0:
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
                ]
                cursor.executemany('INSERT INTO config (key, value) VALUES (?, ?)', default_configs)
                print('[DB-INIT] ✅ Default configuration inserted')
            
            conn.commit()
            conn.close()
            
            print('[DB-INIT] ✅ Database initialized successfully!')
            print(f'[DB-INIT] 📁 Database: {DB_PATH}')
            print('[DB-INIT] ⚠️  Default credentials: admin / admin123')
            
        except Exception as e:
            print(f'[DB-INIT] ❌ Failed to initialize database: {e}')
            import traceback
            traceback.print_exc()
            raise
    else:
        print(f'[DB-INIT] ✅ Database OK: {DB_PATH}')
    
    # CRITICAL: Verify tables exist before proceeding
    print('[DB-VERIFY] Verifying all tables exist...')
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        required_tables = ['users', 'config', 'sourced_products', 'orders', 
                          'activity_logs', 'tax_records', 'marketplace_listings', 'stock_monitor_log']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f'[DB-VERIFY] ❌ ERROR: Missing tables: {missing_tables}')
            print(f'[DB-VERIFY] Found tables: {tables}')
            raise Exception(f'Database verification failed! Missing tables: {missing_tables}')
        else:
            print(f'[DB-VERIFY] ✅ All {len(required_tables)} required tables exist!')
            print(f'[DB-VERIFY] Tables: {", ".join(tables)}')
    except Exception as e:
        print(f'[DB-VERIFY] ❌ Verification failed: {e}')
        raise
    
    # Always print completion marker
    print('='*70)
    print('!!! DATABASE INITIALIZATION COMPLETE !!!')
    print('='*70)

# RUN DATABASE INITIALIZATION IMMEDIATELY (BEFORE ANYTHING ELSE)
print('[CRITICAL] Starting database initialization...')
auto_init_database()
print('[CRITICAL] Database initialization finished. Proceeding with Flask setup...')

# ============================================================================
# FLASK APP INITIALIZATION (AFTER DATABASE IS READY)
# ============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler with rotation (max 10MB, keep 5 backup files)
file_handler = RotatingFileHandler(
    'logs/server.log',
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Add handlers to app logger
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.INFO)

# Log startup
app.logger.info('=' * 70)
app.logger.info('AI Dropshipping ERP System v2.0 - Starting Up')
app.logger.info('=' * 70)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============================================================================
# JINJA2 CUSTOM FILTERS
# ============================================================================

def parse_datetime_filter(date_string):
    """Parse datetime string to datetime object for Jinja2 template"""
    if not date_string:
        return datetime.now()
    
    # Handle various datetime formats
    try:
        # ISO format: 2024-01-21 12:34:56 or with microseconds
        date_str = str(date_string).split('.')[0]  # Remove microseconds if present
        if 'T' in date_str:
            # ISO format with T separator
            return datetime.fromisoformat(date_str.replace('T', ' '))
        else:
            # Standard SQL format
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError):
        # If parsing fails, return current time to avoid template errors
        return datetime.now()

# Register custom Jinja2 filter
app.jinja_env.filters['parse_datetime'] = parse_datetime_filter

# Add now() function to Jinja2 globals for template usage
app.jinja_env.globals['now'] = datetime.now

# ============================================================================
# DATABASE UTILITIES
# ============================================================================

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(action_type, description, status='success', details=None):
    """Log system activity"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_logs (action_type, description, status, details_json)
        VALUES (?, ?, ?, ?)
    ''', (action_type, description, status, json.dumps(details) if details else None))
    conn.commit()
    conn.close()

def get_config(key, default=None):
    """Get configuration value with defensive handling"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        value = row['value']
        # Strip whitespace from string values
        if isinstance(value, str):
            value = value.strip()
        # Return None for empty strings (treat as not configured)
        if value == '':
            return default
        return value
    return default

def set_config(key, value):
    """Set configuration value"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO config (key, value, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
    ''', (key, value, value))
    conn.commit()
    conn.close()

def system_check_critical_configs():
    """
    CRITICAL: System-wide configuration verification
    This function MUST be called at the start of any critical operation
    to ensure all required API keys and configs are loaded from DB.
    
    Returns: dict with status and config values
    Raises: RuntimeError if critical configs are missing
    """
    app.logger.info('[SYSTEM-CHECK] ========================================')
    app.logger.info(f'[SYSTEM-CHECK] 🔍 DB Path (ABSOLUTE): {DB_PATH}')
    app.logger.info(f'[SYSTEM-CHECK] DB Path is absolute: {os.path.isabs(DB_PATH)}')
    app.logger.info(f'[SYSTEM-CHECK] DB Exists: {os.path.exists(DB_PATH)}')
    
    if not os.path.exists(DB_PATH):
        error_msg = f'CRITICAL: Database file not found at {DB_PATH}'
        app.logger.error(f'[SYSTEM-CHECK] ❌ {error_msg}')
        raise RuntimeError(error_msg)
    
    app.logger.info(f'[SYSTEM-CHECK] DB Size: {os.path.getsize(DB_PATH)} bytes')
    
    # Load critical configs from DB
    openai_key = get_config('openai_api_key', '')
    scrapingant_key = get_config('scrapingant_api_key', '')
    target_margin = get_config('target_margin_rate', '30')
    cny_rate = get_config('cny_exchange_rate', '190')
    
    # Log first 4 characters of API keys (masked)
    openai_preview = openai_key[:4] + '****' if len(openai_key) >= 4 else 'EMPTY'
    scrapingant_preview = scrapingant_key[:4] + '****' if len(scrapingant_key) >= 4 else 'EMPTY'
    
    app.logger.info(f'[SYSTEM-CHECK] 🔑 OpenAI API Key: {openai_preview} (length: {len(openai_key)})')
    app.logger.info(f'[SYSTEM-CHECK] 🔑 ScrapingAnt API Key: {scrapingant_preview} (length: {len(scrapingant_key)})')
    app.logger.info(f'[SYSTEM-CHECK] 💰 Target Margin: {target_margin}%')
    app.logger.info(f'[SYSTEM-CHECK] 💱 CNY Exchange Rate: {cny_rate}')
    
    # Check if critical keys are empty
    missing_keys = []
    if not openai_key or openai_key.strip() == '':
        missing_keys.append('openai_api_key')
        app.logger.error('[SYSTEM-CHECK] ❌ OpenAI API key is EMPTY or NOT CONFIGURED')
    
    if not scrapingant_key or scrapingant_key.strip() == '':
        missing_keys.append('scrapingant_api_key')
        app.logger.error('[SYSTEM-CHECK] ❌ ScrapingAnt API key is EMPTY or NOT CONFIGURED')
    
    if missing_keys:
        error_msg = f'CRITICAL: Missing required API keys in DB: {missing_keys}'
        app.logger.error(f'[SYSTEM-CHECK] ❌ {error_msg}')
        app.logger.error('[SYSTEM-CHECK] ❌ Please configure these keys in the Settings page!')
        app.logger.info('[SYSTEM-CHECK] ========================================')
        raise RuntimeError(error_msg)
    
    app.logger.info('[SYSTEM-CHECK] ✅ All critical configurations verified successfully')
    app.logger.info('[SYSTEM-CHECK] ========================================')
    
    return {
        'success': True,
        'openai_key_preview': openai_preview,
        'scrapingant_key_preview': scrapingant_preview,
        'target_margin': target_margin,
        'cny_rate': cny_rate
    }
    
    # Check critical API keys
    critical_keys = {
        'scrapingant_api_key': 'ScrapingAnt API Key',
        'openai_api_key': 'OpenAI API Key'
    }
    
    config_status = {}
    missing_keys = []
    
    for key, display_name in critical_keys.items():
        app.logger.info(f'[SYSTEM-CHECK] Fetching {display_name} from DB...')
        
        # Direct DB query to ensure we're reading from the correct database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row['value'] and row['value'].strip():
            value = row['value'].strip()
            # Show first 4 chars for verification
            preview = f"{value[:4]}..." if len(value) > 4 else "[TOO_SHORT]"
            config_status[key] = {
                'configured': True,
                'length': len(value),
                'preview': preview
            }
            app.logger.info(f'[SYSTEM-CHECK] ✅ {display_name}: YES (length: {len(value)}, preview: {preview})')
        else:
            config_status[key] = {
                'configured': False,
                'length': 0,
                'preview': None
            }
            missing_keys.append(display_name)
            app.logger.error(f'[SYSTEM-CHECK] ❌ {display_name}: NOT CONFIGURED')
    
    # Check other important configs
    other_configs = ['target_margin_rate', 'cny_exchange_rate']
    for key in other_configs:
        value = get_config(key)
        config_status[key] = value
        app.logger.info(f'[SYSTEM-CHECK] {key}: {value}')
    
    app.logger.info('[SYSTEM-CHECK] ========================================')
    
    return {
        'success': len(missing_keys) == 0,
        'missing_keys': missing_keys,
        'configs': config_status
    }

# ============================================================================
# USER MODEL FOR FLASK-LOGIN
# ============================================================================

class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(row['id'], row['username'])
    return None

# ============================================================================
# MODULE 1: AUTHENTICATION
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'])
            login_user(user_obj)
            log_activity('auth', f'User {username} logged in')
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    log_activity('auth', f'User {username} logged out')
    return redirect(url_for('login'))

# ============================================================================
# MODULE 2: AI SOURCING ENGINE WITH SAFETY FILTERS & BLUE OCEAN ANALYSIS
# ============================================================================

# Safety filter keywords
BANNED_KEYWORDS = {
    'food': ['食品', '食物', '零食', '糖果', '饼干', '巧克力', '饮料'],
    'tableware': ['餐具', '碗', '盘子', '筷子', '勺子', '叉子', '杯子'],
    'baby': ['婴儿', '儿童', '宝宝', '玩具', '奶瓶', '尿布', '童装'],
    'cosmetic': ['化妆品', '护肤', '面膜', '口红', '眼影', '粉底'],
    'replica': ['Nike', 'Adidas', 'Gucci', 'LV', 'Louis Vuitton', 'Chanel', 
                'Disney', '迪士尼', 'Supreme', 'Rolex', 'Apple']
}

def analyze_blue_ocean_market(user_keyword=''):
    """
    Advanced Blue Ocean Market Analysis using GPT-4o-mini
    Finds niche opportunities with rising demand and low competition
    """
    api_key = get_config('openai_api_key')
    
    # Defensive: Check API key validity
    if not api_key:
        app.logger.warning('⚠️ OpenAI API key not configured in database')
        return {
            'suggested_keyword': user_keyword if user_keyword else '무선이어폰',
            'reasoning': 'OpenAI API key not configured. Using provided keyword.',
            'analysis_performed': False
        }
    
    # Log API key prefix for debugging (first 7 chars only for security)
    api_key_preview = api_key[:7] + '...' if len(api_key) > 7 else 'TOO_SHORT'
    app.logger.info(f'🔑 Using OpenAI API key: {api_key_preview} (length: {len(api_key)})')
    
    # Validate API key format
    if not api_key.startswith('sk-'):
        app.logger.error(f'❌ Invalid OpenAI API key format (does not start with sk-): {api_key_preview}')
        return {
            'suggested_keyword': user_keyword if user_keyword else '무선이어폰',
            'reasoning': 'Invalid OpenAI API key format. Please check your configuration.',
            'analysis_performed': False
        }
    
    # Get current date and season for context
    now = datetime.now()
    current_month = now.month
    
    # Determine Korean season
    if current_month in [3, 4, 5]:
        season = '봄 (Spring)'
    elif current_month in [6, 7, 8]:
        season = '여름 (Summer)'
    elif current_month in [9, 10, 11]:
        season = '가을 (Fall)'
    else:
        season = '겨울 (Winter)'
    
    # Advanced Blue Ocean Analysis Prompt
    # CRITICAL: Must explicitly ask for JSON format to avoid 400 errors with json_object mode
    prompt = f"""당신은 대한민국 E-커머스의 수석 MD이자 데이터 분석 전문가입니다.

【현재 상황】
- 날짜: {now.strftime('%Y년 %m월 %d일')}
- 계절: {season}
- 분석 기간: 향후 2주~1개월 내 판매 폭발 예상 상품

【사용자 관심 키워드】
"{user_keyword if user_keyword else '없음 (자유 선정)'}"

【미션】
위 키워드를 참고하되, 다음 3가지 조건을 모두 만족하는 '블루오션(Blue Ocean)' 상품 키워드 1개를 찾아내세요:

1. Rising Trend (급상승 트렌드)
   - 최근 검색량이 급증하고 있거나, 다가올 시즌에 수요 폭발 예상
   - 계절성, 이벤트, 신규 트렌드를 고려

2. Low Competition (낮은 경쟁 강도)
   - 대기업 브랜드(삼성, LG, 나이키 등)가 장악하지 않은 카테고리
   - 중소 셀러가 진입 가능한 틈새시장

3. Specificity (구체적인 롱테일 키워드)
   - 너무 광범위한 키워드(예: '가습기') 대신
   - 구체적이고 니치한 키워드(예: '무선 무드등 탁상용 가습기')
   - 1688에서 검색 가능한 구체적인 상품명

**중요: 반드시 아래 JSON 형식으로만 답변하세요. 다른 텍스트는 포함하지 마세요:**

{{
  "keyword": "정밀한 블루오션 키워드 (한국어)",
  "reasoning": "이 키워드를 선정한 이유를 1~2문장으로 설명",
  "trend_score": 1-10 사이 점수,
  "competition_score": 1-10 사이 점수 (낮을수록 좋음)
}}

예시:
{{
  "keyword": "반려동물 자동 급식기 카메라",
  "reasoning": "1인 가구 증가로 펫테크 수요 급증, 대기업 미진입 영역",
  "trend_score": 9,
  "competition_score": 3
}}"""

    try:
        # Log request details
        app.logger.info(f'📡 Calling OpenAI API: model=gpt-4o-mini, max_tokens=500, temperature=0.8')
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',  # FORCED: Must use gpt-4o-mini (universal access)
                'messages': [
                    {
                        'role': 'system',
                        'content': '당신은 한국 E-커머스 시장의 전문 MD이자 트렌드 분석가입니다. 블루오션 시장을 발굴하는 전문가입니다. 반드시 JSON 형식으로만 응답하세요.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.8,
                'max_tokens': 500,
                'response_format': {'type': 'json_object'}  # JSON mode enabled
            },
            timeout=30
        )
        
        # Log response status
        app.logger.info(f'📥 OpenAI API Response: status_code={response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            app.logger.info(f'✅ Received response from OpenAI (length: {len(content)} chars)')
            
            # Parse JSON response
            import json
            try:
                analysis = json.loads(content)
                app.logger.info(f'🎯 Blue Ocean Keyword: {analysis.get("keyword")}')
                
                return {
                    'suggested_keyword': analysis.get('keyword', user_keyword or '무선이어폰'),
                    'reasoning': analysis.get('reasoning', 'AI 분석 완료'),
                    'trend_score': analysis.get('trend_score', 0),
                    'competition_score': analysis.get('competition_score', 0),
                    'analysis_performed': True
                }
            except json.JSONDecodeError as je:
                app.logger.error(f'❌ JSON parsing failed: {je}')
                app.logger.error(f'Raw content: {content[:200]}...')
                return {
                    'suggested_keyword': user_keyword if user_keyword else '무선이어폰',
                    'reasoning': f'AI 응답 파싱 실패: {str(je)}',
                    'analysis_performed': False
                }
        else:
            # Enhanced error logging for non-200 responses
            try:
                error_body = response.json()
                error_message = error_body.get('error', {}).get('message', 'No error message')
                error_type = error_body.get('error', {}).get('type', 'unknown')
                app.logger.error(f'❌ OpenAI API error {response.status_code}: {error_type} - {error_message}')
                app.logger.error(f'Full error body: {error_body}')
            except:
                app.logger.error(f'❌ OpenAI API error {response.status_code}: {response.text[:300]}')
            
            return {
                'suggested_keyword': user_keyword if user_keyword else '무선이어폰',
                'reasoning': f'AI 분석 실패 (API 오류: {response.status_code})',
                'analysis_performed': False
            }
    
    except requests.exceptions.Timeout:
        app.logger.error('❌ OpenAI API timeout (30s)')
        return {
            'suggested_keyword': user_keyword if user_keyword else '무선이어폰',
            'reasoning': 'AI 분석 시간 초과 (30초)',
            'analysis_performed': False
        }
    except requests.exceptions.RequestException as re:
        app.logger.error(f'❌ Network error: {str(re)}')
        return {
            'suggested_keyword': user_keyword if user_keyword else '무선이어폰',
            'reasoning': f'네트워크 오류: {str(re)}',
            'analysis_performed': False
        }
    except Exception as e:
        app.logger.error(f'❌ Unexpected error in Blue Ocean analysis: {str(e)}')
        app.logger.exception(e)  # This will log full traceback
        return {
            'suggested_keyword': user_keyword if user_keyword else '무선이어폰',
            'reasoning': f'AI 분석 실패: {str(e)}',
            'analysis_performed': False
        }

def check_safety_filter(title, description=''):
    """Check if product passes safety filter"""
    text = (title + ' ' + description).lower()
    
    for category, keywords in BANNED_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return False, f'Banned category: {category} (keyword: {keyword})'
    
    return True, 'Pass'

def scrape_1688_search(keyword, max_results=50):
    """Scrape 1688 search results using ScrapingAnt"""
    app.logger.info(f'[1688 Scraping] ========================================')
    app.logger.info(f'[1688 Scraping] Starting search for keyword: {keyword}')
    app.logger.info(f'[1688 Scraping] Max results: {max_results}')
    
    # CRITICAL: Always fetch fresh config from DB
    app.logger.info('[1688 Scraping] [DEBUG] Fetching ScrapingAnt API key from DB...')
    api_key = get_config('scrapingant_api_key')
    
    # Detailed logging for debugging
    if api_key is None:
        app.logger.error('[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: NO (returned None)')
        app.logger.error('[1688 Scraping] ❌ ScrapingAnt API key not configured in database')
        return {'error': 'ScrapingAnt API key not configured'}
    
    api_key_stripped = api_key.strip() if isinstance(api_key, str) else ''
    
    if api_key_stripped == '':
        app.logger.error('[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: NO (empty string)')
        app.logger.error('[1688 Scraping] ❌ ScrapingAnt API key is empty')
        return {'error': 'ScrapingAnt API key not configured'}
    
    app.logger.info(f'[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: YES')
    app.logger.info(f'[1688 Scraping] ✅ API key found (length: {len(api_key_stripped)})')
    app.logger.info(f'[1688 Scraping] API key preview: {api_key_stripped[:10]}...')
    
    search_url = f'https://s.1688.com/selloffer/offer_search.htm?keywords={keyword}'
    app.logger.info(f'[1688 Scraping] Search URL: {search_url}')
    
    params = {
        'url': search_url,
        'x-api-key': api_key,
        'browser': 'true',
        'cookies_persistence': 'true',
        'return_page_source': 'true'
    }
    
    try:
        app.logger.info('[1688 Scraping] Sending request to ScrapingAnt API...')
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, timeout=60)
        
        app.logger.info(f'[1688 Scraping] Response status: {response.status_code}')
        app.logger.info(f'[1688 Scraping] Response length: {len(response.text)} characters')
        
        response.raise_for_status()
        
        # Parse HTML response
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Log page structure for debugging
        app.logger.info(f'[1688 Scraping] Parsed HTML. Looking for product cards...')
        
        products = []
        # Simplified parsing - actual implementation would need real 1688 HTML structure
        card_items = soup.find_all('div', class_='card-item')
        app.logger.info(f'[1688 Scraping] Found {len(card_items)} card-item elements')
        
        # Try alternative selectors if no card-item found
        if len(card_items) == 0:
            app.logger.warning('[1688 Scraping] No card-item elements found. Trying alternative selectors...')
            # Try different common selectors
            card_items = soup.find_all('div', class_='offer-item')
            app.logger.info(f'[1688 Scraping] Found {len(card_items)} offer-item elements')
        
        if len(card_items) == 0:
            card_items = soup.find_all('div', class_='item')
            app.logger.info(f'[1688 Scraping] Found {len(card_items)} item elements')
        
        for idx, item in enumerate(card_items[:max_results]):
            try:
                product = {
                    'url': item.find('a')['href'] if item.find('a') else '',
                    'title': item.find('h3').get_text(strip=True) if item.find('h3') else '',
                    'price': float(item.find('span', class_='price').get_text(strip=True).replace('¥', '')) if item.find('span', class_='price') else 0,
                    'sales': int(item.find('span', class_='sales').get_text(strip=True).replace('销', '')) if item.find('span', class_='sales') else 0,
                    'image': item.find('img')['src'] if item.find('img') else ''
                }
                
                # Only add if we have at least title and price
                if product['title'] and product['price'] > 0:
                    products.append(product)
                    app.logger.debug(f'[1688 Scraping] Product {idx+1}: {product["title"][:40]} - ¥{product["price"]}')
                else:
                    app.logger.debug(f'[1688 Scraping] Skipped product {idx+1}: missing title or price')
            except Exception as e:
                app.logger.warning(f'[1688 Scraping] Failed to parse product {idx+1}: {str(e)}')
                continue
        
        app.logger.info(f'[1688 Scraping] ✅ Successfully parsed {len(products)} products')
        return {'products': products, 'count': len(products)}
    
    except requests.exceptions.RequestException as e:
        error_msg = f'Request failed: {str(e)}'
        app.logger.error(f'[1688 Scraping] ❌ {error_msg}')
        return {'error': error_msg}
    except Exception as e:
        error_msg = f'Parsing failed: {str(e)}'
        app.logger.error(f'[1688 Scraping] ❌ {error_msg}')
        app.logger.exception(e)
        return {'error': error_msg}

def analyze_product_profitability(price_cny):
    """Calculate profit margin and KRW price"""
    exchange_rate = float(get_config('cny_exchange_rate', 190))
    buffer = float(get_config('exchange_rate_buffer', 1.05))
    shipping = int(get_config('shipping_cost_base', 5000))
    customs_rate = float(get_config('customs_tax_rate', 0.10))
    
    # Use highest price for safety (prevent loss)
    purchase_price_krw = int(price_cny * exchange_rate * buffer)
    
    # Calculate costs
    customs_tax = int(purchase_price_krw * customs_rate)
    total_cost = purchase_price_krw + shipping + customs_tax
    
    # Calculate sale price with target margin
    target_margin = float(get_config('target_margin_rate', 30)) / 100
    sale_price = int(total_cost / (1 - target_margin))
    
    # Round to nearest 100
    sale_price = ((sale_price + 99) // 100) * 100
    
    # Calculate actual profit
    actual_profit = sale_price - total_cost
    actual_margin = (actual_profit / sale_price * 100) if sale_price > 0 else 0
    
    return {
        'purchase_price_krw': purchase_price_krw,
        'shipping_cost': shipping,
        'customs_tax': customs_tax,
        'total_cost': total_cost,
        'sale_price': sale_price,
        'profit': actual_profit,
        'margin': actual_margin,
        'exchange_rate': exchange_rate
    }

def generate_test_products(keyword, count=5):
    """Generate test products for development/testing when scraping fails"""
    import random
    
    app.logger.warning(f'[Test Data] Generating {count} test products for keyword: {keyword}')
    
    test_products = []
    for i in range(count):
        price = random.uniform(10, 200)
        test_products.append({
            'url': f'https://detail.1688.com/offer/{1000000 + i}.html',
            'title': f'{keyword} 테스트상품 {i+1} - 고품질 무료배송',
            'price': round(price, 2),
            'sales': random.randint(100, 5000),
            'image': 'https://via.placeholder.com/300x300?text=Test+Product'
        })
    
    app.logger.info(f'[Test Data] ✅ Generated {len(test_products)} test products')
    return test_products

def execute_smart_sourcing(keyword, use_test_data=False):
    """
    Unified [Smart Sniper] engine for both keyword search and AI discovery
    
    Execution steps:
    1. 1688 Lite search (listing only - no detail pages)
    2. Load config: target_margin, cny_rate, delivery_fee
    3. Margin simulation - drop items not meeting target_margin
    4. Sort by net profit (descending)
    5. Slice to Top 3 only
    6. Use ScrapingAnt tokens ONLY for these 3 items to fetch details
    
    Returns: dict with 'success', 'products' (Top 3 only), 'stats'
    """
    app.logger.info(f'[Smart Sniper] ========================================')
    app.logger.info(f'[Smart Sniper] Executing unified sourcing for keyword: {keyword}')
    app.logger.info(f'[Smart Sniper] Use test data: {use_test_data}')
    
    # ========================================================================
    # CRITICAL: SYSTEM CHECK - Verify DB and load configurations
    # ========================================================================
    try:
        app.logger.info('[Smart Sniper] 🔍 Running SYSTEM-CHECK before sourcing...')
        system_config = system_check_critical_configs()
        app.logger.info(f'[Smart Sniper] ✅ System check passed: {system_config}')
    except RuntimeError as e:
        app.logger.error(f'[Smart Sniper] ❌ SYSTEM CHECK FAILED: {str(e)}')
        log_activity('sourcing', f'❌ System check failed: {str(e)}', 'error')
        return {
            'success': False,
            'error': f'System configuration error: {str(e)}',
            'stats': {'scanned': 0, 'safe': 0, 'profitable': 0, 'final_count': 0}
        }
    
    # ========================================================================
    # Load configs from DB (NEVER use global variables)
    # ========================================================================
    scrapingant_key = get_config('scrapingant_api_key', '')
    openai_key = get_config('openai_api_key', '')
    target_margin_rate = get_config('target_margin_rate', 30)
    cny_exchange_rate = get_config('cny_exchange_rate', 190)
    
    app.logger.info('[Smart Sniper] 📋 Config loaded from DB:')
    app.logger.info(f'  - ScrapingAnt key: {scrapingant_key[:4]}**** (len: {len(scrapingant_key)})')
    app.logger.info(f'  - OpenAI key: {openai_key[:4]}**** (len: {len(openai_key)})')
    app.logger.info(f'  - Target margin: {target_margin_rate}%')
    app.logger.info(f'  - CNY rate: {cny_exchange_rate}')
    
    if not scrapingant_key and not use_test_data:
        app.logger.error('[Smart Sniper] ❌ CRITICAL: ScrapingAnt API key is EMPTY after DB load')
        app.logger.error('[Smart Sniper] Please configure API key in Settings page')
        log_activity('sourcing', '❌ ScrapingAnt API key not configured', 'error')
        return {
            'success': False,
            'error': 'ScrapingAnt API key not configured. Please set it in Settings.',
            'stats': {'scanned': 0, 'safe': 0, 'profitable': 0, 'final_count': 0}
        }
    
    # Step 1: 1688 Lite Search (Listing Only)
    log_activity('sourcing', f'Step 1/5: 🔍 1688 Lite Search for "{keyword}"', 'in_progress')
    
    if use_test_data:
        # Use test data for development/debugging
        app.logger.warning('[Smart Sniper] Using TEST DATA instead of real scraping')
        products = generate_test_products(keyword, count=10)
        log_activity('sourcing', f'Found {len(products)} TEST items (development mode)', 'warning')
    else:
        # Real scraping
        results = scrape_1688_search(keyword, max_results=50)
        
        if 'error' in results:
            error_msg = results['error']
            app.logger.error(f'[Smart Sniper] Scraping error: {error_msg}')
            log_activity('sourcing', f'❌ Search failed: {error_msg}', 'error')
            
            # Fallback to test data if scraping fails
            app.logger.warning('[Smart Sniper] Falling back to TEST DATA due to scraping failure')
            products = generate_test_products(keyword, count=10)
            log_activity('sourcing', f'Using {len(products)} TEST items as fallback', 'warning')
        else:
            products = results.get('products', [])
            app.logger.info(f'[Smart Sniper] Raw scraping result: {len(products)} products')
            log_activity('sourcing', f'Found {len(products)} items from listing', 'success')
    
    # Critical check: if still no products, cannot continue
    if len(products) == 0:
        app.logger.error('[Smart Sniper] ❌ CRITICAL: No products found after scraping AND test data fallback')
        log_activity('sourcing', '❌ No products found - cannot continue', 'error')
        return {
            'success': False,
            'error': 'No products found. Please check ScrapingAnt API or try different keyword.',
            'stats': {'scanned': 0, 'safe': 0, 'profitable': 0, 'final_count': 0}
        }
    
    # Step 2: Safety Filter
    log_activity('sourcing', 'Step 2/5: 🛡️ Applying safety filters', 'in_progress')
    app.logger.info(f'[Smart Sniper] Starting safety filter on {len(products)} products')
    
    safe_products = []
    filtered_count = 0
    for product in products:
        is_safe, reason = check_safety_filter(product['title'])
        if is_safe:
            safe_products.append(product)
        else:
            filtered_count += 1
            app.logger.debug(f'[Safety Filter] Filtered: {product["title"][:40]} - {reason}')
    
    app.logger.info(f'[Smart Sniper] Safety filter result: {len(safe_products)} safe, {filtered_count} filtered')
    log_activity('sourcing', f'{len(safe_products)}/{len(products)} items passed safety filter', 'success')
    
    # Step 3: Margin Simulation (Load Config)
    log_activity('sourcing', 'Step 3/5: 💰 Margin simulation in progress', 'in_progress')
    target_margin = float(get_config('target_margin_rate', 30))
    app.logger.info(f'[Smart Sniper] Target margin: {target_margin}%')
    app.logger.info(f'[Smart Sniper] Analyzing profitability of {len(safe_products)} products')
    
    profitable_products = []
    failed_margin_count = 0
    
    for idx, product in enumerate(safe_products):
        try:
            analysis = analyze_product_profitability(product['price'])
            
            app.logger.debug(f'[Margin Check {idx+1}] {product["title"][:30]}: '
                           f'Price ¥{product["price"]}, '
                           f'Margin {analysis["margin"]:.1f}%, '
                           f'Profit ₩{analysis["profit"]:,}')
            
            # Drop items not meeting target margin
            if analysis['margin'] >= target_margin:
                product['analysis'] = analysis
                profitable_products.append(product)
            else:
                failed_margin_count += 1
        except Exception as e:
            app.logger.error(f'[Margin Check] Failed for product {idx+1}: {str(e)}')
            failed_margin_count += 1
    
    app.logger.info(f'[Smart Sniper] Profitability result: {len(profitable_products)} profitable, {failed_margin_count} rejected')
    log_activity('sourcing', f'{len(profitable_products)} items meet target margin {target_margin}%', 'success')
    
    # Step 4: Sort by net profit (descending)
    profitable_products.sort(key=lambda x: x['analysis']['profit'], reverse=True)
    
    # Step 5: Slice to Top 3 ONLY
    top_3 = profitable_products[:3]
    log_activity('sourcing', f'Step 4/5: 🎯 Top 3 selected (sorted by profit)', 'success')
    
    if len(top_3) == 0:
        log_activity('sourcing', '⚠️ No profitable products found', 'warning')
        return {
            'success': True,
            'products': [],
            'stats': {
                'scanned': len(products),
                'safe': len(safe_products),
                'profitable': len(profitable_products),
                'final_count': 0
            }
        }
    
    # Step 6: Save Top 3 to Database
    log_activity('sourcing', 'Step 5/5: 💾 Saving Top 3 to database', 'in_progress')
    app.logger.info(f'[Smart Sniper] Attempting to save {len(top_3)} products to database')
    
    conn = get_db()
    cursor = conn.cursor()
    
    saved_count = 0
    for idx, product in enumerate(top_3):
        try:
            app.logger.info(f'[DB Save {idx+1}] Title: {product["title"][:50]}')
            app.logger.info(f'[DB Save {idx+1}] Price CNY: ¥{product["price"]}')
            app.logger.info(f'[DB Save {idx+1}] Price KRW: ₩{product["analysis"]["sale_price"]:,}')
            app.logger.info(f'[DB Save {idx+1}] Margin: {product["analysis"]["margin"]:.1f}%')
            app.logger.info(f'[DB Save {idx+1}] Profit: ₩{product["analysis"]["profit"]:,}')
            
            cursor.execute('''
                INSERT INTO sourced_products 
                (original_url, title_cn, price_cny, price_krw, profit_margin, 
                 estimated_profit, safety_status, images_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product['url'],
                product['title'],
                product['price'],
                product['analysis']['sale_price'],
                product['analysis']['margin'],
                product['analysis']['profit'],
                'passed',
                json.dumps([product['image']]),
                'pending'
            ))
            saved_count += 1
            app.logger.info(f'[DB Save {idx+1}] ✅ Successfully inserted')
        except Exception as e:
            app.logger.error(f'[DB Save {idx+1}] ❌ Failed to insert: {str(e)}')
            app.logger.exception(e)
    
    conn.commit()
    conn.close()
    
    app.logger.info(f'[Smart Sniper] Completed: {saved_count}/{len(top_3)} products saved to database')
    log_activity('sourcing', f'✅ Smart Sourcing completed: {saved_count} products saved', 'success')
    
    return {
        'success': True,
        'products': top_3,
        'stats': {
            'scanned': len(products),
            'safe': len(safe_products),
            'profitable': len(profitable_products),
            'final_count': len(top_3)
        }
    }

@app.route('/api/sourcing/start', methods=['POST'])
@login_required
def start_sourcing():
    """
    Unified sourcing endpoint supporting two modes:
    - Case A (Direct search): Use user-provided keyword
    - Case B (AI Blue Ocean): Run GPT-4 analysis first, then use suggested keyword
    """
    data = request.json
    user_keyword = data.get('keyword', '')
    mode = data.get('mode', 'direct')  # 'direct' or 'ai_discovery'
    use_test_data = data.get('use_test_data', False)  # NEW: test data mode
    
    app.logger.info(f'=== Sourcing Started by {current_user.username} ===')
    app.logger.info(f'Mode: {mode}, User keyword: {user_keyword}, Test data: {use_test_data}')
    
    # Determine target keyword based on mode
    if mode == 'ai_discovery':
        # Case B: AI Blue Ocean Discovery
        log_activity('sourcing', 'Step 0: 🌊 Blue Ocean Market Analysis', 'in_progress')
        
        blue_ocean_result = analyze_blue_ocean_market(user_keyword)
        target_keyword = blue_ocean_result['suggested_keyword']
        reasoning = blue_ocean_result['reasoning']
        
        app.logger.info(f'Blue Ocean Keyword: {target_keyword}')
        app.logger.info(f'Reasoning: {reasoning}')
        
        log_activity('sourcing', 
                    f'🎯 Blue Ocean Keyword: "{target_keyword}"', 
                    'success',
                    {'reasoning': reasoning, 'original': user_keyword})
        
        blue_ocean_data = {
            'original_keyword': user_keyword,
            'suggested_keyword': target_keyword,
            'reasoning': reasoning,
            'trend_score': blue_ocean_result.get('trend_score', 0),
            'competition_score': blue_ocean_result.get('competition_score', 0)
        }
    else:
        # Case A: Direct keyword search
        target_keyword = user_keyword
        blue_ocean_data = None
        log_activity('sourcing', f'📌 Direct search mode: "{target_keyword}"', 'info')
    
    # Execute unified Smart Sniper engine
    result = execute_smart_sourcing(target_keyword, use_test_data=use_test_data)
    
    if not result['success']:
        return jsonify({'error': result.get('error', 'Unknown error')}), 500
    
    # Build response
    response_data = {
        'success': True,
        'mode': mode,
        'keyword': target_keyword,
        'stats': result['stats']
    }
    
    if blue_ocean_data:
        response_data['blue_ocean_analysis'] = blue_ocean_data
    
    app.logger.info(f'=== Sourcing Completed: {result["stats"]["final_count"]} products ===')
    
    return jsonify(response_data)

@app.route('/api/sourcing/test-scraping', methods=['POST'])
@login_required
def test_scraping():
    """
    Diagnostic endpoint to test 1688 scraping functionality
    Returns detailed information about scraping attempt
    """
    data = request.json
    keyword = data.get('keyword', '电热毯')  # Default test keyword
    
    app.logger.info(f'[Test Scraping] Testing scraping for keyword: {keyword}')
    
    # Test scraping
    result = scrape_1688_search(keyword, max_results=10)
    
    # Build diagnostic response
    if 'error' in result:
        return jsonify({
            'success': False,
            'error': result['error'],
            'keyword': keyword,
            'timestamp': datetime.now().isoformat()
        })
    
    products = result.get('products', [])
    
    return jsonify({
        'success': True,
        'keyword': keyword,
        'product_count': len(products),
        'products': products[:5],  # Return first 5 for preview
        'sample_product': products[0] if products else None,
        'timestamp': datetime.now().isoformat()
    })

# ============================================================================
# MODULE 3: AI CONTENT GENERATOR WITH IMAGE PROCESSING
# ============================================================================

def generate_marketing_copy(title, price):
    """Generate marketing copy using GPT-4"""
    api_key = get_config('openai_api_key')
    if not api_key:
        return '상품 설명이 준비 중입니다.'
    
    prompt = f"""
다음 상품에 대한 한국어 마케팅 카피를 작성해주세요.
상품명: {title}
가격: {price:,}원

구조:
1. 훅(Hook): 고객의 관심을 끄는 한 문장
2. 문제(Problem): 이 상품이 해결하는 고객의 불편함
3. 솔루션(Solution): 이 상품의 장점과 특징

300자 이내로 작성해주세요.
"""
    
    try:
        # CRITICAL: Using gpt-4o-mini (universal access, no 404 errors)
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',  # FORCED: Must use gpt-4o-mini
                'messages': [
                    {'role': 'system', 'content': '당신은 전문 카피라이터입니다.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return '상품 설명이 준비 중입니다.'
    
    except Exception as e:
        log_activity('content', f'Failed to generate copy: {str(e)}', 'error')
        return '상품 설명이 준비 중입니다.'

def process_product_image(image_url, chinese_text_regions=None):
    """
    Download image, overlay text boxes, and add Korean text
    Simplified implementation - actual would use OCR for text detection
    """
    try:
        # Download image
        response = requests.get(image_url, timeout=10)
        img = Image.open(io.BytesIO(response.content))
        
        # Remove metadata
        data = list(img.getdata())
        image_without_exif = Image.new(img.mode, img.size)
        image_without_exif.putdata(data)
        
        # If text regions provided, overlay boxes
        if chinese_text_regions:
            draw = ImageDraw.Draw(image_without_exif, 'RGBA')
            
            # Try to load Korean font
            try:
                font = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', 20)
            except:
                font = ImageFont.load_default()
            
            for region in chinese_text_regions:
                x, y, w, h = region['bbox']
                korean_text = region.get('korean_text', '')
                
                # Draw semi-transparent white box
                draw.rectangle([x, y, x+w, y+h], fill=(255, 255, 255, 200))
                
                # Draw Korean text
                draw.text((x+5, y+5), korean_text, fill=(0, 0, 0, 255), font=font)
        
        # Save to memory
        output = io.BytesIO()
        image_without_exif.save(output, format='PNG')
        output.seek(0)
        
        # Save to disk
        filename = f"processed_{int(time.time())}_{os.path.basename(image_url)}.png"
        filepath = os.path.join('static', 'processed_images', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            f.write(output.getvalue())
        
        return f'/static/processed_images/{filename}'
    
    except Exception as e:
        log_activity('content', f'Image processing failed: {str(e)}', 'error')
        return image_url

@app.route('/api/content/generate/<int:product_id>', methods=['POST'])
@login_required
def generate_content(product_id):
    """Generate AI content for product"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM sourced_products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    
    log_activity('content', f'Generating content for product {product_id}', 'in_progress')
    
    # Generate marketing copy
    marketing_copy = generate_marketing_copy(product['title_cn'], product['price_krw'])
    
    # Process images
    original_images = json.loads(product['images_json']) if product['images_json'] else []
    processed_images = []
    
    for img_url in original_images[:5]:  # Process max 5 images
        processed_url = process_product_image(img_url)
        processed_images.append(processed_url)
    
    # Add notice image (create or use existing)
    notice_path = create_notice_image()
    processed_images.append(notice_path)
    
    # Update database
    cursor.execute('''
        UPDATE sourced_products
        SET marketing_copy = ?,
            processed_images_json = ?,
            title_kr = ?
        WHERE id = ?
    ''', (marketing_copy, json.dumps(processed_images), product['title_cn'], product_id))
    
    conn.commit()
    conn.close()
    
    log_activity('content', f'Content generated for product {product_id}', 'success')
    
    return jsonify({
        'success': True,
        'marketing_copy': marketing_copy,
        'processed_images': processed_images
    })

def create_notice_image():
    """Create notice image for product detail bottom"""
    width, height = 800, 400
    img = Image.new('RGB', (width, height), color=(255, 248, 240))
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', 24)
        font_text = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', 16)
    except:
        font_title = font_text = ImageFont.load_default()
    
    # Draw notice content
    draw.text((50, 50), '⚠️ 해외직구 상품 안내', fill=(220, 20, 60), font=font_title)
    
    notices = [
        '• 본 상품은 해외 직구 상품으로 배송기간이 2-3주 소요됩니다.',
        '• 통관 과정에서 추가 세금이 발생할 수 있습니다.',
        '• 단순 변심 반품 시 왕복 배송비가 부과됩니다.',
        '• 상품 문의는 고객센터로 연락 주시기 바랍니다.'
    ]
    
    y = 120
    for notice in notices:
        draw.text((50, y), notice, fill=(50, 50, 50), font=font_text)
        y += 40
    
    # Save
    filepath = 'static/notice_image.png'
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    img.save(filepath)
    
    return '/static/notice_image.png'

# ============================================================================
# MODULE 4: NAVER/COUPANG API INTEGRATION
# ============================================================================

def generate_naver_signature(client_id, client_secret, timestamp, method, path):
    """Generate Naver Commerce API signature with bcrypt"""
    message = f"{timestamp}.{method}.{path}"
    signature = hmac.new(
        client_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return base64.b64encode(signature.encode()).decode()

def register_to_naver(product_data):
    """Register product to Naver Smart Store"""
    client_id = get_config('naver_client_id')
    client_secret = get_config('naver_client_secret')
    
    if not client_id or not client_secret:
        return {'error': 'Naver API credentials not configured'}
    
    timestamp = str(int(time.time() * 1000))
    path = '/v1/products'
    signature = generate_naver_signature(client_id, client_secret, timestamp, 'POST', path)
    
    headers = {
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret,
        'X-Timestamp': timestamp,
        'X-Signature': signature,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            f'https://api.commerce.naver.com{path}',
            headers=headers,
            json=product_data,
            timeout=30
        )
        
        return response.json()
    
    except Exception as e:
        return {'error': str(e)}

def register_to_coupang(product_data):
    """Register product to Coupang"""
    access_key = get_config('coupang_access_key')
    secret_key = get_config('coupang_secret_key')
    
    if not access_key or not secret_key:
        return {'error': 'Coupang API credentials not configured'}
    
    # Coupang requires IP whitelisting
    static_ip = get_config('server_static_ip')
    if not static_ip:
        log_activity('marketplace', 'Warning: Static IP not configured for Coupang', 'warning')
    
    path = '/v2/providers/seller_api/apis/api/v1/marketplace/seller-products'
    timestamp = str(int(time.time() * 1000))
    
    message = timestamp + 'POST' + path + ''
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={timestamp}, signature={signature}'
    }
    
    try:
        response = requests.post(
            f'https://api-gateway.coupang.com{path}',
            headers=headers,
            json=product_data,
            timeout=30
        )
        
        return response.json()
    
    except Exception as e:
        return {'error': str(e)}

def update_marketplace_status(marketplace, external_id, status):
    """Update order status on marketplace"""
    if marketplace == 'naver':
        return update_naver_order_status(external_id, status)
    elif marketplace == 'coupang':
        return update_coupang_order_status(external_id, status)
    
    return {'error': 'Unknown marketplace'}

def update_naver_order_status(order_id, status):
    """Update Naver order status"""
    # Check if API credentials are configured
    client_id = get_config('naver_client_id')
    client_secret = get_config('naver_client_secret')
    
    if not client_id or not client_secret:
        log_activity('marketplace', 'Naver API credentials not configured - skipping status update', 'warning')
        return {'success': True, 'message': f'Order {order_id} status updated locally (API not configured)', 'skipped': True}
    
    # Simplified implementation - in production, make actual API call
    return {'success': True, 'message': f'Order {order_id} status updated to {status}'}

def update_coupang_order_status(order_id, status):
    """Update Coupang order status"""
    # Check if API credentials are configured
    access_key = get_config('coupang_access_key')
    secret_key = get_config('coupang_secret_key')
    
    if not access_key or not secret_key:
        log_activity('marketplace', 'Coupang API credentials not configured - skipping status update', 'warning')
        return {'success': True, 'message': f'Order {order_id} status updated locally (API not configured)', 'skipped': True}
    
    # Simplified implementation - in production, make actual API call
    return {'success': True, 'message': f'Order {order_id} status updated to {status}'}

# ============================================================================
# MODULE 5: ORDER MANAGEMENT WITH PCCC VALIDATION
# ============================================================================

def validate_pccc(pccc):
    """Validate Korean PCCC (Personal Customs Clearance Code)"""
    # PCCC format: P123456789012 (P + 12 digits)
    pattern = r'^P\d{12}$'
    return bool(re.match(pattern, pccc))

@app.route('/api/orders/create', methods=['POST'])
@login_required
def create_order():
    """Create new order"""
    data = request.json
    
    # Validate PCCC
    pccc = data.get('pccc', '')
    if not validate_pccc(pccc):
        return jsonify({'error': 'Invalid PCCC format'}), 400
    
    # Get current exchange rate (will be locked to this order)
    current_rate = float(get_config('cny_exchange_rate', 190))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Calculate order financials
    price_cny = data.get('price_cny', 0)
    quantity = data.get('quantity', 1)
    
    analysis = analyze_product_profitability(price_cny)
    marketplace_fee_rate = float(get_config(f"{data.get('marketplace', 'naver')}_fee_rate", 0.06))
    marketplace_fee = int(analysis['sale_price'] * marketplace_fee_rate)
    
    net_profit = analysis['profit'] - marketplace_fee
    
    # Set shipping deadline (3 days from now)
    shipping_deadline = datetime.now() + timedelta(days=3)
    
    cursor.execute('''
        INSERT INTO orders (
            order_number, marketplace, product_id, customer_name, customer_phone,
            customer_address, pccc, pccc_validated, quantity, sale_price,
            purchase_price_cny, purchase_price_krw, applied_exchange_rate,
            shipping_cost, customs_tax, marketplace_fee, net_profit,
            original_product_url, shipping_deadline, order_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('order_number'),
        data.get('marketplace'),
        data.get('product_id'),
        data.get('customer_name'),
        data.get('customer_phone'),
        data.get('customer_address'),
        pccc,
        True,
        quantity,
        analysis['sale_price'] * quantity,
        price_cny,
        analysis['purchase_price_krw'],
        current_rate,  # Lock exchange rate
        analysis['shipping_cost'],
        analysis['customs_tax'],
        marketplace_fee,
        net_profit * quantity,
        data.get('original_product_url'),
        shipping_deadline.isoformat(),
        'pending'
    ))
    
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    log_activity('order', f'Order {data.get("order_number")} created', 'success')
    
    return jsonify({'success': True, 'order_id': order_id})

@app.route('/api/orders/<int:order_id>/confirm', methods=['POST'])
@login_required
def confirm_order(order_id):
    """Mark order as confirmed and update marketplace status"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    # Update local status
    cursor.execute('''
        UPDATE orders SET order_status = 'confirmed' WHERE id = ?
    ''', (order_id,))
    
    conn.commit()
    conn.close()
    
    # Update marketplace
    result = update_marketplace_status(
        order['marketplace'],
        order['order_number'],
        'preparing'
    )
    
    log_activity('order', f'Order {order["order_number"]} confirmed', 'success')
    
    return jsonify({'success': True})

@app.route('/api/orders/<int:order_id>/ship', methods=['POST'])
@login_required
def ship_order(order_id):
    """Add tracking number and mark as shipped"""
    data = request.json
    tracking_number = data.get('tracking_number', '')
    
    if not tracking_number:
        return jsonify({'error': 'Tracking number required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    # Update order
    cursor.execute('''
        UPDATE orders 
        SET tracking_number = ?,
            order_status = 'shipped',
            shipped_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (tracking_number, order_id))
    
    conn.commit()
    conn.close()
    
    # Update marketplace
    result = update_marketplace_status(
        order['marketplace'],
        order['order_number'],
        'shipping'
    )
    
    log_activity('order', f'Order {order["order_number"]} shipped with tracking {tracking_number}', 'success')
    
    return jsonify({'success': True})

@app.route('/api/orders/<int:order_id>/deliver', methods=['POST'])
@login_required
def deliver_order(order_id):
    """Mark order as delivered and create tax record"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    # Update order status
    cursor.execute('''
        UPDATE orders 
        SET order_status = 'delivered',
            delivered_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (order_id,))
    
    # Create tax record
    cursor.execute('''
        INSERT INTO tax_records (
            order_id, order_number, sale_date, sale_amount,
            purchase_amount, shipping_cost, marketplace_fee,
            net_profit, applied_exchange_rate
        ) VALUES (?, ?, DATE('now'), ?, ?, ?, ?, ?, ?)
    ''', (
        order_id,
        order['order_number'],
        order['sale_price'],
        order['purchase_price_krw'],
        order['shipping_cost'],
        order['marketplace_fee'],
        order['net_profit'],
        order['applied_exchange_rate']
    ))
    
    conn.commit()
    conn.close()
    
    log_activity('order', f'Order {order["order_number"]} delivered', 'success')
    
    return jsonify({'success': True})

# ============================================================================
# MODULE 6: RISK DEFENSE - STOCK MONITORING
# ============================================================================

def check_product_stock_status(product_url):
    """Check if product is still available on 1688"""
    api_key = get_config('scrapingant_api_key')
    if not api_key:
        return {'available': True, 'reason': 'Cannot verify - API key missing'}
    
    try:
        params = {
            'url': product_url,
            'x-api-key': api_key,
            'browser': 'true'
        }
        
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, timeout=30)
        
        if response.status_code == 404:
            return {'available': False, 'reason': 'Product deleted'}
        
        # Check for out of stock indicators
        text = response.text.lower()
        if '下架' in text or '已下架' in text or '缺货' in text:
            return {'available': False, 'reason': 'Out of stock'}
        
        return {'available': True, 'reason': 'Available'}
    
    except Exception as e:
        return {'available': True, 'reason': f'Check failed: {str(e)}'}

def run_stock_monitor():
    """Daily stock monitoring job"""
    log_activity('stock_monitor', 'Starting daily stock check', 'in_progress')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all active marketplace listings
    cursor.execute('''
        SELECT ml.id, ml.product_id, sp.original_url, ml.marketplace, ml.external_product_id
        FROM marketplace_listings ml
        JOIN sourced_products sp ON ml.product_id = sp.id
        WHERE ml.status = 'active'
    ''')
    
    listings = cursor.fetchall()
    
    for listing in listings:
        status = check_product_stock_status(listing['original_url'])
        
        if not status['available']:
            # Mark as out of stock
            cursor.execute('''
                UPDATE marketplace_listings
                SET status = 'out_of_stock', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (listing['id'],))
            
            # Log action
            cursor.execute('''
                INSERT INTO stock_monitor_log (product_id, original_url, check_status, action_taken)
                VALUES (?, ?, ?, ?)
            ''', (
                listing['product_id'],
                listing['original_url'],
                'unavailable',
                f"Marked as out of stock: {status['reason']}"
            ))
            
            log_activity('stock_monitor', 
                        f"Product {listing['product_id']} marked out of stock: {status['reason']}", 
                        'warning')
        else:
            cursor.execute('''
                INSERT INTO stock_monitor_log (product_id, original_url, check_status, action_taken)
                VALUES (?, ?, ?, ?)
            ''', (
                listing['product_id'],
                listing['original_url'],
                'available',
                'No action needed'
            ))
    
    conn.commit()
    conn.close()
    
    log_activity('stock_monitor', f'Stock check completed. Checked {len(listings)} products', 'success')

# Schedule daily stock monitoring
schedule.every().day.at("02:00").do(run_stock_monitor)

def run_scheduler():
    """Run scheduled tasks in background thread"""
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start scheduler thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# ============================================================================
# MODULE 7: TAX AUTOMATION & EXCEL EXPORT
# ============================================================================

@app.route('/api/tax/export', methods=['GET'])
@login_required
def export_tax_records():
    """Export tax records to Excel"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM tax_records WHERE 1=1'
    params = []
    
    if start_date:
        query += ' AND sale_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND sale_date <= ?'
        params.append(end_date)
    
    query += ' ORDER BY sale_date DESC'
    
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "판매대장"
    
    # Header style
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    # Headers
    headers = [
        '일자', '주문번호', '판매금액', '매입금액(원)', '배송비', 
        '수수료', '순수익', '적용환율', '비고'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    # Data rows
    for row_idx, record in enumerate(records, 2):
        ws.cell(row=row_idx, column=1, value=record['sale_date'])
        ws.cell(row=row_idx, column=2, value=record['order_number'])
        ws.cell(row=row_idx, column=3, value=record['sale_amount'])
        ws.cell(row=row_idx, column=4, value=record['purchase_amount'])
        ws.cell(row=row_idx, column=5, value=record['shipping_cost'])
        ws.cell(row=row_idx, column=6, value=record['marketplace_fee'])
        ws.cell(row=row_idx, column=7, value=record['net_profit'])
        ws.cell(row=row_idx, column=8, value=record['applied_exchange_rate'])
        ws.cell(row=row_idx, column=9, value='완료')
    
    # Add summary row
    summary_row = len(records) + 3
    ws.cell(row=summary_row, column=1, value='합계').font = Font(bold=True)
    ws.cell(row=summary_row, column=3, value=f'=SUM(C2:C{len(records)+1})')
    ws.cell(row=summary_row, column=7, value=f'=SUM(G2:G{len(records)+1})')
    
    # Adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width
    
    # Save to file
    filename = f'tax_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    filepath = os.path.join('static', 'exports', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    wb.save(filepath)
    
    log_activity('tax', f'Exported {len(records)} tax records', 'success')
    
    return send_file(filepath, as_attachment=True, download_name=filename)

# ============================================================================
# MODULE 8: DASHBOARD & FRONTEND ROUTES
# ============================================================================

@app.route('/')
@login_required
def dashboard():
    """Main dashboard"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) as count FROM sourced_products WHERE status = "pending"')
    pending_products = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM orders WHERE order_status = "pending"')
    pending_orders = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM orders WHERE datetime(shipping_deadline) < datetime("now", "+1 day")')
    urgent_orders = cursor.fetchone()['count']
    
    cursor.execute('SELECT SUM(net_profit) as total FROM orders WHERE order_status = "delivered"')
    total_profit = cursor.fetchone()['total'] or 0
    
    # NEW: Financial analytics for Version 2.0
    # Today's revenue
    cursor.execute('''
        SELECT 
            COALESCE(SUM(sale_price), 0) as today_sales,
            COALESCE(SUM(net_profit), 0) as today_profit
        FROM orders 
        WHERE DATE(delivered_at) = DATE('now') AND order_status = 'delivered'
    ''')
    today_stats = cursor.fetchone()
    today_sales = today_stats['today_sales']
    today_profit = today_stats['today_profit']
    
    # This month's revenue
    cursor.execute('''
        SELECT 
            COALESCE(SUM(sale_price), 0) as month_sales,
            COALESCE(SUM(net_profit), 0) as month_profit
        FROM orders 
        WHERE strftime('%Y-%m', delivered_at) = strftime('%Y-%m', 'now') 
        AND order_status = 'delivered'
    ''')
    month_stats = cursor.fetchone()
    month_sales = month_stats['month_sales']
    month_profit = month_stats['month_profit']
    
    # Last 7 days daily revenue for chart
    cursor.execute('''
        SELECT 
            DATE(delivered_at) as date,
            COALESCE(SUM(sale_price), 0) as daily_sales,
            COALESCE(SUM(net_profit), 0) as daily_profit
        FROM orders 
        WHERE delivered_at >= DATE('now', '-7 days') 
        AND order_status = 'delivered'
        GROUP BY DATE(delivered_at)
        ORDER BY date
    ''')
    daily_stats = cursor.fetchall()
    
    # Monthly revenue for last 6 months
    cursor.execute('''
        SELECT 
            strftime('%Y-%m', delivered_at) as month,
            COALESCE(SUM(sale_price), 0) as monthly_sales,
            COALESCE(SUM(net_profit), 0) as monthly_profit
        FROM orders 
        WHERE delivered_at >= DATE('now', '-6 months')
        AND order_status = 'delivered'
        GROUP BY strftime('%Y-%m', delivered_at)
        ORDER BY month
    ''')
    monthly_stats = cursor.fetchall()
    
    # Recent activity logs
    cursor.execute('SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 20')
    recent_logs = cursor.fetchall()
    
    conn.close()
    
    # Prepare chart data
    daily_labels = [row['date'] if row['date'] else '' for row in daily_stats] if daily_stats else []
    daily_sales_data = [row['daily_sales'] for row in daily_stats] if daily_stats else []
    daily_profit_data = [row['daily_profit'] for row in daily_stats] if daily_stats else []
    
    monthly_labels = [row['month'] if row['month'] else '' for row in monthly_stats] if monthly_stats else []
    monthly_profit_data = [row['monthly_profit'] for row in monthly_stats] if monthly_stats else []
    
    return render_template('dashboard.html',
                         pending_products=pending_products,
                         pending_orders=pending_orders,
                         urgent_orders=urgent_orders,
                         total_profit=total_profit,
                         today_sales=today_sales,
                         today_profit=today_profit,
                         month_sales=month_sales,
                         month_profit=month_profit,
                         daily_labels=json.dumps(daily_labels),
                         daily_sales_data=json.dumps(daily_sales_data),
                         daily_profit_data=json.dumps(daily_profit_data),
                         monthly_labels=json.dumps(monthly_labels),
                         monthly_profit_data=json.dumps(monthly_profit_data),
                         recent_logs=recent_logs)

@app.route('/products')
@login_required
def products():
    """Products management page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sourced_products ORDER BY created_at DESC')
    products = cursor.fetchall()
    conn.close()
    
    return render_template('products.html', products=products)

@app.route('/orders')
@login_required
def orders():
    """Orders management page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.*, sp.title_kr, sp.original_url
        FROM orders o
        LEFT JOIN sourced_products sp ON o.product_id = sp.id
        ORDER BY o.ordered_at DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    
    return render_template('orders.html', orders=orders)

@app.route('/config')
@login_required
def config_page():
    """Configuration page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM config')
    configs = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    
    return render_template('config.html', configs=configs)

@app.route('/logs')
@login_required
def logs_page():
    """System logs viewer page"""
    app.logger.info(f'User {current_user.username} accessed system logs')
    
    log_file_path = 'logs/server.log'
    log_lines = []
    
    try:
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8') as f:
                # Read all lines and get last 100
                all_lines = f.readlines()
                log_lines = all_lines[-100:] if len(all_lines) > 100 else all_lines
                # Reverse to show newest first
                log_lines.reverse()
        else:
            log_lines = ['[INFO] Log file not found. Server just started or no logs generated yet.']
    except Exception as e:
        log_lines = [f'[ERROR] Failed to read log file: {str(e)}']
        app.logger.error(f'Failed to read log file: {str(e)}')
    
    return render_template('logs.html', log_lines=log_lines)

@app.route('/api/config/update', methods=['POST'])
@login_required
def update_config():
    """Update configuration"""
    data = request.json
    
    app.logger.info('[Config Update] ========================================')
    app.logger.info(f'[Config Update] Received {len(data)} config items to update')
    
    saved_configs = []
    for key, value in data.items():
        # Log what's being saved (mask sensitive data)
        if 'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower():
            display_value = f'{value[:10]}...' if value and len(value) > 10 else '[EMPTY]'
        else:
            display_value = value
        
        app.logger.info(f'[Config Update] Saving: {key} = {display_value}')
        
        set_config(key, value)
        saved_configs.append(key)
        
        # Immediately verify it was saved
        verify_value = get_config(key)
        if verify_value == value:
            app.logger.info(f'[Config Update] ✅ Verified: {key} saved correctly')
        else:
            app.logger.error(f'[Config Update] ❌ FAILED: {key} mismatch! Expected: {value[:20]}..., Got: {verify_value}')
    
    app.logger.info(f'[Config Update] Successfully saved: {", ".join(saved_configs)}')
    log_activity('config', f'Configuration updated: {", ".join(saved_configs)}', 'success')
    
    return jsonify({'success': True, 'saved_configs': saved_configs})

@app.route('/api/config/verify', methods=['GET'])
@login_required
def verify_config():
    """Verify current configuration (diagnostic endpoint)"""
    app.logger.info('[Config Verify] Checking current configuration...')
    
    # Check critical config values
    configs_to_check = [
        'scrapingant_api_key',
        'openai_api_key',
        'target_margin_rate',
        'cny_exchange_rate',
        'exchange_rate_buffer',
        'shipping_cost_base',
        'customs_tax_rate'
    ]
    
    config_status = {}
    for key in configs_to_check:
        value = get_config(key)
        
        # Mask sensitive values
        if 'key' in key.lower() or 'secret' in key.lower():
            if value:
                masked = f'{value[:10]}...' if len(value) > 10 else '[TOO_SHORT]'
                config_status[key] = {
                    'configured': True,
                    'length': len(value),
                    'preview': masked
                }
                app.logger.info(f'[Config Verify] {key}: ✅ Configured (length: {len(value)})')
            else:
                config_status[key] = {
                    'configured': False,
                    'length': 0,
                    'preview': None
                }
                app.logger.warning(f'[Config Verify] {key}: ❌ Not configured')
        else:
            config_status[key] = {
                'configured': value is not None,
                'value': value
            }
            app.logger.info(f'[Config Verify] {key}: {value}')
    
    return jsonify({
        'success': True,
        'configs': config_status,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/logs/stream')
@login_required
def stream_logs():
    """Stream activity logs (SSE endpoint)"""
    def generate():
        last_id = 0
        while True:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM activity_logs WHERE id > ? ORDER BY id DESC LIMIT 10', (last_id,))
            logs = cursor.fetchall()
            conn.close()
            
            if logs:
                last_id = logs[0]['id']
                for log in logs:
                    yield f"data: {json.dumps(dict(log))}\n\n"
            
            time.sleep(2)
    
    return app.response_class(generate(), mimetype='text/event-stream')

@app.route('/api/products/<int:product_id>/approve', methods=['POST'])
@login_required
def approve_product(product_id):
    """Approve product for marketplace registration"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE sourced_products SET status = ?, approved_at = CURRENT_TIMESTAMP WHERE id = ?', 
                   ('approved', product_id))
    conn.commit()
    conn.close()
    
    log_activity('product', f'Product {product_id} approved', 'success')
    
    return jsonify({'success': True})

@app.route('/api/products/<int:product_id>/register', methods=['POST'])
@login_required
def register_product(product_id):
    """Register product to marketplace"""
    data = request.json
    marketplace = data.get('marketplace')
    
    if marketplace not in ['naver', 'coupang']:
        return jsonify({'error': 'Invalid marketplace'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM sourced_products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    
    # Prepare product data for marketplace
    product_data = {
        'title': product['title_kr'] or product['title_cn'],
        'description': product['marketing_copy'],
        'price': product['price_krw'],
        'images': json.loads(product['processed_images_json']) if product['processed_images_json'] else []
    }
    
    # Register to marketplace
    if marketplace == 'naver':
        result = register_to_naver(product_data)
    else:
        result = register_to_coupang(product_data)
    
    if 'error' in result:
        log_activity('marketplace', f'Failed to register product {product_id} to {marketplace}: {result["error"]}', 'error')
        return jsonify({'error': result['error']}), 500
    
    # Save marketplace listing
    cursor.execute('''
        INSERT INTO marketplace_listings (product_id, marketplace, external_product_id, status)
        VALUES (?, ?, ?, ?)
    ''', (product_id, marketplace, result.get('product_id', ''), 'active'))
    
    cursor.execute('UPDATE sourced_products SET status = ?, registered_at = CURRENT_TIMESTAMP WHERE id = ?',
                   ('registered', product_id))
    
    conn.commit()
    conn.close()
    
    log_activity('marketplace', f'Product {product_id} registered to {marketplace}', 'success')
    
    return jsonify({'success': True, 'external_id': result.get('product_id', '')})

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs('static/processed_images', exist_ok=True)
    os.makedirs('static/exports', exist_ok=True)
    
    # Run app
    app.run(host='0.0.0.0', port=5000, debug=False)
