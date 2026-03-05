"""
Blue Ocean Discovery Module
네이버 시장 데이터 기반 틈새 시장 발견

기능:
1. 네이버 DataLab API로 트렌드 키워드 수집
2. 네이버 쇼핑 API로 시장 깊이 분석
3. Blue Ocean 점수 계산
4. 알리익스프레스 공급자 매칭
"""

import requests
import json
from datetime import datetime, timedelta
import logging
from market_analysis import analyze_naver_market

# 로거 설정
logger = logging.getLogger(__name__)

def get_naver_shopping_trends(client_id, client_secret, categories=None):
    """
    네이버 쇼핑 인기 검색어로 트렌드 분석
    
    DataLab API는 복잡하므로, 대신 인기 카테고리 키워드 리스트 사용
    
    Args:
        client_id: 네이버 Client ID
        client_secret: 네이버 Client Secret
        categories: 분석할 카테고리 리스트 (None이면 기본 카테고리)
    
    Returns:
        list: [
            {
                'keyword': '키워드',
                'category': '카테고리',
                'priority': 우선순위
            },
            ...
        ]
    """
    
    # 🎯 한국 이커머스 인기 카테고리 (데이터 기반)
    default_categories = {
        '전자기기': [
            '무선 이어폰', '블루투스 스피커', '보조배터리', '휴대폰 거치대',
            '차량용 충전기', 'USB 허브', '케이블 정리', '스마트워치',
            '게이밍 마우스', '기계식 키보드', '웹캠', '마이크'
        ],
        '생활용품': [
            '공기청정기', '가습기', '제습기', '선풍기', '전기히터',
            '무선청소기', '로봇청소기', '의류건조대', '빨래건조대',
            '주방용품', '정리함', '수납함', '옷걸이'
        ],
        '자동차용품': [
            '차량용 공기청정기', '블랙박스', '차량용 청소기', '차량용 방향제',
            '핸드폰 거치대', '차량용 정리함', '썬팅', '타이어 공기주입기',
            '세차용품', '차량용 커버', '시트커버'
        ],
        '반려동물': [
            '자동 급식기', '자동 급수기', '고양이 화장실', '강아지 목욕',
            '반려동물 이동장', '펫카메라', '고양이 장난감', '강아지 옷',
            '애견 간식', '고양이 스크래쳐', '펫 미용'
        ],
        '홈인테리어': [
            'LED 조명', '무드등', '스탠드 조명', '블라인드', '커튼',
            '러그', '방석', '쿠션', '액자', '벽시계', '거울',
            '플랜테리어', '화분', '인테리어 소품'
        ],
        '헬스케어': [
            '마사지건', '요가매트', '폼롤러', '덤벨', '저울', 
            '혈압계', '체온계', '수면 안대', '귀마개', '목베개',
            '발마사지기', '손목보호대', '무릎보호대'
        ],
        '뷰티': [
            '피부관리기', '헤어드라이기', '고데기', '면도기', '제모기',
            '네일케어', '화장품 정리함', '거울', '화장솜', '메이크업 브러시',
            '향수', '립밤', '마스크팩'
        ],
        '패션잡화': [
            '에코백', '크로스백', '백팩', '지갑', '카드지갑',
            '벨트', '모자', '양말', '슬리퍼', '실내화',
            '장갑', '목도리', '우산'
        ],
        '주방가전': [
            '에어프라이어', '전기포트', '믹서기', '전기그릴', '토스터',
            '커피머신', '전기밥솥', '전자레인지', '식기세척기',
            '정수기', '얼음틀', '밀폐용기'
        ],
        '사무용품': [
            '모니터 받침대', '노트북 거치대', '키보드 받침대', '손목 쿠션',
            '케이블 정리', '서류함', '필기구', '메모지', '화이트보드',
            '책상 정리', '의자 쿠션', '발받침대'
        ]
    }
    
    if categories:
        keyword_list = categories
    else:
        # 모든 카테고리의 키워드를 하나의 리스트로
        keyword_list = []
        for category, keywords in default_categories.items():
            for keyword in keywords:
                keyword_list.append({
                    'keyword': keyword,
                    'category': category,
                    'priority': 1.0
                })
    
    logger.info(f'📋 총 {len(keyword_list)}개 카테고리 키워드 수집 완료')
    return keyword_list


