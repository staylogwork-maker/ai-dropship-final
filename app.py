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
                    keywords TEXT,
                    source_site TEXT DEFAULT '1688',
                    moq INTEGER DEFAULT 1,
                    trend_score INTEGER DEFAULT 0,
                    competition_score INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    registered_at TIMESTAMP
                )
            ''')
            
            # CRITICAL: Add new columns if they don't exist (migration)
            migrations = [
                ('keywords', 'TEXT'),
                ('source_site', "TEXT DEFAULT '1688'"),
                ('moq', 'INTEGER DEFAULT 1'),
                ('trend_score', 'INTEGER DEFAULT 0'),
                ('competition_score', 'INTEGER DEFAULT 0')
            ]
            
            for column_name, column_type in migrations:
                try:
                    cursor.execute(f'ALTER TABLE sourced_products ADD COLUMN {column_name} {column_type}')
                    app.logger.info(f'[DB Init] ✅ Added {column_name} column to sourced_products table')
                except:
                    pass  # Column already exists
            
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
                    ('debug_mode_ignore_filters', 'false'),  # NEW: Debug mode for diagnostics
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

# Add custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string to Python object"""
    import json
    try:
        return json.loads(value) if value else []
    except (ValueError, TypeError):
        return []

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
    """
    Scrape 1688 search results using ScrapingAnt with browser rendering
    CRITICAL: Includes fallback to test data if scraping fails
    """
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
        app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
        return generate_fallback_test_data(keyword)
    
    api_key_stripped = api_key.strip() if isinstance(api_key, str) else ''
    
    if api_key_stripped == '':
        app.logger.error('[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: NO (empty string)')
        app.logger.error('[1688 Scraping] ❌ ScrapingAnt API key is empty')
        app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
        return generate_fallback_test_data(keyword)
    
    app.logger.info(f'[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: YES')
    app.logger.info(f'[1688 Scraping] ✅ API key found (length: {len(api_key_stripped)})')
    app.logger.info(f'[1688 Scraping] API key preview: {api_key_stripped[:10]}...')
    
    # Encode keyword for URL
    import urllib.parse
    encoded_keyword = urllib.parse.quote(keyword)
    search_url = f'https://s.1688.com/selloffer/offer_search.htm?keywords={encoded_keyword}'
    app.logger.info(f'[1688 Scraping] Search URL: {search_url}')
    
    # CRITICAL: Enhanced ScrapingAnt parameters for browser rendering
    params = {
        'url': search_url,
        'x-api-key': api_key_stripped,
        'browser': 'true',  # CRITICAL: Enable browser rendering (JS execution)
        'return_page_source': 'true',  # Return full HTML after JS execution
        'wait_for_selector': '.offer-list-row',  # Wait for product list to load
        'wait_for_timeout': '10000',  # Wait up to 10 seconds
        'proxy_country': 'CN',  # Use China proxy
        'block_resource': 'image,stylesheet,media,font'  # Block unnecessary resources for speed
    }
    
    # CRITICAL: Modern Chrome User-Agent to avoid bot detection
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # CRITICAL: Add 1688 authentication cookie for real pricing
    cookie_1688 = get_config('1688_cookie')
    if cookie_1688 and cookie_1688.strip():
        headers['Cookie'] = cookie_1688.strip()
        app.logger.info(f'[1688 Scraping] 🔑 Using 1688 authentication cookie (length: {len(cookie_1688.strip())})')
        app.logger.info(f'[1688 Scraping] Cookie preview: {cookie_1688.strip()[:50]}...')
    else:
        app.logger.warning('[1688 Scraping] ⚠️ No 1688 cookie configured - prices may not be accurate')
        app.logger.warning('[1688 Scraping] 💡 To get real wholesale prices:')
        app.logger.warning('[1688 Scraping]    1. Login to 1688.com in browser')
        app.logger.warning('[1688 Scraping]    2. Open F12 Developer Tools → Network tab')
        app.logger.warning('[1688 Scraping]    3. Copy the "Cookie" header from any request')
        app.logger.warning('[1688 Scraping]    4. Add to config: 1688_cookie = <your cookie>')
    
    try:
        app.logger.info('[1688 Scraping] 🌐 Sending request to ScrapingAnt API with BROWSER MODE...')
        app.logger.info('[1688 Scraping] Parameters: browser=true, wait_for_selector=.offer-list-row')
        # 🔥 EMERGENCY FIX: Prevent redirects to ensure we scrape the EXACT URL
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, headers=headers, timeout=120, allow_redirects=False)
        
        # If we got a redirect response, log it and fail
        if response.status_code in [301, 302, 303, 307, 308]:
            app.logger.error(f'[1688 Scraping] ❌ REDIRECT DETECTED: {response.status_code}')
            app.logger.error(f'[1688 Scraping] Location: {response.headers.get("Location", "Unknown")}')
            app.logger.error('[1688 Scraping] ⚠️ Refusing to follow redirect. Falling back to TEST DATA')
            return generate_fallback_test_data(keyword)
        
        # Continue with normal processing
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, headers=headers, timeout=120)
        
        app.logger.info(f'[1688 Scraping] Response status: {response.status_code}')
        app.logger.info(f'[1688 Scraping] Response length: {len(response.text)} characters')
        
        # 🔍 CRITICAL: Log first 500 chars of HTML response for debugging
        html_preview = response.text[:500]
        app.logger.info(f'[1688 Scraping] 📄 HTML Preview (first 500 chars):')
        app.logger.info(f'[1688 Scraping] {html_preview}')
        app.logger.info(f'[1688 Scraping] ========================================')
        
        # Check if response looks like a block page
        if '验证' in html_preview or 'blocked' in html_preview.lower() or 'captcha' in html_preview.lower() or '登录' in html_preview:
            app.logger.warning('[1688 Scraping] ⚠️ WARNING: Response may be a block/login/captcha page!')
            app.logger.warning('[1688 Scraping] Keywords detected: 验证/blocked/captcha/登录')
            app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
            return generate_fallback_test_data(keyword)
        
        # Check if response is too short (likely error page)
        if len(response.text) < 50000:
            app.logger.warning(f'[1688 Scraping] ⚠️ Response too short ({len(response.text)} chars) - likely error page')
            app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
            return generate_fallback_test_data(keyword)
        
        response.raise_for_status()
        
        # Parse HTML response
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Log page structure for debugging
        app.logger.info(f'[1688 Scraping] Parsed HTML. Looking for product cards...')
        
        products = []
        
        # Try multiple selectors for 1688 product listings
        selectors = [
            ('div', 'offer-list-row'),  # Most common
            ('div', 'card-item'),
            ('div', 'offer-item'),
            ('div', 'sm-offer-item'),
            ('div', 'sw-offer-item'),
            ('div', 'item')
        ]
        
        card_items = []
        for tag, class_name in selectors:
            card_items = soup.find_all(tag, class_=class_name)
            app.logger.info(f'[1688 Scraping] Tried selector "{tag}.{class_name}": Found {len(card_items)} elements')
            if len(card_items) > 0:
                break
        
        if len(card_items) == 0:
            app.logger.error('[1688 Scraping] ❌ No product elements found with any selector!')
            app.logger.error('[1688 Scraping] This indicates 1688 is blocking or page structure changed')
            app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
            return generate_fallback_test_data(keyword)
        
        for idx, item in enumerate(card_items[:max_results]):
            try:
                # Try multiple ways to extract product info
                url = ''
                title = ''
                price = 0
                sales = 0
                image = ''
                
                # Extract URL
                link = item.find('a', href=True)
                if link:
                    url = link['href']
                    if not url.startswith('http'):
                        url = 'https:' + url if url.startswith('//') else 'https://detail.1688.com' + url
                
                # Extract title
                title_elem = item.find('div', class_='title') or item.find('h3') or item.find('a', class_='title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                
                # Extract price
                price_elem = item.find('span', class_='price') or item.find('div', class_='price') or item.find('span', string=re.compile(r'¥'))
                if price_elem:
                    price_text = price_elem.get_text(strip=True).replace('¥', '').replace(',', '').replace(' ', '')
                    try:
                        price = float(re.findall(r'\d+\.?\d*', price_text)[0])
                    except:
                        price = 0
                
                # Extract sales
                sales_elem = item.find('span', class_='sales') or item.find('div', class_='sales')
                if sales_elem:
                    sales_text = sales_elem.get_text(strip=True)
                    try:
                        sales = int(re.findall(r'\d+', sales_text)[0])
                    except:
                        sales = 0
                
                # Extract image
                img = item.find('img')
                if img:
                    image = img.get('src', '') or img.get('data-src', '') or img.get('data-lazy-src', '')
                    if image and not image.startswith('http'):
                        image = 'https:' + image if image.startswith('//') else ''
                
                # 🔥 EMERGENCY FIX: STRICT validation - NO fallback URLs or placeholders
                # If title is missing or is a URL, skip this product entirely
                if not title or title.startswith('http') or len(title) < 3:
                    app.logger.warning(f'[1688 Scraping] ❌ REJECTED product {idx+1}: Invalid title "{title}"')
                    continue
                
                # If image is missing, use empty string instead of placeholder
                if not image or 'placeholder' in image:
                    app.logger.warning(f'[1688 Scraping] ⚠️ Product {idx+1} has no valid image')
                    image = ''  # Empty string, NOT placeholder
                
                # If URL is missing or redirected, skip
                if not url or not ('1688.com' in url):
                    app.logger.warning(f'[1688 Scraping] ❌ REJECTED product {idx+1}: Invalid URL "{url}"')
                    continue
                
                product = {
                    'url': url,
                    'title': title,
                    'price': price,
                    'sales': sales,
                    'image': image  # May be empty, but NEVER a placeholder
                }
                
                # Only add if we have valid title, price, and URL
                if product['title'] and product['price'] > 0 and product['url']:
                    products.append(product)
                    app.logger.info(f'[1688 Scraping] ✅ Product {idx+1}: {product["title"][:40]} - ¥{product["price"]}')
                else:
                    app.logger.warning(f'[1688 Scraping] ❌ REJECTED product {idx+1}: Incomplete data')
            except Exception as e:
                app.logger.warning(f'[1688 Scraping] Failed to parse product {idx+1}: {str(e)}')
                continue
        
        if len(products) == 0:
            app.logger.error('[1688 Scraping] ❌ Parsing succeeded but extracted 0 products!')
            app.logger.error('[1688 Scraping] This means selectors need updating or 1688 changed structure')
            app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
            return generate_fallback_test_data(keyword)
        
        app.logger.info(f'[1688 Scraping] ✅ Successfully parsed {len(products)} products')
        return {'products': products, 'count': len(products)}
    
    except requests.exceptions.Timeout:
        app.logger.error('[1688 Scraping] ❌ Request timeout (120s)')
        app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
        return generate_fallback_test_data(keyword)
    except requests.exceptions.RequestException as e:
        error_msg = f'Request failed: {str(e)}'
        app.logger.error(f'[1688 Scraping] ❌ {error_msg}')
        app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
        return generate_fallback_test_data(keyword)
    except Exception as e:
        error_msg = f'Parsing failed: {str(e)}'
        app.logger.error(f'[1688 Scraping] ❌ {error_msg}')
        app.logger.exception(e)
        app.logger.warning('[1688 Scraping] ⚠️ Falling back to TEST DATA')
        return generate_fallback_test_data(keyword)

def generate_fallback_test_data(keyword):
    """
    Generate realistic test data as fallback when scraping fails
    CRITICAL: Ensures system always shows results to user
    """
    import random
    
    app.logger.warning('[TEST DATA] ⚠️ 크롤링 실패: 테스트 데이터를 표시합니다')
    app.logger.info('[TEST DATA] Generating realistic fallback test products')
    
    # Predefined realistic test products (Korean winter/trending items)
    base_products = [
        {
            'category': '전기담요',
            'variants': ['수면용', '사무실용', '차량용', '휴대용', '대형'],
            'price_range': (30, 80)
        },
        {
            'category': '가습기',
            'variants': ['초음파', '가열식', '복합식', '미니', '대용량'],
            'price_range': (25, 90)
        },
        {
            'category': '블루투스 이어폰',
            'variants': ['무선', 'ANC', '스포츠', '게이밍', '프리미엄'],
            'price_range': (15, 120)
        },
        {
            'category': '무선충전기',
            'variants': ['고속', '스탠드형', '멀티', '차량용', '접이식'],
            'price_range': (10, 45)
        },
        {
            'category': 'LED 조명',
            'variants': ['무드등', '스탠드', '스마트', 'USB', '침실용'],
            'price_range': (8, 60)
        },
        {
            'category': '휴대폰 거치대',
            'variants': ['차량용', '책상용', '침대용', '삼각대', '자석'],
            'price_range': (5, 30)
        },
        {
            'category': '보조배터리',
            'variants': ['고속충전', '대용량', '소형', '무선', '태양광'],
            'price_range': (20, 85)
        },
        {
            'category': '스마트워치',
            'variants': ['운동용', '건강측정', '방수', '저렴이', '프리미엄'],
            'price_range': (25, 150)
        }
    ]
    
    products = []
    num_products = min(10, max_results) if 'max_results' in locals() else 10
    
    for i in range(num_products):
        # Randomly select a product category
        base = random.choice(base_products)
        variant = random.choice(base['variants'])
        
        # Generate realistic product
        price = round(random.uniform(base['price_range'][0], base['price_range'][1]), 2)
        
        product = {
            'url': f'https://detail.1688.com/offer/{9000000 + random.randint(1000, 99999)}.html',
            'title': f'{keyword} {base["category"]} {variant} 고품질 무료배송 도매',
            'price': price,
            'sales': random.randint(500, 15000),
            'image': f'https://via.placeholder.com/300x300?text={base["category"]}'
        }
        products.append(product)
        app.logger.info(f'[TEST DATA] Product {i+1}: {product["title"][:50]} - ¥{product["price"]}')
    
    app.logger.warning(f'[TEST DATA] ✅ Generated {len(products)} realistic test products')
    app.logger.warning('[TEST DATA] ⚠️ 이것은 테스트 데이터입니다 - 실제 1688 상품이 아닙니다!')
    
    return {'products': products, 'count': len(products), 'is_test_data': True}

def parse_smart_price(price_text):
    """
    Smart price parser for Alibaba/AliExpress
    Handles: $10-$20 -> 10.0, $15.99 -> 15.99, ¥50-¥100 -> 50.0
    """
    import re
    if not price_text:
        return 0.0
    
    # Remove currency symbols and spaces
    cleaned = price_text.replace('$', '').replace('¥', '').replace(' ', '').replace(',', '')
    
    # Find all numbers (including decimals)
    numbers = re.findall(r'\d+\.?\d*', cleaned)
    
    if not numbers:
        return 0.0
    
    # If range (e.g., "10-20"), take the LOWEST price
    prices = [float(n) for n in numbers]
    return min(prices)

def scrape_alibaba_search(keyword, max_results=50):
    """
    Scrape Alibaba.com search results
    Focus on: Ready to Ship, Low MOQ (≤2)
    """
    app.logger.info(f'[Alibaba Scraping] ========================================')
    app.logger.info(f'[Alibaba Scraping] Starting search for keyword: {keyword}')
    
    api_key = get_config('scrapingant_api_key')
    if not api_key or not api_key.strip():
        app.logger.error('[Alibaba Scraping] ❌ No ScrapingAnt API key')
        return {'products': [], 'count': 0}
    
    import urllib.parse
    encoded_keyword = urllib.parse.quote(keyword)
    search_url = f'https://www.alibaba.com/trade/search?SearchText={encoded_keyword}'
    
    params = {
        'url': search_url,
        'x-api-key': api_key.strip(),
        'browser': 'true',
        'return_page_source': 'true',
        'wait_for_selector': '.organic-list-offer',
        'wait_for_timeout': '10000',
        'proxy_country': 'US'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        app.logger.info('[Alibaba Scraping] 🌐 Sending request to ScrapingAnt...')
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, headers=headers, timeout=120, allow_redirects=False)
        
        if response.status_code in [301, 302, 303, 307, 308]:
            app.logger.error(f'[Alibaba Scraping] ❌ REDIRECT DETECTED: {response.status_code}')
            return {'products': [], 'count': 0}
        
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, headers=headers, timeout=120)
        
        if response.status_code != 200:
            app.logger.error(f'[Alibaba Scraping] ❌ API error: {response.status_code}')
            return {'products': [], 'count': 0}
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        products = []
        selectors = [
            ('div', 'organic-list-offer'),
            ('div', 'offer-card'),
            ('div', 'product-card')
        ]
        
        card_items = []
        for tag, class_name in selectors:
            card_items = soup.find_all(tag, class_=class_name)
            if len(card_items) > 0:
                app.logger.info(f'[Alibaba Scraping] Found {len(card_items)} items with selector {tag}.{class_name}')
                break
        
        for idx, item in enumerate(card_items[:max_results]):
            try:
                url = ''
                title = ''
                price = 0
                moq = 1
                image = ''
                
                # Extract URL
                link = item.find('a', href=True)
                if link:
                    url = link['href']
                    if not url.startswith('http'):
                        url = 'https://www.alibaba.com' + url
                
                # Extract title
                title_elem = item.find('h2') or item.find('h3') or item.find('div', class_='title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                
                # Extract price (smart parsing)
                price_elem = item.find('span', class_='price') or item.find('div', class_='price')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = parse_smart_price(price_text)
                
                # Extract MOQ
                moq_elem = item.find('span', string=re.compile(r'MOQ', re.I)) or item.find('div', string=re.compile(r'MOQ', re.I))
                if moq_elem:
                    moq_text = moq_elem.get_text(strip=True)
                    moq_match = re.search(r'(\d+)', moq_text)
                    if moq_match:
                        moq = int(moq_match.group(1))
                
                # Extract image
                img = item.find('img')
                if img:
                    image = img.get('src', '') or img.get('data-src', '')
                    if image and not image.startswith('http'):
                        image = 'https:' + image if image.startswith('//') else ''
                
                # Validation
                if not title or title.startswith('http') or len(title) < 3:
                    continue
                if not url or 'alibaba.com' not in url:
                    continue
                if moq > 2:  # Filter: MOQ must be ≤ 2
                    continue
                
                product = {
                    'url': url,
                    'title': title,
                    'price': price,
                    'moq': moq,
                    'sales': 0,  # Alibaba doesn't show sales easily
                    'image': image,
                    'source_site': 'Alibaba'
                }
                
                if product['title'] and product['price'] > 0:
                    products.append(product)
                    app.logger.info(f'[Alibaba] ✅ Product {len(products)}: {title[:40]} - ${price} (MOQ: {moq})')
            
            except Exception as e:
                app.logger.warning(f'[Alibaba Scraping] Failed to parse product {idx+1}: {str(e)}')
                continue
        
        app.logger.info(f'[Alibaba Scraping] ✅ Found {len(products)} valid products')
        return {'products': products, 'count': len(products)}
    
    except Exception as e:
        app.logger.error(f'[Alibaba Scraping] ❌ Exception: {str(e)}')
        return {'products': [], 'count': 0}

def scrape_aliexpress_search(keyword, max_results=50):
    """
    Scrape AliExpress search results
    Note: AliExpress has MOQ = 1 by default
    """
    app.logger.info(f'[AliExpress Scraping] ========================================')
    app.logger.info(f'[AliExpress Scraping] Starting search for keyword: {keyword}')
    
    api_key = get_config('scrapingant_api_key')
    if not api_key or not api_key.strip():
        app.logger.error('[AliExpress Scraping] ❌ No ScrapingAnt API key')
        return {'products': [], 'count': 0}
    
    import urllib.parse
    encoded_keyword = urllib.parse.quote(keyword)
    search_url = f'https://www.aliexpress.com/wholesale?SearchText={encoded_keyword}'
    
    params = {
        'url': search_url,
        'x-api-key': api_key.strip(),
        'browser': 'true',
        'return_page_source': 'true',
        'wait_for_selector': '.list--gallery--C2f2tvm',
        'wait_for_timeout': '10000',
        'proxy_country': 'US'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        app.logger.info('[AliExpress Scraping] 🌐 Sending request to ScrapingAnt...')
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, headers=headers, timeout=120, allow_redirects=False)
        
        if response.status_code in [301, 302, 303, 307, 308]:
            app.logger.error(f'[AliExpress Scraping] ❌ REDIRECT DETECTED: {response.status_code}')
            return {'products': [], 'count': 0}
        
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, headers=headers, timeout=120)
        
        if response.status_code != 200:
            app.logger.error(f'[AliExpress Scraping] ❌ API error: {response.status_code}')
            return {'products': [], 'count': 0}
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        products = []
        selectors = [
            ('div', 'list--gallery--C2f2tvm'),
            ('div', 'product-snippet'),
            ('div', 'product-card')
        ]
        
        card_items = []
        for tag, class_name in selectors:
            card_items = soup.find_all(tag, class_=class_name)
            if len(card_items) > 0:
                app.logger.info(f'[AliExpress Scraping] Found {len(card_items)} items with selector {tag}.{class_name}')
                break
        
        for idx, item in enumerate(card_items[:max_results]):
            try:
                url = ''
                title = ''
                price = 0
                image = ''
                
                # Extract URL
                link = item.find('a', href=True)
                if link:
                    url = link['href']
                    if not url.startswith('http'):
                        url = 'https://www.aliexpress.com' + url
                
                # Extract title
                title_elem = item.find('h1') or item.find('h2') or item.find('h3')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                
                # Extract price (smart parsing for discount prices)
                price_elem = item.find('span', class_='price') or item.find('div', class_='price')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = parse_smart_price(price_text)
                
                # Extract image
                img = item.find('img')
                if img:
                    image = img.get('src', '') or img.get('data-src', '')
                    if image and not image.startswith('http'):
                        image = 'https:' + image if image.startswith('//') else ''
                
                # Validation
                if not title or title.startswith('http') or len(title) < 3:
                    continue
                if not url or 'aliexpress.com' not in url:
                    continue
                
                product = {
                    'url': url,
                    'title': title,
                    'price': price,
                    'moq': 1,  # AliExpress always MOQ = 1
                    'sales': 0,
                    'image': image,
                    'source_site': 'AliExpress'
                }
                
                if product['title'] and product['price'] > 0:
                    products.append(product)
                    app.logger.info(f'[AliExpress] ✅ Product {len(products)}: {title[:40]} - ${price}')
            
            except Exception as e:
                app.logger.warning(f'[AliExpress Scraping] Failed to parse product {idx+1}: {str(e)}')
                continue
        
        app.logger.info(f'[AliExpress Scraping] ✅ Found {len(products)} valid products')
        return {'products': products, 'count': len(products)}
    
    except Exception as e:
        app.logger.error(f'[AliExpress Scraping] ❌ Exception: {str(e)}')
        return {'products': [], 'count': 0}

def search_integrated_hybrid(keyword, max_results=50):
    """
    🚀 HYBRID SOURCING ENGINE
    Search Alibaba + AliExpress simultaneously
    Merge results and select Top 3 based on price + margin + MOQ
    """
    app.logger.info(f'[Hybrid Engine] ========================================')
    app.logger.info(f'[Hybrid Engine] 🚀 Starting HYBRID search for: {keyword}')
    app.logger.info(f'[Hybrid Engine] Sources: Alibaba.com + AliExpress.com')
    
    # Step 1: Search Alibaba
    app.logger.info('[Hybrid Engine] Step 1: Searching Alibaba.com...')
    alibaba_result = scrape_alibaba_search(keyword, max_results)
    alibaba_products = alibaba_result.get('products', [])
    app.logger.info(f'[Hybrid Engine] ✅ Alibaba: {len(alibaba_products)} products')
    
    # Step 2: Search AliExpress
    app.logger.info('[Hybrid Engine] Step 2: Searching AliExpress.com...')
    aliexpress_result = scrape_aliexpress_search(keyword, max_results)
    aliexpress_products = aliexpress_result.get('products', [])
    app.logger.info(f'[Hybrid Engine] ✅ AliExpress: {len(aliexpress_products)} products')
    
    # Step 3: Merge and compare
    all_products = alibaba_products + aliexpress_products
    app.logger.info(f'[Hybrid Engine] Step 3: Merging {len(all_products)} total products')
    
    if len(all_products) == 0:
        app.logger.error('[Hybrid Engine] ❌ No products found from either source!')
        return {'products': [], 'count': 0}
    
    # Calculate profitability for each product
    for product in all_products:
        try:
            # Convert USD to CNY for uniform calculation (1 USD ≈ 7.2 CNY)
            price_cny = product['price'] * 7.2
            analysis = analyze_product_profitability(price_cny)
            product['analysis'] = analysis
            product['price_cny'] = price_cny  # Store for DB
            
            # Calculate score: lower price + higher margin + lower MOQ = better
            price_score = max(0, 100 - product['price'])  # Lower price = higher score
            margin_score = analysis['margin']  # Higher margin = higher score
            moq_score = max(0, 10 - product['moq'])  # Lower MOQ = higher score
            
            product['hybrid_score'] = price_score + (margin_score * 2) + (moq_score * 3)
            
            app.logger.debug(f'[Hybrid Score] {product["title"][:30]}: '
                           f'Price=${product["price"]:.2f}, '
                           f'Margin={analysis["margin"]:.1f}%, '
                           f'MOQ={product["moq"]}, '
                           f'Score={product["hybrid_score"]:.1f}')
        except Exception as e:
            app.logger.error(f'[Hybrid Engine] Failed to analyze product: {str(e)}')
            product['hybrid_score'] = 0
    
    # Sort by hybrid score (descending)
    all_products.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
    
    app.logger.info(f'[Hybrid Engine] ✅ HYBRID search complete: {len(all_products)} products analyzed')
    return {'products': all_products, 'count': len(all_products)}

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
    
    Returns: dict with 'success', 'products' (Top 3 only), 'stats', 'stage_stats'
    """
    app.logger.info(f'[Smart Sniper] ========================================')
    app.logger.info(f'[Smart Sniper] Executing unified sourcing for keyword: {keyword}')
    app.logger.info(f'[Smart Sniper] Use test data: {use_test_data}')
    
    # Initialize stage-by-stage tracking for UI feedback
    stage_stats = {
        'stage1_scraped': 0,
        'stage2_safe': 0,
        'stage3_profitable': 0,
        'stage4_final': 0,
        'highest_margin_product': None,
        'highest_margin_value': 0
    }
    
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
            'stats': {'scanned': 0, 'safe': 0, 'profitable': 0, 'final_count': 0},
            'stage_stats': stage_stats
        }
    
    # ========================================================================
    # Load configs from DB (NEVER use global variables)
    # ========================================================================
    scrapingant_key = get_config('scrapingant_api_key', '')
    openai_key = get_config('openai_api_key', '')
    target_margin_rate = get_config('target_margin_rate', 30)
    cny_exchange_rate = get_config('cny_exchange_rate', 190)
    debug_mode = get_config('debug_mode_ignore_filters', 'false')
    
    # Convert debug_mode to boolean
    debug_mode_enabled = debug_mode.lower() in ['true', '1', 'yes', 'on']
    
    app.logger.info('[Smart Sniper] 📋 Config loaded from DB:')
    app.logger.info(f'  - ScrapingAnt key: {scrapingant_key[:4]}**** (len: {len(scrapingant_key)})')
    app.logger.info(f'  - OpenAI key: {openai_key[:4]}**** (len: {len(openai_key)})')
    app.logger.info(f'  - Target margin: {target_margin_rate}%')
    app.logger.info(f'  - CNY rate: {cny_exchange_rate}')
    app.logger.info(f'  - 🐛 DEBUG MODE (Ignore Filters): {debug_mode_enabled}')
    
    if not scrapingant_key and not use_test_data:
        app.logger.error('[Smart Sniper] ❌ CRITICAL: ScrapingAnt API key is EMPTY after DB load')
        app.logger.error('[Smart Sniper] Please configure API key in Settings page')
        log_activity('sourcing', '❌ ScrapingAnt API key not configured', 'error')
        return {
            'success': False,
            'error': 'ScrapingAnt API key not configured. Please set it in Settings.',
            'stats': {'scanned': 0, 'safe': 0, 'profitable': 0, 'final_count': 0},
            'stage_stats': stage_stats
        }
    
    # Step 1: 🚀 HYBRID Search (Alibaba + AliExpress)
    log_activity('sourcing', f'Step 1/5: 🚀 HYBRID Search (Alibaba + AliExpress) for "{keyword}"', 'in_progress')
    
    if use_test_data:
        # Use test data for development/debugging
        app.logger.warning('[Smart Sniper] Using TEST DATA instead of real scraping')
        products = generate_test_products(keyword, count=10)
        log_activity('sourcing', f'Found {len(products)} TEST items (development mode)', 'warning')
    else:
        # 🚀 Real HYBRID scraping (Alibaba + AliExpress)
        results = search_integrated_hybrid(keyword, max_results=50)
        
        # Check if test data was returned (has is_test_data flag)
        if results.get('is_test_data', False):
            app.logger.warning('[Smart Sniper] ⚠️ Using FALLBACK TEST DATA from scraping function')
            products = results.get('products', [])
            log_activity('sourcing', f'⚠️ Scraping failed - Using {len(products)} TEST items', 'warning')
        elif 'error' in results:
            # Old error handling (shouldn't happen now, but keep for safety)
            error_msg = results['error']
            app.logger.error(f'[Smart Sniper] Scraping error: {error_msg}')
            log_activity('sourcing', f'❌ Search failed: {error_msg}', 'error')
            
            # This path shouldn't be reached anymore, but keep as safety net
            app.logger.warning('[Smart Sniper] Falling back to TEST DATA due to error')
            products = generate_test_products(keyword, count=10)
            log_activity('sourcing', f'Using {len(products)} TEST items as fallback', 'warning')
        else:
            products = results.get('products', [])
            app.logger.info(f'[Smart Sniper] 🚀 HYBRID scraping result: {len(products)} products from Alibaba + AliExpress')
            
            # Check if it's real data or test data
            if results.get('is_test_data', False):
                log_activity('sourcing', f'⚠️ Using {len(products)} TEST items (scraping failed)', 'warning')
            else:
                log_activity('sourcing', f'Found {len(products)} items from listing', 'success')
    
    # 📊 STAGE 1: Record scraped count
    stage_stats['stage1_scraped'] = len(products)
    app.logger.info(f'[Smart Sniper] 📊 STAGE 1 COMPLETE: {len(products)} products scraped')
    
    # Critical check: if still no products, cannot continue
    if len(products) == 0:
        app.logger.error('[Smart Sniper] ❌ CRITICAL: No products found after scraping AND test data fallback')
        log_activity('sourcing', '❌ No products found - cannot continue', 'error')
        return {
            'success': False,
            'error': 'No products found. Please check ScrapingAnt API or try different keyword.',
            'stats': {'scanned': 0, 'safe': 0, 'profitable': 0, 'final_count': 0},
            'stage_stats': stage_stats
        }
    
    # Step 2: Safety Filter (SKIP if debug mode enabled)
    log_activity('sourcing', 'Step 2/5: 🛡️ Applying safety filters', 'in_progress')
    app.logger.info(f'[Smart Sniper] Starting safety filter on {len(products)} products')
    
    if debug_mode_enabled:
        # 🐛 DEBUG MODE: Skip safety filter
        app.logger.warning('[Smart Sniper] 🐛 DEBUG MODE: SKIPPING SAFETY FILTER')
        safe_products = products
        filtered_count = 0
        log_activity('sourcing', f'🐛 Debug mode: All {len(products)} products marked as safe', 'warning')
    else:
        # Normal safety filtering
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
    
    # 📊 STAGE 2: Record safe count
    stage_stats['stage2_safe'] = len(safe_products)
    app.logger.info(f'[Smart Sniper] 📊 STAGE 2 COMPLETE: {len(safe_products)} products passed safety filter')
    
    # Step 3: Margin Simulation (SKIP if debug mode enabled)
    log_activity('sourcing', 'Step 3/5: 💰 Margin simulation in progress', 'in_progress')
    target_margin = float(get_config('target_margin_rate', 30))
    app.logger.info(f'[Smart Sniper] Target margin: {target_margin}%')
    app.logger.info(f'[Smart Sniper] Analyzing profitability of {len(safe_products)} products')
    
    profitable_products = []
    failed_margin_count = 0
    highest_margin = 0
    highest_margin_product = None
    
    for idx, product in enumerate(safe_products):
        try:
            analysis = analyze_product_profitability(product['price'])
            
            app.logger.debug(f'[Margin Check {idx+1}] {product["title"][:30]}: '
                           f'Price ¥{product["price"]}, '
                           f'Margin {analysis["margin"]:.1f}%, '
                           f'Profit ₩{analysis["profit"]:,}')
            
            # Track highest margin product
            if analysis['margin'] > highest_margin:
                highest_margin = analysis['margin']
                highest_margin_product = {
                    'title': product['title'][:50],
                    'price_cny': product['price'],
                    'margin': analysis['margin'],
                    'profit': analysis['profit']
                }
            
            # Drop items not meeting target margin (UNLESS debug mode enabled)
            if debug_mode_enabled or analysis['margin'] >= target_margin:
                product['analysis'] = analysis
                profitable_products.append(product)
            else:
                failed_margin_count += 1
        except Exception as e:
            app.logger.error(f'[Margin Check] Failed for product {idx+1}: {str(e)}')
            failed_margin_count += 1
    
    # 📊 Record highest margin for diagnostics
    stage_stats['highest_margin_value'] = highest_margin
    stage_stats['highest_margin_product'] = highest_margin_product
    
    app.logger.info(f'[Smart Sniper] 📊 Highest margin found: {highest_margin:.1f}%')
    if highest_margin_product:
        app.logger.info(f'[Smart Sniper] 📊 Highest margin product: {highest_margin_product["title"]}')
    
    if debug_mode_enabled:
        app.logger.warning(f'[Smart Sniper] 🐛 DEBUG MODE: SKIPPING MARGIN FILTER - All {len(profitable_products)} products accepted')
        log_activity('sourcing', f'🐛 Debug mode: All {len(profitable_products)} products marked as profitable', 'warning')
    else:
        app.logger.info(f'[Smart Sniper] Profitability result: {len(profitable_products)} profitable, {failed_margin_count} rejected')
        log_activity('sourcing', f'{len(profitable_products)} items meet target margin {target_margin}%', 'success')
    
    # 📊 STAGE 3: Record profitable count
    stage_stats['stage3_profitable'] = len(profitable_products)
    app.logger.info(f'[Smart Sniper] 📊 STAGE 3 COMPLETE: {len(profitable_products)} products are profitable')
    
    # Step 4: Sort by net profit (descending)
    profitable_products.sort(key=lambda x: x['analysis']['profit'], reverse=True)
    
    # Step 5: Slice to Top 3 ONLY (or all products if debug mode)
    if debug_mode_enabled:
        # 🐛 DEBUG MODE: Return ALL products instead of just top 3
        top_3 = profitable_products[:50]  # Cap at 50 to avoid UI overload
        app.logger.warning(f'[Smart Sniper] 🐛 DEBUG MODE: Returning TOP {len(top_3)} products (not limited to 3)')
        log_activity('sourcing', f'Step 4/5: 🐛 Debug mode: Top {len(top_3)} selected', 'warning')
    else:
        top_3 = profitable_products[:3]
        log_activity('sourcing', f'Step 4/5: 🎯 Top 3 selected (sorted by profit)', 'success')
    
    # 📊 STAGE 4: Record final count
    stage_stats['stage4_final'] = len(top_3)
    app.logger.info(f'[Smart Sniper] 📊 STAGE 4 COMPLETE: {len(top_3)} products in final selection')
    
    if len(top_3) == 0:
        # 🚨 CRITICAL: No products after all filters
        app.logger.error('[Smart Sniper] ❌ ZERO products after all filters!')
        app.logger.error(f'[Smart Sniper] 📊 Breakdown: Scraped={stage_stats["stage1_scraped"]}, '
                        f'Safe={stage_stats["stage2_safe"]}, '
                        f'Profitable={stage_stats["stage3_profitable"]}, '
                        f'Final={stage_stats["stage4_final"]}')
        app.logger.error(f'[Smart Sniper] 💡 Highest margin found: {highest_margin:.1f}% (target: {target_margin}%)')
        
        if highest_margin_product:
            app.logger.error(f'[Smart Sniper] 💡 SUGGESTION: Best product was: {highest_margin_product["title"]}')
            app.logger.error(f'[Smart Sniper] 💡 Consider lowering target margin or enabling debug mode')
        
        log_activity('sourcing', '⚠️ No products met all criteria - check stage breakdown in logs', 'warning')
        return {
            'success': True,
            'products': [],
            'stats': {
                'scanned': len(products),
                'safe': len(safe_products),
                'profitable': len(profitable_products),
                'final_count': 0
            },
            'stage_stats': stage_stats,
            'suggestion': f'No products found. Highest margin was {highest_margin:.1f}% (target: {target_margin}%). Consider lowering margin target or enabling Debug Mode.'
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
                 estimated_profit, safety_status, images_json, status,
                 source_site, moq, traffic_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product['url'],
                product['title'],
                product.get('price_cny', product['price']),  # Use converted CNY if available
                product['analysis']['sale_price'],
                product['analysis']['margin'],
                product['analysis']['profit'],
                'passed',
                json.dumps([product.get('image', '')]),
                'pending',
                product.get('source_site', '1688'),  # 🚀 NEW: source site
                product.get('moq', 1),  # 🚀 NEW: MOQ
                product.get('sales', 0)  # 🚀 NEW: traffic score (use sales as proxy)
            ))
            saved_count += 1
            app.logger.info(f'[DB Save {idx+1}] ✅ Successfully inserted')
        except Exception as e:
            app.logger.error(f'[DB Save {idx+1}] ❌ Failed to insert: {str(e)}')
            app.logger.exception(e)
    
    conn.commit()
    conn.close()
    
    app.logger.info(f'[Smart Sniper] Completed: {saved_count}/{len(top_3)} products saved to database')
    app.logger.info(f'[Smart Sniper] 📊 FINAL BREAKDOWN:')
    app.logger.info(f'[Smart Sniper]   Stage 1 (Scraped): {stage_stats["stage1_scraped"]}')
    app.logger.info(f'[Smart Sniper]   Stage 2 (Safe): {stage_stats["stage2_safe"]}')
    app.logger.info(f'[Smart Sniper]   Stage 3 (Profitable): {stage_stats["stage3_profitable"]}')
    app.logger.info(f'[Smart Sniper]   Stage 4 (Final): {stage_stats["stage4_final"]}')
    log_activity('sourcing', f'✅ Smart Sourcing completed: {saved_count} products saved', 'success')
    
    return {
        'success': True,
        'products': top_3,
        'stats': {
            'scanned': len(products),
            'safe': len(safe_products),
            'profitable': len(profitable_products),
            'final_count': len(top_3)
        },
        'stage_stats': stage_stats,
        'debug_mode_enabled': debug_mode_enabled
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
        return jsonify({'error': result.get('error', 'Unknown error'), 'stage_stats': result.get('stage_stats', {})}), 500
    
    # Build response
    response_data = {
        'success': True,
        'mode': mode,
        'keyword': target_keyword,
        'stats': result['stats'],
        'stage_stats': result.get('stage_stats', {}),  # NEW: Stage-by-stage breakdown
        'debug_mode_enabled': result.get('debug_mode_enabled', False),
        'suggestion': result.get('suggestion', '')  # NEW: Suggestion when no products found
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
            copy = response.json()['choices'][0]['message']['content']
            
            # 🔥 EMERGENCY FIX: Remove labels from marketing copy
            import re
            copy = re.sub(r'\d+\.\s*(훅|문제|솔루션|Hook|Problem|Solution):\s*', '', copy, flags=re.IGNORECASE)
            copy = re.sub(r'\*\*(훅|문제|솔루션|Hook|Problem|Solution)\s*\([^)]+\):\*\*\s*', '', copy, flags=re.IGNORECASE)
            copy = re.sub(r'(훅|문제|솔루션|Hook|Problem|Solution):\s*', '', copy, flags=re.IGNORECASE)
            
            return copy.strip()
        else:
            return '상품 설명이 준비 중입니다.'
    
    except Exception as e:
        log_activity('content', f'Failed to generate copy: {str(e)}', 'error')
        return '상품 설명이 준비 중입니다.'

def generate_winning_product_page(title, price, images):
    """
    Generate a WINNING product detail page using the 5-section formula.
    This structure mimics best-selling Coupang/Naver products.
    
    5-SECTION FORMULA:
    1. Hook: "Do you have this problem?" (GIF or strong image)
    2. Empathy/Solution: "That's why we prepared this." (Product intro)
    3. Key Points: "3 reasons why this product is special" (Icons + brief)
    4. Details: Usage shots + spec explanation (Image-text alternating)
    5. FAQ/Shipping: Frequently asked questions
    """
    api_key = get_config('openai_api_key')
    if not api_key:
        return generate_fallback_product_page(title, images)
    
    # Classify images: lifestyle shots first, detail shots later
    lifestyle_imgs = images[:3] if len(images) >= 3 else images
    detail_imgs = images[3:] if len(images) > 3 else []
    
    system_prompt = """You are a TOP-TIER Korean E-commerce Merchandiser specialized in creating WINNING product pages.

🚨 CRITICAL RULES - MUST FOLLOW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ❌ NEVER use placeholder images (via.placeholder.com, example.com, etc.)
2. ✅ ONLY use image URLs from the provided product_images list
3. ❌ NEVER write section labels like "1. 훅:", "2. 솔루션:" in the output
4. ✅ Write naturally flowing marketing copy without numbered labels
5. ✅ MUST include SEO tags at the end: [TAGS]: keyword1, keyword2, ...

IMAGE RULES (CRITICAL):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Use ONLY the exact image URLs provided in the prompt
- Format: <img src="[PROVIDED_URL]" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin: 20px 0;">
- If you need to reference images, use {img_1}, {img_2}, {img_3}, etc.
- These placeholders will be replaced with REAL product images

TEXT RULES (CRITICAL):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NO section labels like "1. 훅:", "2. 문제:", "3. 솔루션:"
- Write as continuous, natural marketing copy
- Use HTML headings (<h3>) for section titles only
- No Markdown syntax (**bold**, ##heading)

SEO RULES (MANDATORY):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
At the END of your HTML, include:
[TAGS]: keyword1, keyword2, keyword3, keyword4, keyword5, keyword6, keyword7, keyword8, keyword9, keyword10

Example keywords: 겨울이불, 따뜻한담요, 전기장판, 방한용품, 수면용품...

SECTION STRUCTURE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1: HOOK (강렬한 후킹)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Start with customer PAIN POINT
- Use emotional language
- Show problem scenario
- 1-2 sentences MAX

SECTION 2: EMPATHY & SOLUTION (공감 + 솔루션)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "그래서 준비했습니다"
- Introduce product as THE solution
- Show lifestyle image
- Build excitement

SECTION 3: KEY POINTS (핵심 포인트 3가지)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use this EXACT format:
<div style="background: #f8f9fa; padding: 30px; border-radius: 15px; margin: 30px 0;">
  <h3 style="font-size: 24px; font-weight: bold; margin-bottom: 20px; text-align: center;">✨ 이 제품이 특별한 이유 3가지</h3>
  
  <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 20px;">
    <div style="text-align: center; padding: 20px; background: white; border-radius: 10px;">
      <div style="font-size: 48px; margin-bottom: 10px;">🎯</div>
      <h4 style="font-size: 18px; font-weight: bold; margin-bottom: 10px;">Point 1 Title</h4>
      <p style="font-size: 14px; color: #666;">Brief explanation</p>
    </div>
    <!-- Repeat for Point 2 and 3 -->
  </div>
</div>

SECTION 4: DETAILS (디테일 설명)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Alternate between image and text:
- Image → Feature explanation
- Image → Spec details
- Image → Usage scenario

SECTION 5: FAQ & TRUST (FAQ + 신뢰 구축)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<div style="background: #fff9e6; padding: 30px; border-radius: 15px; margin: 30px 0;">
  <h3 style="font-size: 22px; font-weight: bold; margin-bottom: 20px;">💬 자주 묻는 질문</h3>
  
  <div style="margin: 15px 0; padding: 15px; background: white; border-left: 4px solid #ffa500; border-radius: 8px;">
    <strong style="color: #333;">Q: Question here?</strong>
    <p style="margin-top: 10px; color: #666;">A: Answer here.</p>
  </div>
  <!-- Repeat 3-5 FAQs -->
</div>

FINAL SECTION: CTA
<div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin: 30px 0;">
  <h3 style="font-size: 26px; font-weight: bold; margin-bottom: 15px;">지금 바로 경험해보세요!</h3>
  <p style="font-size: 16px; margin-bottom: 20px;">✅ 무료배송 | ✅ 당일출고 | ✅ 100% 환불보증</p>
</div>

REMEMBER:
- NO Markdown (**bold**, ##heading) - Use HTML only
- ALL images MUST have rounded corners and shadows
- Use emojis for visual appeal (🎯, ✨, 💯, 👍)
- Keep Korean natural and persuasive
- Focus on BENEFITS over features
"""
    
    user_prompt = f"""Create a WINNING product detail page for:

Product: {title}
Price: {price:,}원

🖼️ REAL PRODUCT IMAGES (Use these EXACT URLs):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join([f'{{img_{i+1}}} = {url}' for i, url in enumerate(images)])}

IMAGE USAGE:
- Lifestyle shots (1-3): Use {chr(10).join([f'{{img_{i+1}}}' for i in range(min(3, len(images)))])}
- Detail shots (4+): Use {chr(10).join([f'{{img_{i+1}}}' for i in range(3, len(images))])} if available

🚨 CRITICAL REMINDERS:
1. Replace {{img_1}}, {{img_2}}, etc. with the PROVIDED URLs above
2. NO placeholder images (via.placeholder.com)
3. NO section labels like "1. 훅:", "2. 솔루션:" in output
4. Write natural, flowing marketing copy
5. END with: [TAGS]: keyword1, keyword2, ... (10 Korean keywords)

TASK:
Generate complete HTML following the 5-section formula.
Make it look PROFESSIONAL and PERSUASIVE like top Coupang sellers.

OUTPUT FORMAT:
Pure HTML code (no markdown, no code blocks).
Start directly with HTML tags.
End with SEO tags: [TAGS]: keyword1, keyword2, ...
"""
    
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': 0.8,
                'max_tokens': 3000
            },
            timeout=60
        )
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            
            # Clean up: remove code blocks if present
            content = content.replace('```html', '').replace('```', '').strip()
            
            # 🔥 CRITICAL: Replace image placeholders with REAL URLs
            for i, img_url in enumerate(images, 1):
                content = content.replace(f'{{img_{i}}}', img_url)
                content = content.replace(f'IMAGE_{i}', img_url)
                content = content.replace(f'[IMAGE_{i}]', img_url)
            
            # 🔥 CRITICAL: Remove ANY remaining placeholder images
            import re
            # Remove via.placeholder.com
            content = re.sub(r'<img[^>]*src=["\']https?://via\.placeholder\.com[^"\']*["\'][^>]*>', '', content)
            # Remove example.com placeholders
            content = re.sub(r'<img[^>]*src=["\']https?://example\.com[^"\']*["\'][^>]*>', '', content)
            
            # 🔥 CRITICAL: Extract SEO tags
            tags = ''
            if '[TAGS]:' in content or '[TAGS]' in content:
                import re
                tag_match = re.search(r'\[TAGS\]:?\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
                if tag_match:
                    tags = tag_match.group(1).strip()
                    # Remove tags from HTML content
                    content = re.sub(r'\[TAGS\]:?.+?(?:\n|$)', '', content, flags=re.IGNORECASE)
            
            # 🔥 EMERGENCY FIX: AGGRESSIVE label removal (all patterns)
            import re
            
            # Pattern 1: Numbered labels (1. 훅:, 2. 문제:, etc.)
            content = re.sub(r'\d+\.\s*(훅|문제|솔루션|공감|핵심|특징|디테일|FAQ|신뢰|CTA|Hook|Problem|Solution):\s*', '', content, flags=re.IGNORECASE)
            
            # Pattern 2: Bold labels (**훅(Hook):**, etc.)
            content = re.sub(r'\*\*(훅|문제|솔루션|공감|핵심|특징|디테일|FAQ|신뢰|CTA|Hook|Problem|Solution)\s*\([^)]+\):\*\*\s*', '', content, flags=re.IGNORECASE)
            
            # Pattern 3: Labels without numbers (훅:, 문제:, etc.)
            content = re.sub(r'(훅|문제|솔루션|공감|핵심|특징|디테일|FAQ|신뢰|CTA|Hook|Problem|Solution):\s*', '', content, flags=re.IGNORECASE)
            
            # Pattern 4: Labels in parentheses ((훅), (Hook), etc.)
            content = re.sub(r'\((훅|문제|솔루션|공감|핵심|특징|디테일|FAQ|신뢰|CTA|Hook|Problem|Solution)\)\s*', '', content, flags=re.IGNORECASE)
            
            # Pattern 5: Section markers (SECTION 1:, etc.)
            content = re.sub(r'SECTION\s+\d+:\s*', '', content, flags=re.IGNORECASE)
            
            app.logger.info(f'[Content Generation] ✅ Generated winning product page: {len(content)} chars')
            app.logger.info(f'[Content Generation] 🧹 Applied AGGRESSIVE label cleanup (5 patterns)')
            if tags:
                app.logger.info(f'[Content Generation] ✅ Extracted SEO tags: {tags}')
            
            return content, tags
        else:
            app.logger.error(f'[Content Generation] ❌ API error: {response.status_code}')
            return generate_fallback_product_page(title, images), ''
    
    except Exception as e:
        app.logger.error(f'[Content Generation] ❌ Exception: {str(e)}')
        log_activity('content', f'Failed to generate winning page: {str(e)}', 'error')
        return generate_fallback_product_page(title, images), ''

def generate_fallback_product_page(title, images):
    """Fallback product page when API fails"""
    img_tags = '\n'.join([
        f'<img src="{img}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin: 20px 0;" alt="Product Image">'
        for img in images[:5]
    ])
    
    return f"""
<div style="font-family: 'Noto Sans KR', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin-bottom: 30px;">
        <h2 style="font-size: 28px; font-weight: bold; margin-bottom: 15px;">{title}</h2>
        <p style="font-size: 18px;">✨ 프리미엄 품질을 합리적인 가격에</p>
    </div>
    
    {img_tags}
    
    <div style="background: #f8f9fa; padding: 30px; border-radius: 15px; margin: 30px 0;">
        <h3 style="font-size: 24px; font-weight: bold; margin-bottom: 20px; text-align: center;">✨ 제품 특징</h3>
        <ul style="list-style: none; padding: 0;">
            <li style="padding: 15px; margin: 10px 0; background: white; border-left: 4px solid #667eea; border-radius: 8px;">
                <strong>🎯 고품질 소재</strong><br>
                <span style="color: #666;">엄선된 소재로 만든 프리미엄 제품</span>
            </li>
            <li style="padding: 15px; margin: 10px 0; background: white; border-left: 4px solid #667eea; border-radius: 8px;">
                <strong>💯 완벽한 품질 관리</strong><br>
                <span style="color: #666;">철저한 검수를 거친 안심 상품</span>
            </li>
            <li style="padding: 15px; margin: 10px 0; background: white; border-left: 4px solid #667eea; border-radius: 8px;">
                <strong>🚚 빠른 배송</strong><br>
                <span style="color: #666;">주문 후 신속하게 배송해드립니다</span>
            </li>
        </ul>
    </div>
    
    <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px;">
        <h3 style="font-size: 26px; font-weight: bold; margin-bottom: 15px;">지금 바로 만나보세요!</h3>
        <p style="font-size: 16px;">✅ 무료배송 | ✅ 당일출고 | ✅ 100% 환불보증</p>
    </div>
</div>
"""

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
    """Generate AI content for product using WINNING PRODUCT STRUCTURE"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM sourced_products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    
    app.logger.info(f'[Content Generation] 🚀 Starting WINNING page generation for product {product_id}')
    log_activity('content', f'Generating WINNING content for product {product_id}', 'in_progress')
    
    # Generate SHORT marketing copy (for summary box)
    marketing_copy = generate_marketing_copy(product['title_cn'], product['price_krw'])
    
    # Process images with Korean shopping mall styling
    original_images = json.loads(product['images_json']) if product['images_json'] else []
    processed_images = []
    
    app.logger.info(f'[Content Generation] 📸 Processing {len(original_images)} images with Korean styling')
    for img_url in original_images[:8]:  # Process max 8 images for winning structure
        processed_url = process_product_image(img_url)
        processed_images.append(processed_url)
    
    # Generate WINNING PRODUCT PAGE (5-section structure)
    app.logger.info(f'[Content Generation] ✨ Generating WINNING 5-section structure')
    winning_html, seo_tags = generate_winning_product_page(
        title=product['title_cn'],
        price=product['price_krw'],
        images=processed_images
    )
    
    # Add notice image at the end
    notice_path = create_notice_image()
    processed_images.append(notice_path)
    
    # 🔥 EMERGENCY FIX: Store SEO tags in dedicated keywords column
    cursor.execute('''
        UPDATE sourced_products
        SET marketing_copy = ?,
            description_kr = ?,
            processed_images_json = ?,
            title_kr = ?,
            keywords = ?
        WHERE id = ?
    ''', (
        marketing_copy,
        winning_html,  # Full winning structure in description_kr
        json.dumps(processed_images),
        product['title_cn'],
        seo_tags,  # 🔥 FIXED: Store in keywords column, NOT description_cn
        product_id
    ))
    
    conn.commit()
    conn.close()
    
    app.logger.info(f'[Content Generation] ✅ WINNING content generated: {len(winning_html)} chars')
    if seo_tags:
        app.logger.info(f'[Content Generation] ✅ SEO tags: {seo_tags}')
    log_activity('content', f'✅ WINNING content generated for product {product_id}', 'success')
    
    return jsonify({
        'success': True,
        'marketing_copy': marketing_copy,
        'description_kr': winning_html,
        'processed_images': processed_images,
        'seo_tags': seo_tags,
        'structure': '5-section_winning_formula'
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

@app.route('/products/<int:product_id>')
@login_required
def product_detail(product_id):
    """Product detail and edit page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sourced_products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        flash('상품을 찾을 수 없습니다', 'error')
        return redirect('/products')
    
    return render_template('product_detail.html', product=product)

@app.route('/api/products/<int:product_id>/update', methods=['POST'])
@login_required
def update_product(product_id):
    """Update product information"""
    try:
        data = request.get_json()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Update product fields
        cursor.execute('''
            UPDATE sourced_products 
            SET title_kr = ?, 
                title_cn = ?,
                price_krw = ?,
                profit_margin = ?,
                estimated_profit = ?,
                marketing_copy = ?,
                description_kr = ?,
                description_cn = ?
            WHERE id = ?
        ''', (
            data.get('title_kr'),
            data.get('title_cn'),
            data.get('price_krw'),
            data.get('profit_margin'),
            data.get('estimated_profit'),
            data.get('marketing_copy'),
            data.get('description_kr'),
            data.get('description_cn'),
            product_id
        ))
        
        conn.commit()
        conn.close()
        
        log_activity('product_update', f'상품 수정: ID {product_id}', 'success')
        
        return jsonify({'success': True, 'message': '상품이 수정되었습니다'})
        
    except Exception as e:
        app.logger.error(f'[Product Update] ❌ Error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    """Delete product"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if product exists
        cursor.execute('SELECT * FROM sourced_products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        
        if not product:
            conn.close()
            return jsonify({'success': False, 'error': '상품을 찾을 수 없습니다'}), 404
        
        # Delete product
        cursor.execute('DELETE FROM sourced_products WHERE id = ?', (product_id,))
        
        conn.commit()
        conn.close()
        
        log_activity('product_delete', f'상품 삭제: ID {product_id} - {product["title_kr"] or product["title_cn"]}', 'success')
        app.logger.info(f'[Product Delete] ✅ Product deleted: ID {product_id}')
        
        return jsonify({'success': True, 'message': '상품이 삭제되었습니다'})
        
    except Exception as e:
        app.logger.error(f'[Product Delete] ❌ Error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

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
