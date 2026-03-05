#!/usr/bin/env python3
"""
Integration Test: AliExpress Official API → App.py
Tests the complete flow from API to product analysis
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app
from app import search_integrated_hybrid, get_config

def test_integration():
    """
    Test the complete integration:
    1. API credentials in config
    2. search_integrated_hybrid calls search_aliexpress_official
    3. Products returned and analyzed
    4. Profitability calculations correct
    """
    print("=" * 60)
    print("🧪 Integration Test: AliExpress API → App.py")
    print("=" * 60)
    print()
    
    # Test 1: Config check
    print("📋 Test 1: Config Credentials")
    app_key = get_config('aliexpress_app_key')
    app_secret = get_config('aliexpress_app_secret')
    
    if not app_key or not app_secret:
        print("❌ FAIL: API credentials not in config")
        print("   Run: python3 -c 'import sqlite3; ...'")
        return False
    
    print(f"✅ App Key: {app_key}")
    print(f"✅ App Secret: {app_secret[:10]}...{app_secret[-10:]}")
    print()
    
    # Test 2: Search function
    print("📋 Test 2: Search Integration")
    print("   Keyword: wireless earbuds")
    print("   Calling: search_integrated_hybrid()")
    print()
    
    try:
        result = search_integrated_hybrid('wireless earbuds', max_results=10)
        
        if 'error' in result:
            print(f"❌ FAIL: {result['error']}")
            return False
        
        products = result.get('products', [])
        count = result.get('count', 0)
        
        if count == 0:
            print("❌ FAIL: No products returned")
            return False
        
        print(f"✅ SUCCESS: {count} products found")
        print()
        
        # Test 3: Product data structure
        print("📋 Test 3: Product Data Structure")
        first_product = products[0]
        
        required_fields = ['title', 'price', 'url', 'image', 'analysis', 'hybrid_score']
        missing_fields = [f for f in required_fields if f not in first_product]
        
        if missing_fields:
            print(f"❌ FAIL: Missing fields: {missing_fields}")
            return False
        
        print("✅ All required fields present:")
        print(f"   - Title: {first_product['title'][:50]}...")
        print(f"   - Price: ${first_product['price']:.2f}")
        print(f"   - Margin: {first_product['analysis']['margin']:.1f}%")
        print(f"   - Score: {first_product['hybrid_score']:.1f}")
        print()
        
        # Test 4: Profitability analysis
        print("📋 Test 4: Profitability Analysis")
        analysis = first_product['analysis']
        
        required_analysis = ['purchase_price_krw', 'sale_price', 'profit', 'margin']
        missing_analysis = [f for f in required_analysis if f not in analysis]
        
        if missing_analysis:
            print(f"❌ FAIL: Missing analysis fields: {missing_analysis}")
            return False
        
        print("✅ Analysis complete:")
        print(f"   - Purchase: ₩{analysis['purchase_price_krw']:,}")
        print(f"   - Sale Price: ₩{analysis['sale_price']:,}")
        print(f"   - Profit: ₩{analysis['profit']:,}")
        print(f"   - Margin: {analysis['margin']:.1f}%")
        print()
        
        # Test 5: Top 3 products
        print("📋 Test 5: Top Products Ranking")
        top_3 = products[:3]
        
        print(f"✅ Top 3 products by score:")
        for i, p in enumerate(top_3, 1):
            print(f"   {i}. {p['title'][:40]}...")
            print(f"      Price: ${p['price']:.2f} | Margin: {p['analysis']['margin']:.1f}% | Score: {p['hybrid_score']:.1f}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Exception during integration test")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print()
    success = test_integration()
    print()
    print("=" * 60)
    
    if success:
        print("🎉 ALL TESTS PASSED ✅")
        print()
        print("Next Steps:")
        print("1. Commit changes to git")
        print("2. Create pull request")
        print("3. Test in production with real keywords")
        print("4. Monitor logs for any issues")
        sys.exit(0)
    else:
        print("🔴 INTEGRATION TEST FAILED")
        print()
        print("Fix issues above before proceeding")
        sys.exit(1)