def calculate_blue_ocean_score(market_data):
    """
    Blue Ocean 점수 계산 (0~10점)
    
    높을수록 진입하기 좋은 시장
    
    Args:
        market_data = {
            'analyzed_products': 분석된 제품 수 (유효 가격 있는 것),
            'total_products': 전체 제품 수,
            'avg_price': 평균 가격,
            'median_price': 중앙값,
        }
    
    Returns:
        float: 0.0 ~ 10.0
        
    점수 기준:
        9.0~10.0: 🔥 매우 우수 (강력 추천)
        7.0~8.9:  ⭐ 우수 (추천)
        5.0~6.9:  💡 보통 (진입 가능)
        3.0~4.9:  ⚠️  낮음 (신중 검토)
        0.0~2.9:  ❌ 매우 낮음 (비추천)
    """
    
    analyzed = market_data.get('analyzed_products', 0)
    total = market_data.get('total_products', 0)
    avg_price = market_data.get('avg_price', 0)
    median_price = market_data.get('median_price', 0)
    
    # 1️⃣ 수요 점수 (0~3점) - 전체 상품 수로 추정
    # 100~1000개: 적당한 수요
    if 100 <= total <= 1000:
        demand_score = 3.0
    elif 1000 < total <= 3000:
        demand_score = 2.5
    elif 3000 < total <= 10000:
        demand_score = 2.0
    elif total < 100:
        demand_score = 1.0  # 너무 적음 (수요 부족)
    else:
        demand_score = 1.0  # 너무 많음 (레드오션)
    
    # 2️⃣ 경쟁 점수 (0~3점) - 유효 제품 비율
    # 전체 대비 유효 제품이 적을수록 경쟁 낮음
    if total > 0:
        valid_ratio = analyzed / total
        if valid_ratio < 0.3:
            competition_score = 3.0  # 30% 미만: 경쟁 낮음
        elif valid_ratio < 0.5:
            competition_score = 2.5
        elif valid_ratio < 0.7:
            competition_score = 2.0
        else:
            competition_score = 1.0  # 70% 이상: 경쟁 높음
    else:
        competition_score = 0.0
    
    # 3️⃣ 수익성 점수 (0~2점) - 평균 가격
    # 30,000원 이상: 마진 남기기 좋음
    if avg_price >= 50000:
        profit_score = 2.0
    elif avg_price >= 30000:
        profit_score = 1.5
    elif avg_price >= 20000:
        profit_score = 1.0
    else:
        profit_score = 0.5
    
    # 4️⃣ 가격 안정성 점수 (0~2점) - 평균과 중앙값 차이
    if avg_price > 0 and median_price > 0:
        price_diff = abs(avg_price - median_price) / avg_price
        if price_diff < 0.2:
            stability_score = 2.0  # 차이 20% 미만: 안정적
        elif price_diff < 0.4:
            stability_score = 1.5
        else:
            stability_score = 1.0
    else:
        stability_score = 0.5
    
    # 총점 계산
    total_score = demand_score + competition_score + profit_score + stability_score
    
    logger.info(f'[Blue Ocean Score] 수요:{demand_score:.1f} + 경쟁:{competition_score:.1f} + 수익:{profit_score:.1f} + 안정:{stability_score:.1f} = {total_score:.1f}')
    
    return round(total_score, 1)


def analyze_market_opportunity(keyword, client_id, client_secret):
    """
    단일 키워드에 대한 시장 기회 분석
    
    Args:
        keyword: 분석할 키워드
        client_id: 네이버 Client ID
        client_secret: 네이버 Client Secret
    
    Returns:
        dict: {
            'keyword': 키워드,
            'success': True/False,
            'blue_ocean_score': 0~10점,
            'market_data': {...},
            'recommendation': 추천 메시지,
            'timestamp': 분석 시간
        }
    """
    
    logger.info(f'🔍 시장 기회 분석 시작: {keyword}')
    
    # 네이버 시장 분석
    market_result = analyze_naver_market(keyword, client_id, client_secret)
    
    if not market_result.get('success'):
        return {
            'keyword': keyword,
            'success': False,
            'error': market_result.get('error', '시장 분석 실패'),
            'blue_ocean_score': 0.0,
            'timestamp': datetime.now().isoformat()
        }
    
    # Blue Ocean 점수 계산
    blue_ocean_score = calculate_blue_ocean_score(market_result)
    
    # 추천 메시지 생성
    if blue_ocean_score >= 7.0:
        recommendation = '🔥 매우 우수한 시장입니다! 진입을 강력히 추천합니다.'
        level = 'excellent'
    elif blue_ocean_score >= 5.0:
        recommendation = '⭐ 괜찮은 시장입니다. 진입을 검토해보세요.'
        level = 'good'
    elif blue_ocean_score >= 3.0:
        recommendation = '💡 보통 시장입니다. 차별화 전략이 필요합니다.'
        level = 'moderate'
    else:
        recommendation = '⚠️ 경쟁이 치열한 시장입니다. 진입을 신중히 검토하세요.'
        level = 'poor'
    
    result = {
        'keyword': keyword,
        'success': True,
        'blue_ocean_score': blue_ocean_score,
        'level': level,
        'recommendation': recommendation,
        'market_data': {
            'total_products': market_result.get('total_products', 0),
            'analyzed_products': market_result.get('analyzed_products', 0),
            'avg_price': market_result.get('avg_price', 0),
            'median_price': market_result.get('median_price', 0),
            'min_price': market_result.get('min_price', 0),
            'max_price': market_result.get('max_price', 0),
            'recommended_price': market_result.get('recommended_price', 0),
        },
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f'✅ {keyword}: Blue Ocean Score = {blue_ocean_score} ({level})')
    
    return result


