"""
AliExpress ↔ Naver Real-time Matching & Validation
알리익스프레스와 네이버 실시간 매칭 및 검증
"""

import logging
import sqlite3
import requests
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


def get_config(key: str, default=None):
    """설정값 조회"""
    try:
        conn = sqlite3.connect('dropship.db')
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default
    except Exception as e:
        logger.error(f"Failed to get config {key}: {e}")
        return default


def translate_keyword_to_english(korean_keyword: str) -> str:
    """
    한글 키워드 → 영문 키워드 변환 (Gemini → OpenAI → 규칙 기반 순)
    
    Args:
        korean_keyword: 한글 키워드 (예: "차량용 USB 공기청정기", "드라이기")
    
    Returns:
        영문 키워드 (예: "car usb air purifier", "hair dryer")
    """
    try:
        import google.generativeai as genai
    except:
        genai = None
    
    try:
        import openai
    except:
        openai = None
    
    # 1단계: Gemini API 시도 (무료, 1,500 calls/day)
    gemini_key = get_config('gemini_api_key')
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""Translate this Korean e-commerce keyword to English for AliExpress search.
Output ONLY the English keyword, nothing else.

Rules:
1. Use simple, searchable product category terms
2. Remove brand names, model numbers
3. Focus on what the product IS or DOES
4. Keep it short (2-5 words)

Korean: {korean_keyword}
English:"""
            
            response = model.generate_content(prompt)
            english = response.text.strip().lower()
            
            logger.info(f"[Translation-Gemini] ✅ {korean_keyword} → {english}")
            return english
            
        except Exception as e:
            logger.warning(f"[Translation-Gemini] ❌ Failed: {e}")
    
    # 2단계: OpenAI GPT-4o-mini 시도 (유료)
    openai_key = get_config('openai_api_key')
    if openai_key:
        try:
            openai.api_key = openai_key
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""Translate this Korean e-commerce keyword to English for AliExpress search.
Output ONLY the English keyword, nothing else.

Korean: {korean_keyword}
English:"""
                }],
                max_tokens=20,
                temperature=0.3
            )
            
            english = response.choices[0].message.content.strip().lower()
            logger.info(f"[Translation-OpenAI] ✅ {korean_keyword} → {english}")
            return english
            
        except Exception as e:
            logger.warning(f"[Translation-OpenAI] ❌ Failed: {e}")
    
    # 3단계: 규칙 기반 매핑 (100% 폴백) - 확장판
    translation_map = {
        # 가전제품
        '드라이기': 'hair dryer',
        '헤어드라이기': 'hair dryer',
        '공기청정기': 'air purifier',
        '가습기': 'humidifier',
        '선풍기': 'fan',
        '청소기': 'vacuum cleaner',
        '세척기': 'washer',
        '세탁기': 'washing machine',
        '건조기': 'dryer',
        '냉장고': 'refrigerator',
        '전자레인지': 'microwave',
        '에어프라이어': 'air fryer',
        '믹서기': 'blender',
        '주전자': 'kettle',
        
        # 차량용품
        '차량용': 'car',
        '자동차': 'car',
        '오토바이': 'motorcycle',
        '자전거': 'bicycle',
        
        # 전자제품
        '무선': 'wireless',
        '블루투스': 'bluetooth',
        '이어폰': 'earphone',
        '헤드폰': 'headphone',
        '스피커': 'speaker',
        '보조배터리': 'power bank',
        '충전기': 'charger',
        '휴대폰': 'phone',
        '스마트폰': 'smartphone',
        '거치대': 'holder',
        '케이블': 'cable',
        '키보드': 'keyboard',
        '마우스 패드': 'mouse pad',  # 🔧 추가: 복합어 우선
        '마우스패드': 'mousepad',    # 🔧 추가: 붙여쓰기
        '게이밍 마우스패드': 'gaming mouse pad',  # 🔧 추가
        # '마우스': 'mouse',  # 🔧 제거: "마우스 패드"를 "mouse"로 오역 방지
        '게이밍': 'gaming',
        '기계식': 'mechanical',
        '웹캠': 'webcam',
        '마이크': 'microphone',
        
        # 반려동물
        '반려동물': 'pet',
        '강아지': 'dog',
        '고양이': 'cat',
        '급식기': 'feeder',
        '급수기': 'water dispenser',
        '화장실': 'litter box',
        '장난감': 'toy',
        
        # 패션/악세서리
        '주얼리': 'jewelry',
        '목걸이': 'necklace',
        '반지': 'ring',
        '귀걸이': 'earring',
        '팔찌': 'bracelet',
        '시계': 'watch',
        '가방': 'bag',
        '지갑': 'wallet',
        
        # 주방/조리
        '조리도구': 'cooking utensil',
        '실리콘': 'silicone',
        '세트': 'set',
        '냄비': 'pot',
        '프라이팬': 'frying pan',
        '칼': 'knife',
        '도마': 'cutting board',
        
        # 기타
        '자동': 'automatic',
        '고압': 'high pressure',
        '청소': 'cleaning',
        '측정': 'measurement',
        '반도체': 'semiconductor',
        'IC칩': 'ic chip',
        '다용도': 'multi purpose',
    }
    
    # 🔧 FIX: 복합어 우선 매칭 (긴 키워드부터)
    # "마우스 패드"를 통째로 매칭한 후, 개별 단어 매칭
    for ko, en in sorted(translation_map.items(), key=lambda x: -len(x[0])):
        if ko == korean_keyword:
            logger.info(f"[Translation-RuleBased] ✅ {korean_keyword} → {en}")
            return en
    
    # 개별 단어 번역
    words = korean_keyword.split()
    english_words = []
    
    for word in words:
        # 직접 매칭
        if word in translation_map:
            english_words.append(translation_map[word])
        else:
            # 부분 매칭
            matched = False
            for ko, en in translation_map.items():
                if ko in word:
                    english_words.append(en)
                    matched = True
                    break
            # 매칭 안 되면 원문 유지
            if not matched:
                english_words.append(word)
    
    english = ' '.join(english_words) if english_words else korean_keyword
    logger.info(f"[Translation-RuleBased] ⚠️ {korean_keyword} → {english}")
    return english


