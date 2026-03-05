"""
Product Matching Engine v2.0
알리익스프레스 ↔ 네이버 제품 매칭 엔진

핵심 기능:
1. 영문 → 한글 AI 번역 (Gemini → OpenAI → 규칙 기반)
2. 제품명 정제 (브랜드/모델명 제거, 핵심 키워드만 추출)
3. 카테고리 자동 분류 및 네이버 검색 필터링
4. 네이버 검색 결과 유사도 검증 (카테고리 미스매치 제외)
"""

import logging
import sqlite3
import re
from typing import Dict, List, Optional, Tuple

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


# ============================================================================
# 1. 영문 → 한글 AI 번역 (Gemini → OpenAI → 규칙 기반)
# ============================================================================

def translate_english_to_korean(english_text: str) -> str:
    """
    영문 제품명/키워드 → 한글 키워드 변환
    
    Args:
        english_text: 영문 제품명 (예: "Bicycle Phone Holder")
    
    Returns:
        한글 키워드 (예: "자전거 휴대폰 거치대")
    """
    import google.generativeai as genai
    import openai
    
    # 1단계: Gemini API 시도 (무료, 1,500 calls/day)
    gemini_key = get_config('gemini_api_key')
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""Translate this English product name to Korean for Naver shopping search.
Output ONLY the Korean keyword, nothing else.

Rules:
1. Focus on product category and function
2. Remove brand names and model numbers
3. Use common Korean shopping terms
4. Keep it concise (2-5 words)

Examples:
"Bicycle Phone Holder" → "자전거 휴대폰 거치대"
"Car Air Purifier USB" → "차량용 공기청정기"
"Wireless Bluetooth Earphones" → "무선 블루투스 이어폰"
"Automatic Pet Feeder" → "반려동물 자동 급식기"

