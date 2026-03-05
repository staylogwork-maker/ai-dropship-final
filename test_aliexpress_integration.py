#!/usr/bin/env python3
"""
Test script for AliExpress Official API Integration
Expected: RED (fail) before patch, GREEN (pass) after patch
"""

import sys
import hashlib
import time
import requests
import json

def sign_api_request(app_secret, params):
    """Generate MD5 signature for AliExpress API"""
    sorted_params = sorted(params.items())
    sign_string = app_secret + ''.join([f'{k}{v}' for k, v in sorted_params]) + app_secret
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

def test_aliexpress_api(app_key, app_secret, keyword='wireless earbuds'):
    """
    Test AliExpress Affiliate API product search
    
    Expected Response:
    {
        "success": true,
        "products": [
            {
                "product_id": "1234567890",
                "title": "Product Name",
                "price": 15.99,
                "image_url": "https://...",
                "product_url": "https://..."
            }
        ],
        "count": 10
    }
    """
    print("=" * 60)
    print("🧪 AliExpress Official API Integration Test")
    print("=" * 60)
    print(f"📝 Test Parameters:")
    print(f"   - App Key: {app_key}")
    print(f"   - App Secret: {app_secret[:10]}...{app_secret[-10:]}")
    print(f"   - Keyword: {keyword}")
    print()
    
    # API endpoint
    endpoint = "https://api-sg.aliexpress.com/sync"
    
    # Request parameters
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() + 8*3600))
    
    params = {
        'app_key': app_key,
        'method': 'aliexpress.affiliate.product.query',
        'timestamp': timestamp,
        'format': 'json',
        'v': '2.0',
        'sign_method': 'md5',
        'keywords': keyword,
        'page_size': '10',
        'target_currency': 'USD',
        'target_language': 'EN',
        'sort': 'SALE_PRICE_ASC'
    }
    
    # Generate signature
    params['sign'] = sign_api_request(app_secret, params)
    
    print(f"📡 Sending request to: {endpoint}")
    print(f"⏱️  Timestamp: {timestamp}")
    print()
    
    try:
        # Send request
        response = requests.get(endpoint, params=params, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for errors
            if 'error_response' in data:
                error = data['error_response']
                print("❌ TEST FAILED: API Error")
                print(f"   Error Code: {error.get('code', 'N/A')}")
                print(f"   Error Message: {error.get('msg', 'N/A')}")
                print(f"   Sub Code: {error.get('sub_code', 'N/A')}")
                print()
                print("💡 Common Errors:")
                print("   - 'Invalid app Key': Check App Key in Open Platform")
                print("   - 'Invalid signature': Verify timestamp format (GMT+8)")
                print("   - 'Insufficient permissions': Enable Affiliate API in app settings")
                return False
            
            # Parse response
            if 'aliexpress_affiliate_product_query_response' in data:
                result = data['aliexpress_affiliate_product_query_response']['resp_result']['result']
                
                if result['total_record_count'] > 0:
                    products = result['products']['product']
                    print(f"✅ TEST PASSED: Found {len(products)} products")
                    print()
                    print("📦 Sample Products:")
                    for i, product in enumerate(products[:3], 1):
                        print(f"\n   {i}. {product['product_title'][:50]}...")
                        print(f"      Price: ${product['target_sale_price']}")
                        print(f"      URL: {product['product_detail_url'][:60]}...")
                    
                    print()
                    print("🎉 Integration Test: PASSED ✅")
                    return True
                else:
                    print("⚠️  TEST WARNING: API works but no products found")
                    print("   Try different keyword (e.g., 'phone case', 'headphones')")
                    return True
            
            print("❌ TEST FAILED: Unexpected response format")
            print(json.dumps(data, indent=2)[:500])
            return False
            
        else:
            print(f"❌ TEST FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ TEST FAILED: Exception")
        print(f"   {type(e).__name__}: {str(e)}")
        return False

if __name__ == '__main__':
    # Test credentials
    APP_KEY = '528898'
    APP_SECRET = 'imopQLiB4Lv7PxVbCKaikGdMngXuES7s'
    
    # Run test
    success = test_aliexpress_api(APP_KEY, APP_SECRET, 'wireless earbuds')
    
    print()
    print("=" * 60)
    if success:
        print("🟢 FINAL RESULT: READY FOR INTEGRATION")
        print("   Next step: Integrate into app.py")
        sys.exit(0)
    else:
        print("🔴 FINAL RESULT: API NOT READY")
        print("   Fix errors above before proceeding")
        sys.exit(1)