def search_aliexpress_official(keyword: str, max_results: int = 50) -> List[Dict]:
    """
    AliExpress Official Affiliate API 검색
    """
    try:
        # AliExpress API 엔드포인트 (실제 구현 시 API 키 필요)
        # 여기서는 더미 구현 - 실제로는 AliExpress Affiliate API를 호출해야 함
        logger.info(f"[AliExpress API] Searching for: {keyword}")
        
        # TODO: 실제 AliExpress API 구현
        # response = requests.get(
        #     'https://api-sg.aliexpress.com/sync',
        #     params={'keywords': keyword, 'page_size': max_results},
        #     headers={'Authorization': 'Bearer YOUR_API_KEY'}
        # )
        
        # 임시로 빈 리스트 반환
        return []
    except Exception as e:
        logger.error(f"AliExpress search failed: {e}")
        return []


def calculate_dropship_feasibility(ali_price_usd, naver_avg_price_krw, shipping_days=None):
    """
    드롭쉬핑 가능성 계산
    
    Args:
        ali_price_usd: 알리 가격 (USD)
        naver_avg_price_krw: 네이버 평균 가격 (KRW)
        shipping_days: 배송 기간 (일) - 선택
    
    Returns:
        dict: {
            'feasible': True/False,
            'margin_rate': 마진율 (%),
            'profit_krw': 실제 이익 (원),
            'cost_breakdown': {...},
            'score': 0~10점
        }
    """
    # 설정값 로드
    cny_rate = float(get_config('cny_exchange_rate') or 190)
    exchange_buffer = float(get_config('exchange_rate_buffer') or 1.05)
    shipping_cost = float(get_config('shipping_cost_base') or 5000)
    customs_rate = float(get_config('customs_tax_rate') or 0.10)
    naver_fee_rate = float(get_config('naver_fee_rate') or 0.06)
    
    # 비용 계산
    ali_price_krw = ali_price_usd * cny_rate * exchange_buffer  # USD → KRW
    customs_tax = ali_price_krw * customs_rate if ali_price_krw > 150000 else 0  # 15만원 이상만
    total_cost = ali_price_krw + shipping_cost + customs_tax
    
    # 수익 계산
    naver_fee = naver_avg_price_krw * naver_fee_rate
    net_revenue = naver_avg_price_krw - naver_fee
    profit = net_revenue - total_cost
    margin_rate = (profit / net_revenue * 100) if net_revenue > 0 else -100
    
    # 드롭쉬핑 가능성 판단
    feasible = margin_rate >= 25  # 최소 25% 마진
    
    # 점수 계산 (0~10)
    if margin_rate >= 50:
        score = 10.0
    elif margin_rate >= 40:
        score = 8.5
    elif margin_rate >= 30:
        score = 7.0
    elif margin_rate >= 25:
        score = 5.5
    elif margin_rate >= 20:
        score = 4.0
    elif margin_rate >= 15:
        score = 2.5
    else:
        score = 1.0
    
    # 배송 기간 패널티
    if shipping_days:
        if shipping_days > 30:
            score *= 0.7
        elif shipping_days > 20:
            score *= 0.85
    
    return {
        'feasible': feasible,
        'margin_rate': round(margin_rate, 1),
        'profit_krw': int(profit),
        'score': round(score, 1),
        'cost_breakdown': {
            'ali_price_krw': int(ali_price_krw),
            'shipping_cost': int(shipping_cost),
            'customs_tax': int(customs_tax),
            'total_cost': int(total_cost),
            'naver_price': int(naver_avg_price_krw),
            'naver_fee': int(naver_fee),
            'net_revenue': int(net_revenue),
        }
    }


