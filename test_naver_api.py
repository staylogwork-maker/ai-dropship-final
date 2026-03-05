#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 쇼핑 API 연동 테스트
========================================
목적: 실시간 가격 조회 및 시장 분석 검증
"""

import sys
import os
import sqlite3
sys.path.insert(0, os.path.dirname(__file__))

from market_analysis import analyze_naver_market

def test_naver_shopping_api():
    """네이버 쇼핑 API 테스트"""
    print("\n" + "="*60)
    print("🧪 네이버 쇼핑 API 연동 테스트")
    print("="*60)
    
    # Step 1: Config에서 인증 정보 읽기
    print("\n[Step 1] 인증 정보 확인")
    db_path = "/home/user/webapp/dropship.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM config WHERE key IN ('naver_client_id', 'naver_client_secret')")
    config = dict(cursor.fetchall())
    conn.close()
    
    client_id = config.get('naver_client_id', '')
    client_secret = config.get('naver_client_secret', '')
    
    print(f"Client ID: {client_id[:10]}... (길이: {len(client_id)})")
    print(f"Client Secret: {client_secret[:5]}... (길이: {len(client_secret)})")
    
    if not client_id or not client_secret:
        print("❌ ERROR: 네이버 API 인증 정보가 없습니다!")
        return False
    
    print("✅ 인증 정보 확인 완료")
    
    # Step 2: 실제 상품 검색 테스트
    test_keywords = [
        "무선 블루투스 이어폰",
        "폰케이스",
        "블루투스 스피커"
    ]
    
    print("\n[Step 2] 실제 상품 검색 테스트")
    print("-" * 60)
    
    for keyword in test_keywords:
        print(f"\n🔍 키워드: {keyword}")
        print("-" * 40)
        
        try:
            result = analyze_naver_market(keyword, client_id, client_secret)
            
            if result.get('success'):
                print(f"✅ 분석 성공!")
                print(f"   • 조회 상품 수: {result['total_products']}개")
                print(f"   • 가격 범위: ₩{result['min_price']:,} ~ ₩{result['max_price']:,}")
                print(f"   • 평균 가격: ₩{result['avg_price']:,.0f}")
                print(f"   • 중앙값: ₩{result['median_price']:,.0f}")
                print(f"   • 권장 판매가: ₩{result['recommended_price']:,}")
                
                # 상위 10개 경쟁 제품 표시
                print(f"\n   📊 상위 경쟁 제품 Top 10:")
                for i, comp in enumerate(result['top_products'][:10], 1):
                    price = comp.get('lprice', 0)
                    title = comp.get('title', '제목 없음')
                    # HTML 태그 제거
                    import re
                    title = re.sub('<[^<]+?>', '', title)
                    print(f"      {i}. {title[:50]}...")
                    print(f"         가격: ₩{price:,}")
            else:
                error_msg = result.get('error', '알 수 없는 오류')
                print(f"❌ 분석 실패: {error_msg}")
        
        except Exception as e:
            print(f"❌ 예외 발생: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("🎉 네이버 API 테스트 완료!")
    print("="*60)
    return True

if __name__ == "__main__":
    test_naver_shopping_api()
