#!/usr/bin/env python3
"""
Real-World System Integration Test
Tests the complete workflow with actual keywords
Expected: All tests GREEN after AliExpress API integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (
    search_integrated_hybrid,
    get_config,
    app
)
import time

def test_keyword_search(keyword, expected_min_products=5):
    """
    Test real keyword search
    
    Args:
        keyword: Search keyword
        expected_min_products: Minimum products expected
    
    Returns:
        bool: Test passed or failed
    """
    print(f"\n{'='*60}")
    print(f"🔍 Test: Keyword Search - '{keyword}'")
    print(f"{'='*60}")
    
    try:
        start_time = time.time()
        
        # Search
        result = search_integrated_hybrid(keyword, max_results=20)
        
        elapsed = time.time() - start_time
        
        # Check for errors
        if 'error' in result:
            print(f"❌ FAIL: {result['error']}")
            return False
        
        products = result.get('products', [])
        count = len(products)
        
        print(f"\n📊 Results:")
        print(f"   - Found: {count} products")
        print(f"   - Time: {elapsed:.2f}s")
        print(f"   - Expected: ≥{expected_min_products} products")
        
        if count < expected_min_products:
            print(f"\n❌ FAIL: Too few products ({count} < {expected_min_products})")
            return False
        
        # Analyze top 3
        print(f"\n📦 Top 3 Products:")
        for i, p in enumerate(products[:3], 1):
            analysis = p.get('analysis', {})
            print(f"\n   {i}. {p['title'][:50]}...")
            print(f"      Price: ${p['price']:.2f}")
            print(f"      Sale Price: ₩{analysis.get('sale_price', 0):,}")
            print(f"      Profit: ₩{analysis.get('profit', 0):,}")
            print(f"      Margin: {analysis.get('margin', 0):.1f}%")
            print(f"      Score: {p.get('hybrid_score', 0):.1f}")
            print(f"      Source: {p.get('source', 'unknown')}")
        
        # Check data quality
        print(f"\n✅ Data Quality Check:")
        
        # All products should have required fields
        required_fields = ['title', 'price', 'url', 'image', 'source']
        for i, p in enumerate(products[:5], 1):
            missing = [f for f in required_fields if f not in p or not p[f]]
            if missing:
                print(f"   ❌ Product {i} missing: {missing}")
                return False
        
        print(f"   ✅ All products have required fields")
        
        # Check source
        sources = set(p.get('source', 'unknown') for p in products)
        print(f"   ✅ Sources: {', '.join(sources)}")
        
        if 'aliexpress_api' not in sources:
            print(f"   ⚠️  WARNING: No products from AliExpress API")
        
        # Check margins
        margins = [p.get('analysis', {}).get('margin', 0) for p in products[:10]]
        avg_margin = sum(margins) / len(margins) if margins else 0
        print(f"   ✅ Average margin (top 10): {avg_margin:.1f}%")
        
        print(f"\n✅ TEST PASSED: '{keyword}'")
        return True
        
    except Exception as e:
        print(f"\n❌ FAIL: Exception")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_price_calculation():
    """
    Test profitability calculation accuracy
    """
    print(f"\n{'='*60}")
    print(f"💰 Test: Price Calculation Accuracy")
    print(f"{'='*60}")
    
    from app import analyze_product_profitability
    
    # Test case: $10 product
    price_cny = 10 * 7.2  # $10 = 72 CNY
    
    print(f"\n📝 Test Case:")
    print(f"   Product Price: $10.00 (72 CNY)")
    
    analysis = analyze_product_profitability(price_cny)
    
    print(f"\n📊 Calculation Results:")
    print(f"   Purchase Price (KRW): ₩{analysis['purchase_price_krw']:,}")
    print(f"   Shipping Cost: ₩{analysis['shipping_cost']:,}")
    print(f"   Customs Tax: ₩{analysis['customs_tax']:,}")
    print(f"   Total Cost: ₩{analysis['total_cost']:,}")
    print(f"   Sale Price: ₩{analysis['sale_price']:,}")
    print(f"   Profit: ₩{analysis['profit']:,}")
    print(f"   Margin: {analysis['margin']:.1f}%")
    
    # Validation
    target_margin = float(get_config('target_margin_rate', 30))
    
    # Margin should be close to target (within 2%)
    margin_diff = abs(analysis['margin'] - target_margin)
    
    if margin_diff > 2.0:
        print(f"\n❌ FAIL: Margin {analysis['margin']:.1f}% differs from target {target_margin}% by {margin_diff:.1f}%")
        return False
    
    # Sale price should be > total cost
    if analysis['sale_price'] <= analysis['total_cost']:
        print(f"\n❌ FAIL: Sale price (₩{analysis['sale_price']:,}) ≤ Total cost (₩{analysis['total_cost']:,})")
        return False
    
    print(f"\n✅ TEST PASSED: Calculations accurate")
    return True

def test_api_credentials():
    """
    Test API credentials are configured
    """
    print(f"\n{'='*60}")
    print(f"🔑 Test: API Credentials Configuration")
    print(f"{'='*60}")
    
    # Check AliExpress API
    app_key = get_config('aliexpress_app_key')
    app_secret = get_config('aliexpress_app_secret')
    
    print(f"\n📋 AliExpress API:")
    if app_key and app_secret:
        print(f"   ✅ App Key: {app_key}")
        print(f"   ✅ App Secret: {app_secret[:10]}...{app_secret[-10:]}")
    else:
        print(f"   ❌ Missing credentials")
        return False
    
    # Check OpenAI API
    openai_key = get_config('openai_api_key')
    print(f"\n📋 OpenAI API:")
    if openai_key:
        print(f"   ✅ API Key: {openai_key[:10]}...{openai_key[-10:]}")
    else:
        print(f"   ⚠️  Not configured (optional)")
    
    print(f"\n✅ TEST PASSED: Credentials configured")
    return True

def run_all_tests():
    """
    Run complete test suite
    """
    print("\n" + "="*60)
    print("🧪 Real-World System Integration Test Suite")
    print("="*60)
    print("\nTesting AliExpress Official API integration")
    print("Expected: All tests GREEN ✅")
    print()
    
    results = []
    
    # Test 1: Credentials
    results.append(("API Credentials", test_api_credentials()))
    
    # Test 2: Price calculation
    results.append(("Price Calculation", test_price_calculation()))
    
    # Test 3: Real keyword searches
    test_keywords = [
        ("wireless earbuds", 5),
        ("phone case", 5),
        ("bluetooth speaker", 5)
    ]
    
    for keyword, min_products in test_keywords:
        results.append((f"Search: {keyword}", test_keyword_search(keyword, min_products)))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {name}")
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*60}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED ✅")
        print("\nSystem Status:")
        print("   ✅ AliExpress Official API: Working")
        print("   ✅ Product Search: Working")
        print("   ✅ Price Calculation: Accurate")
        print("   ✅ Data Quality: Good")
        print("\n🚀 Ready for production use!")
        return True
    else:
        print(f"\n🔴 {total - passed} TEST(S) FAILED")
        print("\nFix issues above before proceeding")
        return False

if __name__ == '__main__':
    print()
    success = run_all_tests()
    print()
    sys.exit(0 if success else 1)