def translate_to_english_ai(korean_keyword):
    """
    AI를 사용하여 한국어 → 영어 번역
    
    우선순위:
    1. Gemini (무료)
    2. OpenAI (유료)
    3. 규칙 기반 (폴백)
    
    Args:
        korean_keyword: 한국어 키워드
    
    Returns:
        str: 영어 키워드
    """
    from app import get_config
    
    prompt = f"""다음 한국어 이커머스 키워드를 알리익스프레스 검색용 영어로 번역해주세요.

한국어: {korean_keyword}

규칙:
1. 간단하고 명확한 영어 사용
2. 브랜드명 제외
3. 일반 제품 카테고리로 번역

예시:
- "차량용 USB 공기청정기" → "car usb air purifier"
- "반려동물 자동 급식기" → "automatic pet feeder"
- "무선 블루투스 이어폰" → "wireless bluetooth earphones"

응답: 영어 키워드만 작성 (소문자)"""

    # 1️⃣ Try Gemini
    gemini_key = get_config('gemini_api_key')
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)
            result = response.text.strip().lower()
            logger.info(f'[Translation] Gemini: {korean_keyword} → {result}')
            return result
        except Exception as e:
            logger.warning(f'[Translation] Gemini failed: {str(e)[:50]}')
    
    # 2️⃣ Try OpenAI
    openai_key = get_config('openai_api_key')
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Korean-English translator for e-commerce keywords."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=30,
                temperature=0.3
            )
            result = response.choices[0].message.content.strip().lower()
            logger.info(f'[Translation] OpenAI: {korean_keyword} → {result}')
            return result
        except Exception as e:
            logger.warning(f'[Translation] OpenAI failed: {str(e)[:50]}')
    
    # 3️⃣ Fallback: 규칙 기반
    from app import translate_to_english
    result = translate_to_english(korean_keyword)
    logger.info(f'[Translation] Rule-based: {korean_keyword} → {result}')
    return result


def is_brand_product(title):
    """
    브랜드 제품 여부 확인
    
    Args:
        title: 제품명
    
    Returns:
        bool: True if 브랜드 제품
    """
    # 유명 브랜드 리스트
    famous_brands = [
        # 식기/주방
        'lenox', 'wedgwood', 'royal doulton', 'noritake', 'villeroy', 'boch',
        # 전자
        'apple', 'samsung', 'lg', 'sony', 'bose', 'jbl',
        # 패션
        'nike', 'adidas', 'puma', 'gucci', 'prada', 'louis vuitton',
        # 화장품
        'chanel', 'dior', 'lancome', 'estee lauder',
    ]
    
    title_lower = title.lower()
    for brand in famous_brands:
        if brand in title_lower:
            return True
    
    return False