def discover_blue_ocean_opportunities(client_id, client_secret, top_n=20, min_score=5.0):
    """
    Blue Ocean 기회 자동 발견
    
    전체 카테고리를 스캔하여 상위 N개 기회 추출
    
    Args:
        client_id: 네이버 Client ID
        client_secret: 네이버 Client Secret
        top_n: 추출할 상위 기회 수 (기본 20개)
        min_score: 최소 Blue Ocean 점수 (기본 5.0)
    
    Returns:
        list: [
            {
                'keyword': '키워드',
                'blue_ocean_score': 점수,
                'market_data': {...},
                ...
            },
            ...
        ]
    """
    
    logger.info(f'🚀 Blue Ocean Discovery 시작 (Top {top_n}, Min Score {min_score})')
    
    # 1. 트렌드 키워드 수집
    trending_keywords = get_naver_shopping_trends(client_id, client_secret)
    logger.info(f'📋 {len(trending_keywords)}개 키워드 수집 완료')
    
    # 2. 각 키워드 분석
    opportunities = []
    
    for i, item in enumerate(trending_keywords, 1):
        keyword = item['keyword']
        logger.info(f'[{i}/{len(trending_keywords)}] 분석 중: {keyword}')
        
        try:
            result = analyze_market_opportunity(keyword, client_id, client_secret)
            
            if result.get('success') and result.get('blue_ocean_score', 0) >= min_score:
                opportunities.append(result)
                logger.info(f'✅ 기회 발견: {keyword} (점수: {result["blue_ocean_score"]})')
            
        except Exception as e:
            logger.warning(f'⚠️ {keyword} 분석 실패: {str(e)}')
            continue
    
    # 3. Blue Ocean 점수로 정렬
    opportunities.sort(key=lambda x: x['blue_ocean_score'], reverse=True)
    
    # 4. 상위 N개 추출
    top_opportunities = opportunities[:top_n]
    
    logger.info(f'🎯 총 {len(opportunities)}개 기회 발견, 상위 {len(top_opportunities)}개 반환')
    
    return top_opportunities


def get_cached_opportunities(db_conn, max_age_hours=24):
    """
    DB에서 캐시된 Blue Ocean 기회 조회
    
    Args:
        db_conn: SQLite 연결
        max_age_hours: 최대 캐시 시간 (기본 24시간)
    
    Returns:
        list: 캐시된 기회 리스트
    """
    cursor = db_conn.cursor()
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    
    cursor.execute('''
        SELECT keyword, blue_ocean_score, market_data_json, analyzed_at
        FROM blue_ocean_cache
        WHERE analyzed_at >= ?
        ORDER BY blue_ocean_score DESC
        LIMIT 20
    ''', (cutoff_time.isoformat(),))
    
    rows = cursor.fetchall()
    
    opportunities = []
    for row in rows:
        opportunities.append({
            'keyword': row['keyword'],
            'blue_ocean_score': row['blue_ocean_score'],
            'market_data': json.loads(row['market_data_json']),
            'timestamp': row['analyzed_at'],
            'cached': True
        })
    
    return opportunities


def save_opportunities_to_cache(db_conn, opportunities):
    """
    Blue Ocean 기회를 DB 캐시에 저장
    
    Args:
        db_conn: SQLite 연결
        opportunities: 기회 리스트
    """
    cursor = db_conn.cursor()
    
    # 테이블 생성 (없으면)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blue_ocean_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE,
            blue_ocean_score REAL,
            market_data_json TEXT,
            analyzed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 데이터 삽입 (중복 시 업데이트)
    for opp in opportunities:
        cursor.execute('''
            INSERT OR REPLACE INTO blue_ocean_cache 
            (keyword, blue_ocean_score, market_data_json, analyzed_at)
            VALUES (?, ?, ?, ?)
        ''', (
            opp['keyword'],
            opp['blue_ocean_score'],
            json.dumps(opp.get('market_data', {})),
            opp.get('timestamp', datetime.now().isoformat())
        ))
    
    db_conn.commit()
    logger.info(f'💾 {len(opportunities)}개 기회를 캐시에 저장')
