"""
AliExpress Official Open Platform API Integration
Official Documentation: https://openservice.aliexpress.com/doc/api.htm
API Endpoint: https://api-sg.aliexpress.com/sync
"""

import hashlib
import time
import requests
import logging

logger = logging.getLogger(__name__)

def sign_api_request(app_secret, params, sign_method='md5'):
    """
    Generate API signature for AliExpress Open Platform
    
    MD5 Algorithm: MD5(app_secret + sorted_params + app_secret).toUpperCase()
    HMAC Algorithm: HMAC_MD5(sorted_params, app_secret).toUpperCase()
    
    Args:
        app_secret (str): Application secret key
        params (dict): Request parameters (excluding 'sign')
        sign_method (str): 'md5' or 'hmac' (default: 'md5')
    
    Returns:
        str: Uppercase hexadecimal signature
    """
    import hmac
    
    # Sort parameters by key (ASCII order)
    sorted_params = sorted(params.items())
    
    # Build signature string: key1value1key2value2...
    sign_str = ''
    for key, value in sorted_params:
        # Skip empty values
        if key and value:
            sign_str += f"{key}{value}"
    
    # Calculate signature based on method
    if sign_method == 'hmac':
        # HMAC-MD5: hmac_md5(sign_str, app_secret)
        signature = hmac.new(
            app_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.md5
        ).hexdigest()
    else:
        # MD5: md5(app_secret + sign_str + app_secret)
        full_str = app_secret + sign_str + app_secret
        signature = hashlib.md5(full_str.encode('utf-8')).hexdigest()
    
    # Return uppercase
    return signature.upper()


def search_aliexpress_products(app_key, app_secret, keyword, page_size=50, page_no=1, sort='default', min_price=None, max_price=None):
    """
    Search AliExpress products using Official Open Platform API
    
    Args:
        app_key (str): AliExpress App Key
        app_secret (str): AliExpress App Secret
        keyword (str): Search keyword
        page_size (int): Number of results per page (max 50)
        page_no (int): Page number (starts from 1)
        sort (str): Sort order - 'default', 'price_asc', 'price_desc', 'sales_desc', 'rating_desc'
        min_price (float): Minimum price filter (USD)
        max_price (float): Maximum price filter (USD)
    
    Returns:
        dict: {
            'success': bool,
            'products': list of product dicts,
            'total_count': int,
            'current_page': int,
            'error': str (if failed)
        }
    """
    
    logger.info(f'[AliExpress API] ========================================')
    logger.info(f'[AliExpress API] 🔍 Searching for: {keyword}')
    logger.info(f'[AliExpress API] Page: {page_no}, Size: {page_size}')
    
    # API endpoint (use US endpoint for better compatibility)
    api_url = "https://api.taobao.com/router/rest"
    
    # Current timestamp in format: yyyy-MM-dd HH:mm:ss (GMT+8)
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Build request parameters (Affiliate API - works with Dropshipping app too)
    params = {
        'method': 'aliexpress.affiliate.product.query',
        'app_key': app_key,
        'timestamp': timestamp,
        'format': 'json',
        'v': '2.0',
        'sign_method': 'md5',
        'keywords': keyword,
        'target_currency': 'USD',
        'target_language': 'EN',
        'page_no': str(page_no),
        'page_size': str(page_size),
        'sort': 'SALE_PRICE_ASC'  # Sort by price
    }
    
    # Add optional price filters
    if min_price is not None:
        params['min_price'] = str(min_price)
    if max_price is not None:
        params['max_price'] = str(max_price)
    
    # Generate signature (must exclude 'sign' parameter itself)
    params['sign'] = sign_api_request(app_secret, params, sign_method='md5')
    
    logger.info(f'[AliExpress API] 📡 Sending request to: {api_url}')
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        
        logger.info(f'[AliExpress API] 📥 Response status: {response.status_code}')
        
        if response.status_code != 200:
            error_msg = f'API returned status {response.status_code}'
            logger.error(f'[AliExpress API] ❌ {error_msg}')
            logger.error(f'[AliExpress API] Response: {response.text[:500]}')
            return {
                'success': False,
                'products': [],
                'total_count': 0,
                'current_page': page_no,
                'error': error_msg
            }
        
        # Parse JSON response
        data = response.json()
        
        # Check if API call was successful
        if 'aliexpress_affiliate_product_query_response' not in data:
            error_msg = data.get('error_response', {}).get('msg', 'Unknown API error')
            error_code = data.get('error_response', {}).get('code', 'Unknown')
            error_sub_msg = data.get('error_response', {}).get('sub_msg', '')
            logger.error(f'[AliExpress API] ❌ API Error: {error_msg}')
            logger.error(f'[AliExpress API] Error Code: {error_code}')
            logger.error(f'[AliExpress API] Sub Message: {error_sub_msg}')
            return {
                'success': False,
                'products': [],
                'total_count': 0,
                'current_page': page_no,
                'error': f'{error_msg} (Code: {error_code})'
            }
        
        # Extract product data
        response_data = data['aliexpress_affiliate_product_query_response']['resp_result']
        
        if response_data.get('resp_code') != 200:
            error_msg = response_data.get('resp_msg', 'API returned non-200 response')
            logger.error(f'[AliExpress API] ❌ Response Error: {error_msg}')
            return {
                'success': False,
                'products': [],
                'total_count': 0,
                'current_page': page_no,
                'error': error_msg
            }
        
        result = response_data.get('result', {})
        
        if not result.get('products'):
            logger.warning(f'[AliExpress API] ⚠️ No products found for: {keyword}')
            return {
                'success': True,
                'products': [],
                'total_count': 0,
                'current_page': page_no
            }
        
        # Parse products
        products = []
        for item in result['products']['product']:
            try:
                product = {
                    'id': str(item.get('product_id', '')),
                    'title': item.get('product_title', ''),
                    'url': item.get('promotion_link', item.get('product_detail_url', '')),
                    'image': item.get('product_main_image_url', ''),
                    'price': float(item.get('target_original_price', 0)),
                    'sale_price': float(item.get('target_sale_price', 0)),
                    'discount': item.get('discount', '0%'),
                    'currency': item.get('target_original_price_currency', 'USD'),
                    'sales': int(item.get('volume', 0)),
                    'rating': float(item.get('evaluate_rate', 0)),
                    'reviews': int(item.get('orders_count', 0)),
                    'shipping': item.get('ship_from', 'CN'),
                    'moq': 1,  # AliExpress always MOQ=1
                    'source': 'AliExpress',
                    'category': item.get('first_level_category_name', 'Other'),
                    'shop_name': item.get('shop_name', 'Unknown'),
                    'shop_url': item.get('shop_url', ''),
                    'commission_rate': item.get('commission_rate', '0%'),
                    'raw_data': item  # Keep original data for debugging
                }
                
                # Use sale price if available, otherwise use original price
                if product['sale_price'] > 0:
                    product['price'] = product['sale_price']
                
                products.append(product)
                
            except Exception as e:
                logger.error(f'[AliExpress API] Failed to parse product: {e}')
                continue
        
        total_count = int(result.get('total_record_count', len(products)))
        
        logger.info(f'[AliExpress API] ✅ Found {len(products)} products')
        logger.info(f'[AliExpress API] Total available: {total_count}')
        
        return {
            'success': True,
            'products': products,
            'total_count': total_count,
            'current_page': page_no
        }
        
    except requests.exceptions.Timeout:
        error_msg = 'Request timeout (30s)'
        logger.error(f'[AliExpress API] ❌ {error_msg}')
        return {
            'success': False,
            'products': [],
            'total_count': 0,
            'current_page': page_no,
            'error': error_msg
        }
        
    except Exception as e:
        error_msg = f'Exception: {str(e)}'
        logger.error(f'[AliExpress API] ❌ {error_msg}')
        return {
            'success': False,
            'products': [],
            'total_count': 0,
            'current_page': page_no,
            'error': error_msg
        }


