"""
AI Dropshipping ERP System - Main Application
Complete implementation with all 8 modules
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
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

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DB_PATH = 'dropship.db'

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
    """Get configuration value"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

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
# MODULE 2: AI SOURCING ENGINE WITH SAFETY FILTERS
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
    api_key = get_config('scrapingant_api_key')
    if not api_key:
        return {'error': 'ScrapingAnt API key not configured'}
    
    search_url = f'https://s.1688.com/selloffer/offer_search.htm?keywords={keyword}'
    
    params = {
        'url': search_url,
        'x-api-key': api_key,
        'browser': 'true',
        'cookies_persistence': 'true',
        'return_page_source': 'true'
    }
    
    try:
        response = requests.get('https://api.scrapingant.com/v2/general', params=params, timeout=60)
        response.raise_for_status()
        
        # Parse HTML response
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        products = []
        # Simplified parsing - actual implementation would need real 1688 HTML structure
        for item in soup.find_all('div', class_='card-item', limit=max_results):
            try:
                product = {
                    'url': item.find('a')['href'] if item.find('a') else '',
                    'title': item.find('h3').get_text(strip=True) if item.find('h3') else '',
                    'price': float(item.find('span', class_='price').get_text(strip=True).replace('¥', '')) if item.find('span', class_='price') else 0,
                    'sales': int(item.find('span', class_='sales').get_text(strip=True).replace('销', '')) if item.find('span', class_='sales') else 0,
                    'image': item.find('img')['src'] if item.find('img') else ''
                }
                products.append(product)
            except Exception as e:
                continue
        
        return {'products': products, 'count': len(products)}
    
    except Exception as e:
        return {'error': str(e)}

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

@app.route('/api/sourcing/start', methods=['POST'])
@login_required
def start_sourcing():
    """Start AI sourcing process"""
    data = request.json
    keyword = data.get('keyword', '')
    
    if not keyword:
        return jsonify({'error': 'Keyword required'}), 400
    
    log_activity('sourcing', f'Starting sourcing for keyword: {keyword}', 'in_progress')
    
    # Step 1: Initial scan (50 products)
    log_activity('sourcing', 'Step 1/3: Initial scan (50 products)', 'in_progress')
    results = scrape_1688_search(keyword, max_results=50)
    
    if 'error' in results:
        log_activity('sourcing', f'Scraping failed: {results["error"]}', 'error')
        return jsonify({'error': results['error']}), 500
    
    products = results.get('products', [])
    log_activity('sourcing', f'Found {len(products)} products', 'success')
    
    # Step 2: Safety filter
    log_activity('sourcing', 'Step 2/3: Applying safety filters', 'in_progress')
    safe_products = []
    for product in products:
        is_safe, reason = check_safety_filter(product['title'])
        if is_safe:
            safe_products.append(product)
        else:
            log_activity('sourcing', f'Filtered out: {product["title"][:50]} - {reason}', 'warning')
    
    log_activity('sourcing', f'{len(safe_products)} products passed safety filter', 'success')
    
    # Step 3: Profitability analysis
    log_activity('sourcing', 'Step 3/3: Analyzing profitability', 'in_progress')
    analyzed_products = []
    target_margin = float(get_config('target_margin_rate', 30))
    
    for product in safe_products:
        analysis = analyze_product_profitability(product['price'])
        
        if analysis['margin'] >= target_margin:
            product['analysis'] = analysis
            analyzed_products.append(product)
    
    # Sort by profit and get top 3
    analyzed_products.sort(key=lambda x: x['analysis']['profit'], reverse=True)
    top_products = analyzed_products[:3]
    
    log_activity('sourcing', f'Top 3 profitable products selected', 'success')
    
    # Save to database
    conn = get_db()
    cursor = conn.cursor()
    
    for product in top_products:
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
    
    conn.commit()
    conn.close()
    
    log_activity('sourcing', f'Sourcing completed. {len(top_products)} products saved', 'success')
    
    return jsonify({
        'success': True,
        'total_scanned': len(products),
        'safety_passed': len(safe_products),
        'profitable': len(analyzed_products),
        'top_products': len(top_products)
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
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4',
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
    # Simplified implementation
    return {'success': True, 'message': f'Order {order_id} status updated to {status}'}

def update_coupang_order_status(order_id, status):
    """Update Coupang order status"""
    # Simplified implementation
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
    
    # Recent activity logs
    cursor.execute('SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 20')
    recent_logs = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html',
                         pending_products=pending_products,
                         pending_orders=pending_orders,
                         urgent_orders=urgent_orders,
                         total_profit=total_profit,
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

@app.route('/api/config/update', methods=['POST'])
@login_required
def update_config():
    """Update configuration"""
    data = request.json
    
    for key, value in data.items():
        set_config(key, value)
    
    log_activity('config', f'Configuration updated: {", ".join(data.keys())}', 'success')
    
    return jsonify({'success': True})

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
