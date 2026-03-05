"""
Market Analysis Module
실시간 네이버/쿠팡 시장 데이터 분석

기능:
1. 네이버 쇼핑 유사 제품 가격 분석
2. 쿠팡 경쟁 제품 가격 분석
3. 키워드 트렌드 분석
4. 추천 판매가 계산
"""

import requests
import json
from datetime import datetime, timedelta
import statistics

def analyze_naver_market(keyword, client_id, client_secret):
    """
    네이버 쇼핑 API로 시장 분석
    
    Returns:
        dict: {
            'avg_price': 평균가,
            'min_price': 최저가,
            'max_price': 최고가,
            'total_products': 총 상품 수,
            'price_distribution': 가격 분포,
            'recommended_price': 추천 판매가,
            'top_products': 상위 30개 제품,
            'timestamp': 조회 시간
        }
    """
    try:
        # 네이버 쇼핑 검색 API
        url = "https://openapi.naver.com/v1/search/shop.json"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        params = {
            "query": keyword,
            "display": 100,  # 최대 100개
            "sort": "sim"  # 정확도순
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'timestamp': datetime.now().isoformat()
            }
        
        data = response.json()
        items = data.get('items', [])
        
        if not items:
            return {
                'success': False,
                'error': 'No products found',
                'timestamp': datetime.now().isoformat()
            }
        
        # 가격 추출 (문자열 → 숫자)
        prices = []
        for item in items:
            try:
                price = int(item.get('lprice', 0))  # lprice: 최저가
                if price > 0:
                    prices.append(price)
            except:
                continue
        
        if not prices:
            return {
                'success': False,
                'error': 'No valid prices found',
                'timestamp': datetime.now().isoformat()
            }
        
        # 통계 계산
        avg_price = statistics.mean(prices)
        median_price = statistics.median(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        # 가격 분포 (분위수)
        sorted_prices = sorted(prices)
        q1 = sorted_prices[len(sorted_prices) // 4]  # 25%
        q3 = sorted_prices[3 * len(sorted_prices) // 4]  # 75%
        
        # 추천 판매가: 평균의 85-90% (경쟁력 확보)
        recommended_price = int(avg_price * 0.87)
        # 100원 단위로 반올림
        recommended_price = (recommended_price // 100) * 100
        
        # 가격 분포 히스토그램 (5개 구간)
        price_ranges = [
            (0, 10000, "1만원 이하"),
            (10000, 20000, "1-2만원"),
            (20000, 30000, "2-3만원"),
            (30000, 50000, "3-5만원"),
            (50000, float('inf'), "5만원 이상")
        ]
        
        distribution = {}
        for min_val, max_val, label in price_ranges:
            count = sum(1 for p in prices if min_val <= p < max_val)
            if count > 0:
                distribution[label] = {
                    'count': count,
                    'percentage': round(count / len(prices) * 100, 1)
                }
        
        # 상위 제품 정보 (가격 있는 것만 필터링)
        top_products = []
        for item in items:
            price = int(item.get('lprice', 0))
            if price > 0:  # 0원 제품 제외
                top_products.append({
                    'title': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                    'price': price,
                    'link': item.get('link', ''),
                    'image': item.get('image', ''),
                    'mall_name': item.get('mallName', '알 수 없음')
                })
            if len(top_products) >= 10:  # 최대 10개
                break
        
        return {
            'success': True,
            'keyword': keyword,
            'total_products': data.get('total', 0),
            'analyzed_products': len(prices),
            'avg_price': int(avg_price),
            'median_price': int(median_price),
            'min_price': min_price,
            'max_price': max_price,
            'q1_price': q1,  # 하위 25%
            'q3_price': q3,  # 상위 25%
            'recommended_price': recommended_price,
            'price_distribution': distribution,
            'top_products': top_products,
            'analysis_summary': {
                'competitive_price_range': f'{q1:,}원 ~ {q3:,}원',
                'market_position': get_market_position(recommended_price, min_price, max_price),
                'price_competitiveness': calculate_competitiveness(recommended_price, avg_price)
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def get_market_position(price, min_price, max_price):
    """가격 시장 포지션 계산"""
    if price <= min_price * 1.1:
        return "저가 공격형"
    elif price <= (min_price + max_price) / 2:
        return "가성비 중심"
    elif price <= max_price * 0.8:
        return "중고가형"
    else:
        return "프리미엄"

def calculate_competitiveness(my_price, avg_price):
    """가격 경쟁력 계산"""
    diff_percent = ((my_price - avg_price) / avg_price) * 100
    if diff_percent <= -20:
        return "매우 높음 (평균 대비 20% 이상 저렴)"
    elif diff_percent <= -10:
        return "높음 (평균 대비 10-20% 저렴)"
    elif diff_percent <= 0:
        return "보통 (평균 대비 0-10% 저렴)"
    elif diff_percent <= 10:
        return "낮음 (평균 대비 0-10% 비쌈)"
    else:
        return "매우 낮음 (평균 대비 10% 이상 비쌈)"

def analyze_coupang_market(keyword, access_key, secret_key):
    """
    쿠팡 파트너스 API로 시장 분석
    
    Note: 쿠팡 파트너스 API는 최종 승인 필요 (매출 15만원 이상)
    """
    # TODO: 쿠팡 파트너스 API 승인 후 구현
    return {
        'success': False,
        'error': 'Coupang Partners API requires final approval',
        'note': '쿠팡 파트너스 최종 승인(매출 15만원) 후 사용 가능',
        'timestamp': datetime.now().isoformat()
    }

def get_naver_keyword_trend(keyword, client_id, client_secret):
    """
    네이버 DataLab API로 키워드 트렌드 분석
    
    Note: 네이버 DataLab API 신청 필요
    """
    try:
        # DataLab 쇼핑인사이트 API
        url = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json"
        }
        
        # 최근 1개월 데이터
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "timeUnit": "date",
            "keyword": keyword,
            "device": "all",
            "gender": "all",
            "ages": ["10", "20", "30", "40", "50", "60"]
        }
        
        response = requests.post(url, headers=headers, json=body, timeout=10)
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'note': 'DataLab API 승인 필요할 수 있음',
                'timestamp': datetime.now().isoformat()
            }
        
        data = response.json()
        
        # 트렌드 분석
        results = data.get('results', [])
        if not results:
            return {
                'success': False,
                'error': 'No trend data',
                'timestamp': datetime.now().isoformat()
            }
        
        trend_data = results[0].get('data', [])
        ratios = [item['ratio'] for item in trend_data]
        
        avg_ratio = statistics.mean(ratios)
        recent_ratio = statistics.mean(ratios[-7:])  # 최근 7일 평균
        
        # 트렌드 방향
        is_rising = recent_ratio > avg_ratio * 1.1
        
        return {
            'success': True,
            'keyword': keyword,
            'avg_search_ratio': round(avg_ratio, 2),
            'recent_ratio': round(recent_ratio, 2),
            'trend': '상승' if is_rising else ('하락' if recent_ratio < avg_ratio * 0.9 else '유지'),
            'trend_score': round((recent_ratio / avg_ratio - 1) * 100, 1),  # % 변화
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# Test function
if __name__ == '__main__':
    # Example usage
    print("Market Analysis Module Test")
    print("=" * 60)
    print("Note: Requires Naver API credentials in config")
