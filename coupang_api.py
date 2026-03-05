#!/usr/bin/env python3
"""
Coupang Partners API Integration
Collects bestseller data, sales volume, and review information
"""

import hmac
import hashlib
import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)


class CoupangAPI:
    """
    Coupang Partners API client
    Docs: https://developers.coupangcorp.com/hc/ko/articles/360033575113
    """
    
    BASE_URL = "https://api-gateway.coupang.com"
    
    def __init__(self, access_key: str, secret_key: str):
        """Initialize Coupang API client"""
        self.access_key = access_key
        self.secret_key = secret_key
        logger.info("[Coupang API] Initialized")
    
    def search_products(self, keyword: str, limit: int = 100) -> Dict[str, Any]:
        """
        Search Coupang products by keyword
        
        Args:
            keyword: Search keyword (Korean)
            limit: Maximum results (default 100)
        
        Returns:
            Dict with search results including:
            - products: list of product data
            - total_count: total number of results
            - avg_price: average price
            - price_range: min/max prices
        """
        
        logger.info(f"[Coupang API] Searching for keyword: {keyword}")
        
        try:
            # Build API request
            endpoint = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
            params = {
                'keyword': keyword,
                'limit': limit
            }
            
            # Generate request signature
            url = self._generate_request_url(endpoint, params)
            headers = self._generate_headers("GET", endpoint, query=urlencode(params))
            
            # Make API request
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[Coupang API] ✅ Found {len(data.get('data', {}).get('productData', []))} products")
                
                # Parse and enrich results
                return self._parse_search_results(data)
            
            elif response.status_code == 401:
                logger.error("[Coupang API] ❌ Authentication failed - check API credentials")
                return {
                    'success': False,
                    'error': 'Invalid Coupang API credentials',
                    'products': [],
                    'total_count': 0
                }
            
            elif response.status_code == 429:
                logger.error("[Coupang API] ❌ Rate limit exceeded")
                return {
                    'success': False,
                    'error': 'Coupang API rate limit exceeded',
                    'products': [],
                    'total_count': 0
                }
            
            else:
                logger.error(f"[Coupang API] ❌ API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'Coupang API error: {response.status_code}',
                    'products': [],
                    'total_count': 0
                }
        
        except requests.exceptions.Timeout:
            logger.error("[Coupang API] ❌ Request timeout")
            return {
                'success': False,
                'error': 'Coupang API timeout',
                'products': [],
                'total_count': 0
            }
        
        except Exception as e:
            logger.error(f"[Coupang API] ❌ Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'products': [],
                'total_count': 0
            }
    
    def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """
        Get detailed product information
        
        Args:
            product_id: Coupang product ID
        
        Returns:
            Dict with detailed product data
        """
        
        logger.info(f"[Coupang API] Fetching details for product: {product_id}")
        
        try:
            endpoint = f"/v2/providers/affiliate_open_api/apis/openapi/products/{product_id}"
            
            url = self._generate_request_url(endpoint)
            headers = self._generate_headers("GET", endpoint)
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[Coupang API] ✅ Product details retrieved")
                return self._parse_product_details(data)
            else:
                logger.error(f"[Coupang API] ❌ Failed to get product details: {response.status_code}")
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}'
                }
        
        except Exception as e:
            logger.error(f"[Coupang API] ❌ Error getting product details: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_bestsellers(self, category_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Get bestselling products (optionally by category)
        
        Args:
            category_id: Coupang category ID (optional)
            limit: Maximum results
        
        Returns:
            Dict with bestseller data
        """
        
        logger.info(f"[Coupang API] Fetching bestsellers (category: {category_id or 'all'})")
        
        try:
            endpoint = "/v2/providers/affiliate_open_api/apis/openapi/products/bestcategories"
            params = {'limit': limit}
            
            if category_id:
                params['categoryId'] = category_id
            
            url = self._generate_request_url(endpoint, params)
            headers = self._generate_headers("GET", endpoint, query=urlencode(params))
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[Coupang API] ✅ Bestsellers retrieved")
                return self._parse_bestseller_results(data)
            else:
                logger.error(f"[Coupang API] ❌ Bestseller API error: {response.status_code}")
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}',
                    'products': []
                }
        
        except Exception as e:
            logger.error(f"[Coupang API] ❌ Error getting bestsellers: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'products': []
            }
    
    def estimate_sales_volume(self, product_data: Dict[str, Any]) -> int:
        """
        Estimate monthly sales volume based on product data
        
        Args:
            product_data: Product information from API
        
        Returns:
            Estimated monthly sales (units)
        """
        
        # Estimation algorithm based on available signals
        review_count = product_data.get('reviewCount', 0)
        rating = product_data.get('rating', 0)
        rocket_delivery = product_data.get('isRocket', False)
        is_bestseller = product_data.get('isBest', False)
        
        # Base estimate: 1 review per 20-50 purchases (Korean market average)
        base_sales = review_count * 35
        
        # Adjust for rating (higher rating = higher conversion)
        if rating >= 4.5:
            base_sales *= 1.3
        elif rating >= 4.0:
            base_sales *= 1.1
        elif rating < 3.5 and rating > 0:
            base_sales *= 0.7
        
        # Rocket delivery boost (15% higher conversion)
        if rocket_delivery:
            base_sales *= 1.15
        
        # Bestseller boost
        if is_bestseller:
            base_sales *= 1.5
        
        # Assume reviews accumulated over 6 months on average
        monthly_sales = int(base_sales / 6)
        
        logger.info(f"[Coupang API] Estimated monthly sales: {monthly_sales:,} units (based on {review_count} reviews)")
        
        return monthly_sales
    
    # ============================================================================
    # Private Helper Methods
    # ============================================================================
    
    def _generate_request_url(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate full API request URL"""
        url = f"{self.BASE_URL}{endpoint}"
        if params:
            url += f"?{urlencode(params)}"
        return url
    
    def _generate_headers(self, method: str, endpoint: str, query: str = "") -> Dict[str, str]:
        """
        Generate HMAC authentication headers for Coupang API
        
        Coupang uses HMAC-SHA256 signature authentication
        """
        
        datetime_str = datetime.utcnow().strftime('%y%m%d') + 'T' + datetime.utcnow().strftime('%H%M%S') + 'Z'
        
        # Build string to sign
        message = datetime_str + method + endpoint + query
        
        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Build authorization header
        authorization = f"CEA algorithm=HmacSHA256, access-key={self.access_key}, signed-date={datetime_str}, signature={signature}"
        
        headers = {
            'Authorization': authorization,
            'Content-Type': 'application/json;charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        return headers
    
    def _parse_search_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse search API response"""
        
        product_list = data.get('data', {}).get('productData', [])
        
        products = []
        prices = []
        
        for item in product_list:
            product_id = item.get('productId')
            product_name = item.get('productName', '')
            product_price = item.get('productPrice', 0)
            product_url = item.get('productUrl', '')
            product_image = item.get('productImage', '')
            review_count = item.get('reviewCount', 0)
            rating = item.get('rating', 0)
            is_rocket = item.get('isRocket', False)
            is_best = item.get('isBest', False)
            
            # Estimate sales
            estimated_monthly_sales = self.estimate_sales_volume({
                'reviewCount': review_count,
                'rating': rating,
                'isRocket': is_rocket,
                'isBest': is_best
            })
            
            products.append({
                'product_id': product_id,
                'title': product_name,
                'price': product_price,
                'url': product_url,
                'image': product_image,
                'review_count': review_count,
                'rating': rating,
                'is_rocket_delivery': is_rocket,
                'is_bestseller': is_best,
                'estimated_monthly_sales': estimated_monthly_sales,
                'marketplace': 'coupang'
            })
            
            if product_price > 0:
                prices.append(product_price)
        
        # Calculate statistics
        avg_price = int(sum(prices) / len(prices)) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        total_reviews = sum(p['review_count'] for p in products)
        avg_rating = sum(p['rating'] for p in products if p['rating'] > 0) / len([p for p in products if p['rating'] > 0]) if products else 0
        total_estimated_sales = sum(p['estimated_monthly_sales'] for p in products)
        
        logger.info(f"[Coupang API] Parsed {len(products)} products:")
        logger.info(f"  - Total reviews: {total_reviews:,}")
        logger.info(f"  - Avg rating: {avg_rating:.2f}/5.0")
        logger.info(f"  - Estimated total monthly sales: {total_estimated_sales:,} units")
        logger.info(f"  - Price range: ₩{min_price:,} - ₩{max_price:,} (avg: ₩{avg_price:,})")
        
        return {
            'success': True,
            'products': products,
            'total_count': len(products),
            'total_reviews': total_reviews,
            'avg_rating': round(avg_rating, 2),
            'estimated_monthly_sales': total_estimated_sales,
            'avg_price': avg_price,
            'price_range': {
                'min': min_price,
                'max': max_price,
                'avg': avg_price
            },
            'top_products': sorted(products, key=lambda x: x['estimated_monthly_sales'], reverse=True)[:10]
        }
    
    def _parse_product_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse product details API response"""
        
        product_data = data.get('data', {})
        
        return {
            'success': True,
            'product_id': product_data.get('productId'),
            'title': product_data.get('productName', ''),
            'price': product_data.get('productPrice', 0),
            'description': product_data.get('productDescription', ''),
            'category_id': product_data.get('categoryId'),
            'category_name': product_data.get('categoryName', ''),
            'vendor_item_id': product_data.get('vendorItemId'),
            'review_count': product_data.get('reviewCount', 0),
            'rating': product_data.get('rating', 0),
            'is_rocket': product_data.get('isRocket', False),
            'is_free_shipping': product_data.get('isFreeShipping', False)
        }
    
    def _parse_bestseller_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse bestseller API response"""
        
        bestseller_list = data.get('data', [])
        
        products = []
        
        for idx, item in enumerate(bestseller_list, 1):
            product = {
                'bestseller_rank': idx,
                'product_id': item.get('productId'),
                'title': item.get('productName', ''),
                'price': item.get('productPrice', 0),
                'url': item.get('productUrl', ''),
                'image': item.get('productImage', ''),
                'review_count': item.get('reviewCount', 0),
                'rating': item.get('rating', 0),
                'category_name': item.get('categoryName', ''),
                'is_rocket': item.get('isRocket', False)
            }
            
            # Bestsellers typically have high sales
            product['estimated_monthly_sales'] = self.estimate_sales_volume({
                'reviewCount': product['review_count'],
                'rating': product['rating'],
                'isRocket': product['is_rocket'],
                'isBest': True
            })
            
            products.append(product)
        
        logger.info(f"[Coupang API] Parsed {len(products)} bestsellers")
        
        return {
            'success': True,
            'products': products,
            'total_count': len(products)
        }


def analyze_coupang_market(keyword: str, access_key: str, secret_key: str) -> Dict[str, Any]:
    """
    High-level function to analyze Coupang market for a keyword
    
    Args:
        keyword: Korean search keyword
        access_key: Coupang API access key
        secret_key: Coupang API secret key
    
    Returns:
        Comprehensive market analysis dict
    """
    
    logger.info(f"[Coupang Market Analysis] Starting analysis for keyword: {keyword}")
    
    api = CoupangAPI(access_key, secret_key)
    
    # Search products
    search_result = api.search_products(keyword, limit=100)
    
    if not search_result.get('success', False):
        logger.error(f"[Coupang Market Analysis] ❌ Failed: {search_result.get('error', 'Unknown error')}")
        return {
            'success': False,
            'error': search_result.get('error', 'Unknown error'),
            'keyword': keyword,
            'total_products': 0
        }
    
    products = search_result.get('products', [])
    
    # Get top seller details (top 3 only to save API calls)
    top_sellers = []
    for product in products[:3]:
        details = api.get_product_details(product['product_id'])
        if details.get('success'):
            top_sellers.append(details)
    
    logger.info(f"[Coupang Market Analysis] ✅ Analysis complete:")
    logger.info(f"  - Total products: {len(products)}")
    logger.info(f"  - Total reviews: {search_result.get('total_reviews', 0):,}")
    logger.info(f"  - Avg rating: {search_result.get('avg_rating', 0):.2f}/5.0")
    logger.info(f"  - Est. monthly sales: {search_result.get('estimated_monthly_sales', 0):,} units")
    
    return {
        'success': True,
        'keyword': keyword,
        'total_products': len(products),
        'total_reviews': search_result.get('total_reviews', 0),
        'avg_rating': search_result.get('avg_rating', 0),
        'estimated_monthly_sales': search_result.get('estimated_monthly_sales', 0),
        'price_range': search_result.get('price_range', {}),
        'products': products,
        'top_sellers': top_sellers,
        'market_summary': {
            'demand_indicator': 'high' if search_result.get('total_reviews', 0) > 1000 else 'moderate' if search_result.get('total_reviews', 0) > 100 else 'low',
            'competition_level': 'high' if len(products) > 500 else 'moderate' if len(products) > 100 else 'low',
            'avg_monthly_sales_per_seller': int(search_result.get('estimated_monthly_sales', 0) / len(products)) if products else 0
        }
    }