def get_product_details(app_key, app_secret, product_ids):
    """
    Get detailed information for specific products
    
    Args:
        app_key (str): AliExpress App Key
        app_secret (str): AliExpress App Secret
        product_ids (list): List of product IDs (max 20 per request)
    
    Returns:
        dict: Product details
    """
    
    if not product_ids:
        return {'success': False, 'error': 'No product IDs provided'}
    
    # Limit to 20 products per request (API limitation)
    product_ids = product_ids[:20]
    
    logger.info(f'[AliExpress API] 📦 Fetching details for {len(product_ids)} products')
    
    api_url = "https://api-sg.aliexpress.com/sync"
    timestamp = str(int(time.time() * 1000))
    
    params = {
        'method': 'aliexpress.affiliate.productdetail.get',
        'app_key': app_key,
        'timestamp': timestamp,
        'format': 'json',
        'v': '2.0',
        'sign_method': 'md5',
        'product_ids': ','.join(str(pid) for pid in product_ids),
        'target_currency': 'USD',
        'target_language': 'EN'
    }
    
    params['sign'] = sign_api_request(app_secret, params)
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        
        if response.status_code != 200:
            return {'success': False, 'error': f'Status {response.status_code}'}
        
        data = response.json()
        
        if 'aliexpress_affiliate_productdetail_get_response' not in data:
            return {'success': False, 'error': 'Invalid response format'}
        
        result = data['aliexpress_affiliate_productdetail_get_response']['resp_result']['result']
        
        logger.info(f'[AliExpress API] ✅ Retrieved details successfully')
        
        return {
            'success': True,
            'products': result.get('products', {}).get('product', [])
        }
        
    except Exception as e:
        logger.error(f'[AliExpress API] ❌ Failed to get details: {e}')
        return {'success': False, 'error': str(e)}


# Example usage (for testing)
if __name__ == "__main__":
    print("=" * 60)
    print("AliExpress Official API Test")
    print("=" * 60)
    
    # Replace with your actual API credentials
    APP_KEY = "528346"
    APP_SECRET = "YXT43bu7bMiPrmDqobMAxnpTrmWtcjTc"
    
    if APP_KEY and APP_SECRET:
        result = search_aliexpress_products(APP_KEY, APP_SECRET, "wireless earphones", page_size=10)
        
        if result['success']:
            print(f"\n✅ Success! Found {result['total_count']} total products")
            print(f"Showing {len(result['products'])} products:\n")
            
            for i, product in enumerate(result['products'][:3], 1):
                print(f"{i}. {product['title'][:50]}...")
                print(f"   Price: ${product['price']:.2f}")
                print(f"   Sales: {product['sales']}")
                print(f"   Rating: {product['rating']}")
                print(f"   URL: {product['url'][:80]}...")
                print()
        else:
            print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
    else:
        print("\n❌ Please set APP_KEY and APP_SECRET")
