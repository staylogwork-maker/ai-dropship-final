#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blue Ocean Discovery 테스트
"""

import sys
sys.path.insert(0, '/home/user/webapp')

from blue_ocean_discovery import (
    get_naver_shopping_trends,
    calculate_blue_ocean_score,
    analyze_market_opportunity
)
from app import get_config

def test_blue_ocean():
    print("=" * 80)
    print("🧪 Blue Ocean Discovery 테스트")
    print("=" * 80)
    
    # API 키 확인
    client_id = get_config('naver_client_id')
    client_secret = get_config('naver_client_secret')
    
    if not client_id or not client_secret:
        print("\n❌ 네이버 API 키가 설정되지 않았습니다!")
        return
    
    print(f"\n✅ 네이버 API 키 확인 완료")
    
    # 1. 트렌드 키워드 수집 테스트
    print("\n" + "=" * 80)
    print("📋 Step 1: 트렌드 키워드 수집")
    print("=" * 80)
    
    trending = get_naver_shopping_trends(client_id, client_secret)
    print(f"\n총 {len(trending)}개 키워드 수집")
    print(f"샘플 (처음 10개):")
    for item in trending[:10]:
        print(f"  - {item['keyword']} ({item['category']})")
    
    # 2. Blue Ocean 점수 계산 테스트
    print("\n" + "=" * 80)
    print("📊 Step 2: Blue Ocean 점수 계산 테스트")
    print("=" * 80)
    
    test_cases = [
        {
            'name': '좋은 시장 (낮은 경쟁, 높은 가격)',
            'data': {
                'total_products': 500,
                'analyzed_products': 100,
                'avg_price': 50000,
                'median_price': 48000
            }
        },
        {
            'name': '나쁜 시장 (높은 경쟁, 낮은 가격)',
            'data': {
                'total_products': 10000,
                'analyzed_products': 8000,
                'avg_price': 15000,
                'median_price': 12000
            }
        },
        {
            'name': '보통 시장',
            'data': {
                'total_products': 2000,
                'analyzed_products': 800,
                'avg_price': 30000,
                'median_price': 28000
            }
        }
    ]
    
    for case in test_cases:
        score = calculate_blue_ocean_score(case['data'])
        print(f"\n{case['name']}")
        print(f"  전체 제품: {case['data']['total_products']}")
        print(f"  유효 제품: {case['data']['analyzed_products']}")
        print(f"  평균 가격: ₩{case['data']['avg_price']:,}")
        print(f"  Blue Ocean 점수: {score}/10")
        
        if score >= 7.0:
            print(f"  평가: 🔥 매우 우수")
        elif score >= 5.0:
            print(f"  평가: ⭐ 우수")
        elif score >= 3.0:
            print(f"  평가: 💡 보통")
        else:
            print(f"  평가: ⚠️ 낮음")
    
    # 3. 실제 시장 분석 테스트
    print("\n" + "=" * 80)
    print("🔍 Step 3: 실제 키워드 시장 분석 (샘플 3개)")
    print("=" * 80)
    
    sample_keywords = ['차량용 공기청정기', '반려동물 자동 급식기', '무선 이어폰']
    
    for keyword in sample_keywords:
        print(f"\n{'─' * 80}")
        print(f"🎯 키워드: {keyword}")
        print(f"{'─' * 80}")
        
        result = analyze_market_opportunity(keyword, client_id, client_secret)
        
        if result.get('success'):
            print(f"\n✅ 분석 성공!")
            print(f"  Blue Ocean 점수: {result['blue_ocean_score']}/10")
            print(f"  평가: {result['recommendation']}")
            print(f"\n  📊 시장 데이터:")
            market = result['market_data']
            print(f"    - 전체 제품 수: {market['total_products']:,}개")
            print(f"    - 분석 제품 수: {market['analyzed_products']:,}개")
            print(f"    - 평균 가격: ₩{market['avg_price']:,}")
            print(f"    - 중앙값: ₩{market['median_price']:,}")
            print(f"    - 가격 범위: ₩{market['min_price']:,} ~ ₩{market['max_price']:,}")
            print(f"    - 권장 판매가: ₩{market['recommended_price']:,}")
        else:
            print(f"\n❌ 분석 실패: {result.get('error', '알 수 없는 오류')}")
    
    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)

if __name__ == '__main__':
    test_blue_ocean()