def match_aliexpress_suppliers(keyword_kr, naver_market_data, min_margin=25, max_results=20):
    """
    네이버 키워드로 알리익스프레스 공급자 찾기 (실시간 검증)
    
    Args:
        keyword_kr: 한국어 키워드
        naver_market_data: 네이버 시장 데이터
        min_margin: 최소 마진율 (기본 25%)
        max_results: 최대 결과 수
    
    Returns:
        dict: {
            'success': True/False,
            'keyword_kr': 한국어 키워드,
            'keyword_en': 영어 키워드,
            'naver_avg_price': 네이버 평균가,
            'matched_count': 매칭된 제품 수,
            'products': [...],
            'warnings': [...]
        }
    """
    logger.info(f'[AliMatch] Starting: {keyword_kr}')
    
    warnings = []
    
    # 1. 한→영 번역
    keyword_en = translate_to_english_ai(keyword_kr)
    logger.info(f'[AliMatch] Translated: {keyword_kr} → {keyword_en}')
    
    # 2. 알리익스프레스 검색
    try:
        ali_result = search_aliexpress_official(keyword_en, max_results=50)
    except Exception as e:
        logger.error(f'[AliMatch] AliExpress search failed: {str(e)}')
        return {
            'success': False,
            'error': f'알리익스프레스 검색 실패: {str(e)}',
            'keyword_kr': keyword_kr,
            'keyword_en': keyword_en
        }
    
    if not ali_result or not ali_result.get('products'):
        return {
            'success': False,
            'error': f'알리익스프레스에서 "{keyword_en}" 검색 결과가 없습니다.',
            'keyword_kr': keyword_kr,
            'keyword_en': keyword_en
        }
    
    naver_avg_price = naver_market_data.get('avg_price', 0)
    
    # 3. 각 제품 검증 및 마진 계산
    matched_products = []
    
    for product in ali_result['products']:
        price_usd = product.get('price', 0)
        title = product.get('title', '')
        
        if price_usd == 0:
            continue
        
        # 브랜드 제품 필터링
        if is_brand_product(title):
            logger.info(f'[AliMatch] Skipping brand product: {title[:50]}')
            continue
        
        # 드롭쉬핑 가능성 계산
        feasibility = calculate_dropship_feasibility(price_usd, naver_avg_price)
        
        # 최소 마진율 필터링
        if feasibility['margin_rate'] >= min_margin:
            matched_products.append({
                'title': title,
                'price_usd': price_usd,
                'price_krw': feasibility['cost_breakdown']['ali_price_krw'],
                'margin_rate': feasibility['margin_rate'],
                'profit_krw': feasibility['profit_krw'],
                'dropship_score': feasibility['score'],
                'naver_selling_price': naver_avg_price,
                'url': product.get('url', ''),
                'image': product.get('image', ''),
                'rating': product.get('rating', 0),
                'orders': product.get('orders', 0),
                'cost_breakdown': feasibility['cost_breakdown']
            })
    
    # 4. 드롭쉬핑 점수로 정렬
    matched_products.sort(key=lambda x: (x['dropship_score'], x['margin_rate']), reverse=True)
    
    # 5. 경고 메시지
    if len(matched_products) == 0:
        warnings.append('⚠️ 마진이 25% 이상인 제품을 찾을 수 없습니다.')
        warnings.append(f'💡 네이버 평균가(₩{naver_avg_price:,})가 너무 낮거나, 알리 가격이 너무 높습니다.')
    elif len(matched_products) < 5:
        warnings.append(f'⚠️ 매칭된 제품이 {len(matched_products)}개로 적습니다.')
        warnings.append('💡 더 일반적인 키워드로 검색해보세요.')
    
    logger.info(f'[AliMatch] Matched {len(matched_products)}/{len(ali_result["products"])} products')
    
    return {
        'success': True,
        'keyword_kr': keyword_kr,
        'keyword_en': keyword_en,
        'naver_avg_price': naver_avg_price,
        'total_searched': len(ali_result['products']),
        'matched_count': len(matched_products),
        'products': matched_products[:max_results],
        'warnings': warnings
    }
