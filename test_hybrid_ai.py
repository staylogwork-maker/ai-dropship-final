#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하이브리드 AI 키워드 추출 테스트
- Gemini (무료) → OpenAI (유료) → 규칙 기반 (폴백)
"""

import sys
sys.path.insert(0, '/home/user/webapp')

from app import extract_keyword_hybrid_ai, get_config
import sqlite3

def test_hybrid_ai():
    """하이브리드 AI 키워드 추출 테스트"""
    
    print("=" * 80)
    print("🧪 하이브리드 AI 키워드 추출 시스템 테스트")
    print("=" * 80)
    
    # API 키 상태 확인
    print("\n📋 API 키 상태 확인:")
    gemini_key = get_config('gemini_api_key')
    openai_key = get_config('openai_api_key')
    
    print(f"   🟢 Gemini API Key: {'설정됨' if gemini_key else '❌ 없음'} ({len(gemini_key) if gemini_key else 0} chars)")
    print(f"   🟡 OpenAI API Key: {'설정됨' if openai_key else '❌ 없음'} ({len(openai_key) if openai_key else 0} chars)")
    
    if not gemini_key and not openai_key:
        print("\n⚠️ AI API 키가 없습니다. 규칙 기반 추출만 작동합니다.")
    
    print("\n" + "=" * 80)
    
    # 테스트 케이스
    test_cases = [
        {
            'title': 'ATTAGENS Custom Name Necklace Personalized Jewelry Gold Chain Pendant',
            'expected_category': '주얼리',
            'description': '커스텀 목걸이 (영어 브랜드명 포함)'
        },
        {
            'title': 'New Fashion Women\'s Boots Snake Pattern Leather High Heel Winter Shoes',
            'expected_category': '부츠',
            'description': '여성 부츠 (패션 아이템)'
        },
        {
            'title': 'Cathode Ray Tube Show Mechanical Effect Experiment Equipment Physics Teaching',
            'expected_category': '측정 장비',
            'description': '물리 실험 장비 (전문 용어)'
        },
        {
            'title': '5800psi Pressure Washer Car Wash High Pressure Water Gun Foam Generator',
            'expected_category': '세차 장비',
            'description': '고압 세척기 (자동차 용품)'
        },
        {
            'title': 'Sewer Drain Water Cleaning Hose Pipe Spring Plumbing Tool',
            'expected_category': '하수구 청소 도구',
            'description': '하수구 청소 호스 (생활용품)'
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📦 테스트 {i}/{len(test_cases)}: {test_case['description']}")
        print(f"   원문: {test_case['title'][:60]}...")
        print(f"   기대 카테고리: {test_case['expected_category']}")
        
        try:
            # 키워드 추출
            keyword = extract_keyword_hybrid_ai(test_case['title'])
            
            print(f"   ✅ 추출된 키워드: {keyword}")
            
            if keyword:
                success_count += 1
                
                # 예상 카테고리와 비교 (유사한 결과도 성공으로 간주)
                if (test_case['expected_category'] in keyword or 
                    keyword in test_case['expected_category'] or
                    any(word in keyword for word in test_case['expected_category'].split())):
                    print(f"   💚 정확도 평가: 우수 (예상과 일치)")
                else:
                    print(f"   💛 정확도 평가: 양호 (검색 가능한 키워드)")
        
        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")
    
    print("\n" + "=" * 80)
    print(f"📊 테스트 결과: {success_count}/{len(test_cases)} 성공 ({success_count/len(test_cases)*100:.1f}%)")
    print("=" * 80)
    
    # 실제 DB 제품으로 추가 테스트
    print("\n🔍 실제 상품 데이터베이스 테스트:")
    print("-" * 80)
    
    conn = sqlite3.connect('/home/user/webapp/dropship.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # keywords 없는 제품 5개 가져오기
    cursor.execute('''
        SELECT id, title_cn, title_kr, keywords
        FROM sourced_products
        WHERE (keywords IS NULL OR keywords = '')
        AND title_cn IS NOT NULL
        LIMIT 5
    ''')
    
    products = cursor.fetchall()
    conn.close()
    
    if products:
        print(f"\n📋 keywords 필드가 없는 제품 {len(products)}개 발견")
        
        for product in products:
            print(f"\n   상품 ID: {product['id']}")
            print(f"   원제목: {product['title_cn'][:60] if product['title_cn'] else 'N/A'}...")
            
            try:
                keyword = extract_keyword_hybrid_ai(product['title_cn'] or '')
                print(f"   ✅ 추출 키워드: {keyword}")
            except Exception as e:
                print(f"   ❌ 추출 실패: {str(e)}")
    else:
        print("   ℹ️ keywords 필드가 없는 제품이 없습니다.")
    
    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)
    
    if gemini_key:
        print("\n💡 다음 단계:")
        print("   1. 웹 UI에서 시장 분석 버튼 클릭")
        print("   2. app.log에서 '[Hybrid AI] ✅ Gemini extracted keyword' 확인")
        print("   3. Gemini 실패 시 '[Hybrid AI] ⚠️ Gemini failed' → OpenAI 폴백 확인")
    else:
        print("\n💡 Gemini API 키를 설정하려면:")
        print("   1. https://aistudio.google.com/apikey 방문")
        print("   2. 'Get API Key' → 'Create API Key' 클릭")
        print("   3. 웹 UI 설정 페이지에 붙여넣기")

if __name__ == '__main__':
    test_hybrid_ai()