English: {english_text}
Korean:"""
            
            response = model.generate_content(prompt)
            korean = response.text.strip()
            
            logger.info(f"[ENG→KOR Gemini] ✅ {english_text} → {korean}")
            return korean
            
        except Exception as e:
            logger.warning(f"[ENG→KOR Gemini] ❌ Failed: {e}")
    
    # 2단계: OpenAI GPT-4o-mini 시도 (유료)
    openai_key = get_config('openai_api_key')
    if openai_key:
        try:
            openai.api_key = openai_key
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""Translate this English product name to Korean for shopping search.
Output ONLY the Korean keyword.

English: {english_text}
Korean:"""
                }],
                max_tokens=30,
                temperature=0.3
            )
            
            korean = response.choices[0].message.content.strip()
            logger.info(f"[ENG→KOR OpenAI] ✅ {english_text} → {korean}")
            return korean
            
        except Exception as e:
            logger.warning(f"[ENG→KOR OpenAI] ❌ Failed: {e}")
    
    # 3단계: 규칙 기반 매핑 (100% 폴백)
    translation_map = {
        # 🔧 복합어 우선 매칭 (순서 중요!)
        'hair dryer': '헤어 드라이어',
        'power bank': '보조배터리',
        'air purifier': '공기청정기',
        'phone holder': '휴대폰 거치대',
        'car charger': '차량용 충전기',
        'bluetooth speaker': '블루투스 스피커',
        'pet feeder': '반려동물 급식기',
        'fan blade': '선풍기 날개',  # 🔧 추가
        
        # 전자제품
        'phone': '휴대폰',
        'mobile': '휴대폰',
        'holder': '거치대',
        'mount': '거치대',
        'stand': '거치대',
        'charger': '충전기',
        'cable': '케이블',
        'adapter': '어댑터',
        'earphone': '이어폰',
        'earphones': '이어폰',
        'headphone': '헤드폰',
        'speaker': '스피커',
        'bluetooth': '블루투스',
        'wireless': '무선',
        'keyboard': '키보드',
        'mouse': '마우스',
        'dryer': '드라이어',  # 🔧 추가
        'diffuser': '디퓨저',  # 🔧 추가
        'blower': '블로워',  # 🔧 추가
        
        # 차량용품
        'car': '차량용',
        'vehicle': '차량용',
        'automobile': '자동차',
        'motorcycle': '오토바이',
        'bike': '자전거',
        'bicycle': '자전거',
        
        # 가전제품
        'humidifier': '가습기',
        # 'fan': '선풍기',  # 🔧 제거: "hair dryer fan"을 "선풍기"로 오역 방지
        'heater': '히터',
        'vacuum': '청소기',
        'cleaner': '청소기',
        'washer': '세척기',
        
        # 생활용품
        'organizer': '정리함',
        'storage': '수납',
        'bag': '가방',
        'case': '케이스',
        'cover': '커버',
        'clip': '집게',  # 🔧 추가
        'eyebrow': '눈썹',  # 🔧 추가
        'switch': '스위치',  # 🔧 추가
        'rocker': '로커',  # 🔧 추가
        'control': '제어',  # 🔧 추가
        
        # 반려동물
        'pet': '반려동물',
        'dog': '강아지',
        'cat': '고양이',
        'feeder': '급식기',
        'bowl': '밥그릇',
        
        # 형용사
        'automatic': '자동',
        'smart': '스마트',
        'portable': '휴대용',
        'mini': '미니',
        'small': '소형',  # 🔧 추가
        'usb': 'USB',
        'high pressure': '고압',
        'waterproof': '방수',
        'plastic': '플라스틱',  # 🔧 추가
    }
    
    # 영문 소문자 변환
    text_lower = english_text.lower()
    
    # 🔧 복합어 우선 매칭 (긴 구문부터)
    korean_words = []
    matched_positions = []  # 매칭된 위치 저장
    
    # 복합어 먼저 찾기 (예: "hair dryer" > "hair", "dryer")
    for eng, kor in sorted(translation_map.items(), key=lambda x: -len(x[0])):
        if eng in text_lower:
            # 이미 매칭된 부분이 아닌지 확인
            pos = text_lower.find(eng)
            if not any(start <= pos < end or start < pos + len(eng) <= end 
                      for start, end in matched_positions):
                korean_words.append(kor)
                matched_positions.append((pos, pos + len(eng)))
    
    # 🔧 키워드가 없으면 AI 재시도 (Gemini만, 빠르게)
    if not korean_words:
        gemini_key = get_config('gemini_api_key')
        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""Translate to Korean shopping keyword (output ONLY Korean, no explanation):
{english_text}"""
                
                response = model.generate_content(prompt)
                korean = response.text.strip()
                logger.info(f"[ENG→KOR RuleBased→Gemini Retry] ✅ {english_text} → {korean}")
                return korean
            except Exception as e:
                logger.warning(f"[ENG→KOR Gemini Retry] ❌ {e}")
    
    korean = ' '.join(korean_words) if korean_words else english_text
    logger.info(f"[ENG→KOR RuleBased] {'✅' if korean_words else '⚠️'} {english_text} → {korean}")
    return korean


# ============================================================================
# 2. 제품명 정제 (브랜드/모델명 제거, 핵심 키워드만 추출)
# ============================================================================

def clean_product_title(title: str) -> str:
    """
    제품명에서 불필요한 정보 제거 후 핵심 키워드만 추출
    
    Args:
        title: 원본 제품명 (예: "Bicycle Accessories Mobile Cellphone Holder Stand For Motorcycle MTB 3.5-7.2inch Phone Bracket Support GPS")
    
    Returns:
        정제된 키워드 (예: "Bicycle Phone Holder")
    """
    # 🔧 먼저 주요 카테고리 키워드 추출 (맥락 보존)
    category_patterns = {
        'hair dryer': ['hair dryer', 'hairdryer', 'hair blower'],
        'phone holder': ['phone holder', 'phone mount', 'phone stand'],
        'car charger': ['car charger', 'vehicle charger'],
        'power bank': ['power bank', 'portable charger'],
        'bluetooth speaker': ['bluetooth speaker', 'wireless speaker'],
        'air purifier': ['air purifier', 'air cleaner'],
        'pet feeder': ['pet feeder', 'automatic feeder'],
    }
    
    title_lower = title.lower()
    main_category = None
    
    for category, patterns in category_patterns.items():
        for pattern in patterns:
            if pattern in title_lower:
                main_category = category
                break
        if main_category:
            break
    
    # 제거할 패턴들
    patterns_to_remove = [
        r'\b[A-Z0-9]{2,}\d+[A-Z0-9]*\b',  # 모델명 제거 (P82E, XYZ123 등)
        r'\b\d+[\.\-~]\d+\s*(inch|mm|cm|kg|g|oz|lb)\b',  # 크기/무게
        r'\b\d+\s*(piece|pcs|lot|set|pack|pcs|pc)\b',  # 수량
        r'\bfor\s+\w+\b',  # "for MTB", "for motorcycle" 등
        r'\b(mtb|gps|support|bracket|accessories|replacement|small|power)\b',  # 불필요 단어
        r'\bmobile\b',  # mobile (중복)
        r'\bcellphone\b',  # cellphone (phone과 중복)
    ]
    
    cleaned = title
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # 연속된 공백 제거
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # 🔧 주요 카테고리가 있으면 우선 사용
    if main_category:
        # 카테고리 + 추가 키워드 (예: "hair dryer diffuser")
        words = cleaned.split()
        additional_words = [w for w in words if w.lower() not in main_category.split()][:2]
        if additional_words:
            cleaned = f"{main_category} {' '.join(additional_words)}"
        else:
            cleaned = main_category
    else:
        # 핵심 키워드만 추출 (앞 3-4개 단어)
        words = cleaned.split()
        if len(words) > 4:
            cleaned = ' '.join(words[:4])
    
    logger.info(f"[Clean Title] {title[:50]}... → {cleaned}")
    return cleaned


# ============================================================================
# 3. 카테고리 자동 분류
# ============================================================================

CATEGORY_KEYWORDS = {
    '자전거': ['bicycle', 'bike', 'cycling', 'mtb', 'bmx'],
    '차량용품': ['car', 'vehicle', 'automobile', 'automotive'],
    '오토바이': ['motorcycle', 'motorbike', 'scooter'],
    '휴대폰액세서리': ['phone', 'mobile', 'cellphone', 'smartphone'],
    '전자제품': ['electronic', 'digital', 'usb', 'charger', 'cable', 'adapter'],
    '가전제품': ['appliance', 'air purifier', 'humidifier', 'vacuum', 'cleaner'],
    '컴퓨터': ['computer', 'laptop', 'keyboard', 'mouse', 'monitor'],
    '오디오': ['speaker', 'headphone', 'earphone', 'bluetooth', 'audio'],
    '반려동물': ['pet', 'dog', 'cat', 'animal', 'feeder'],
    '스포츠': ['sport', 'fitness', 'exercise', 'outdoor'],
    '가방': ['bag', 'backpack', 'handbag', 'luggage'],
    '의류': ['clothing', 'shirt', 't-shirt', 'pants', 'jacket'],
    '신발': ['shoes', 'sneakers', 'boots', 'sandals'],
    '악세서리': ['jewelry', 'necklace', 'bracelet', 'ring', 'earring'],
    '주방': ['kitchen', 'cookware', 'utensil', 'tableware'],
    '욕실': ['bathroom', 'shower', 'toilet', 'towel'],
    '침구': ['bedding', 'pillow', 'blanket', 'sheet'],
    '가구': ['furniture', 'chair', 'table', 'desk', 'shelf'],
    '조명': ['light', 'lamp', 'led', 'bulb'],
    '공구': ['tool', 'wrench', 'screwdriver', 'hammer'],
}


def classify_category(title: str) -> str:
    """
    제품명으로 카테고리 자동 분류
    
    Args:
        title: 제품명 (영문)
    
    Returns:
        카테고리 (한글)
    """
    title_lower = title.lower()
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                logger.info(f"[Category] {title[:50]}... → {category}")
                return category
    
    logger.info(f"[Category] {title[:50]}... → 기타")
    return '기타'


# ============================================================================
# 4. 네이버 검색 결과 유사도 검증
# ============================================================================

def calculate_category_similarity(ali_category: str, naver_title: str) -> float:
    """
    알리 제품 카테고리 vs 네이버 제품명 유사도 계산
    
    Args:
        ali_category: 알리 제품의 카테고리 (예: "자전거")
        naver_title: 네이버 제품명 (예: "남성 양말 10켤레")
    
    Returns:
        유사도 (0.0 ~ 1.0)
    """
    # 카테고리 키워드 추출
    if ali_category not in CATEGORY_KEYWORDS:
        return 0.5  # 알 수 없으면 중립
    
    category_keywords = CATEGORY_KEYWORDS[ali_category]
    naver_lower = naver_title.lower()
    
    # 키워드 매칭 체크
    matched = 0
    for keyword in category_keywords:
        if keyword in naver_lower:
            matched += 1
    
    # 한글 키워드도 체크
    if ali_category in naver_title:
        matched += 2
    
    # 점수 계산
    if matched >= 2:
        return 1.0  # 완전 매칭
    elif matched == 1:
        return 0.7  # 부분 매칭
    else:
        return 0.0  # 미스매치
    
    
def is_category_mismatch(ali_title: str, naver_title: str, threshold: float = 0.5) -> bool:
    """
    카테고리 미스매치 여부 확인
    
    Args:
        ali_title: 알리익스프레스 제품명
        naver_title: 네이버 제품명
        threshold: 유사도 임계값 (기본 0.5)
    
    Returns:
        True if 미스매치 (제외해야 함)
    """
    ali_category = classify_category(ali_title)
    similarity = calculate_category_similarity(ali_category, naver_title)
    
    is_mismatch = similarity < threshold
    
    if is_mismatch:
        logger.warning(f"[Category Mismatch] Ali({ali_category}): {ali_title[:40]}... vs Naver: {naver_title[:40]}... (similarity: {similarity:.2f})")
    
    return is_mismatch


# ============================================================================
# 5. 통합 매칭 함수
# ============================================================================

def match_aliexpress_to_naver(ali_title: str, naver_results: List[Dict]) -> Dict:
    """
    알리익스프레스 제품 → 네이버 시장 분석 (개선된 버전)
    
    Args:
        ali_title: 알리익스프레스 제품명 (영문)
        naver_results: 네이버 검색 결과 리스트
    
    Returns:
        {
            'success': True/False,
            'ali_title_original': 원본 제품명,
            'ali_title_cleaned': 정제된 제품명,
            'ali_category': 카테고리,
            'search_keyword_kr': 한글 검색 키워드,
            'naver_total': 네이버 전체 결과 수,
            'naver_matched': 카테고리 매칭된 결과 수,
            'naver_filtered': 필터링 후 최종 결과 수,
            'naver_avg_price': 평균 가격,
            'naver_products': 최종 제품 리스트,
            'warnings': 경고 메시지 리스트
        }
    """
    logger.info(f"[AliMatch v2.0] Starting: {ali_title[:60]}...")
    
    warnings = []
    
    # Step 1: 제품명 정제
    ali_title_cleaned = clean_product_title(ali_title)
    
    # Step 2: 카테고리 분류
    ali_category = classify_category(ali_title_cleaned)
    
    # Step 3: 영문 → 한글 번역
    search_keyword_kr = translate_english_to_korean(ali_title_cleaned)
    
    logger.info(f"[AliMatch] Cleaned: {ali_title_cleaned}")
    logger.info(f"[AliMatch] Category: {ali_category}")
    logger.info(f"[AliMatch] Korean: {search_keyword_kr}")
    
    # Step 4: 네이버 결과 필터링
    filtered_products = []
    
    for product in naver_results:
        naver_title = product.get('title', '')
        
        # 카테고리 유사도 체크
        if is_category_mismatch(ali_title_cleaned, naver_title):
            continue  # 미스매치 제외
        
        filtered_products.append(product)
    
    # Step 5: 가격 계산
    if filtered_products:
        prices = [p.get('lprice', 0) for p in filtered_products if p.get('lprice', 0) > 0]
        avg_price = sum(prices) // len(prices) if prices else 0
    else:
        avg_price = 0
        warnings.append('⚠️ 카테고리가 일치하는 네이버 제품을 찾을 수 없습니다.')
        warnings.append(f'💡 알리 카테고리: {ali_category}, 검색 키워드: {search_keyword_kr}')
    
    # Step 6: 경고 메시지
    if len(naver_results) > 0 and len(filtered_products) == 0:
        warnings.append('🚫 네이버 검색 결과가 있지만 카테고리가 모두 미스매치됩니다.')
        warnings.append(f'📊 전체 결과: {len(naver_results)}개, 매칭: 0개')
    elif len(filtered_products) < 10:
        warnings.append(f'⚠️ 매칭된 제품이 {len(filtered_products)}개로 적습니다.')
        warnings.append('💡 더 일반적인 키워드로 재검색을 추천합니다.')
    
    logger.info(f"[AliMatch] Results: {len(naver_results)} → {len(filtered_products)} (filtered)")
    
    return {
        'success': len(filtered_products) > 0,
        'ali_title_original': ali_title,
        'ali_title_cleaned': ali_title_cleaned,
        'ali_category': ali_category,
        'search_keyword_kr': search_keyword_kr,
        'naver_total': len(naver_results),
        'naver_matched': len(filtered_products),
        'naver_filtered': len(filtered_products),
        'naver_avg_price': avg_price,
        'naver_products': filtered_products[:50],  # 최대 50개
        'warnings': warnings
    }
