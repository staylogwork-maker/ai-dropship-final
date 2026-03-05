"""
Market Intelligence Module
===========================
쿠팡/네이버 시장 분석 및 OpenAI 기반 인사이트 생성

기능:
1. 쿠팡 파트너스 API - 베스트셀러, 판매량, 리뷰 데이터
2. 네이버 쇼핑 API - 리뷰 수, 평점, 판매 추이
3. OpenAI GPT-4 - 시장 트렌드 분석 및 수요 예측
4. 판매 가능성 예측 - AI 기반 점수 계산
"""

import requests
import hmac
import hashlib
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 쿠팡 파트너스 API - 베스트셀러 & 판매 데이터
# ============================================================================

class CoupangMarketAnalyzer:
    """쿠팡 시장 분석기"""
    
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = 'https://api-gateway.coupang.com'
        
    def _generate_signature(self, method: str, path: str, query: str = '') -> str:
        """쿠팡 API 서명 생성"""
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{method}{path}{query}"
        
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"{self.access_key}:{signature}:{timestamp}"
    
    def search_products(self, keyword: str, limit: int = 100) -> Dict:
        """
        쿠팡에서 키워드로 제품 검색 (판매량, 리뷰 포함)
        
        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수
            
        Returns:
            {
                'products': [
                    {
                        'product_id': 'xxx',
                        'title': '제품명',
                        'price': 10000,
                        'sales_count': 500,  # 판매량
                        'review_count': 150,  # 리뷰 수
                        'rating': 4.5,        # 평점
                        'rank': 1,            # 베스트셀러 순위
                        'category': '주방용품',
                        'image_url': 'https://...'
                    }
                ],
                'total_count': 100
            }
        """
        try:
            # 쿠팡 파트너스 API: 제품 검색
            path = '/v2/providers/affiliate_open_api/apis/openapi/v1/products/search'
            params = {
                'keyword': keyword,
                'limit': limit
            }
            query_string = urlencode(params)
            
            headers = {
                'Authorization': self._generate_signature('GET', path, query_string),
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}{path}?{query_string}"
            logger.info(f"[Coupang API] Searching for: {keyword}")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"[Coupang API] Error {response.status_code}: {response.text[:200]}")
                return {'products': [], 'total_count': 0, 'error': 'API error'}
            
            data = response.json()
            products = []
            
            # 응답 파싱
            for idx, item in enumerate(data.get('data', [])[:limit]):
                product = {
                    'product_id': item.get('productId', ''),
                    'title': item.get('productName', ''),
                    'price': item.get('productPrice', 0),
                    'sales_count': self._estimate_sales(item),  # 판매량 추정
                    'review_count': item.get('reviewCount', 0),
                    'rating': item.get('productRating', 0),
                    'rank': idx + 1,
                    'category': item.get('categoryName', ''),
                    'image_url': item.get('productImage', ''),
                    'url': item.get('productUrl', '')
                }
                products.append(product)
            
            logger.info(f"[Coupang API] Found {len(products)} products")
            
            return {
                'products': products,
                'total_count': len(products),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"[Coupang API] Exception: {str(e)}")
            return {'products': [], 'total_count': 0, 'error': str(e)}
    
    def _estimate_sales(self, item: Dict) -> int:
        """
        판매량 추정 (리뷰 수 기반)
        일반적으로 리뷰 비율은 1-5% 정도
        """
        review_count = item.get('reviewCount', 0)
        # 보수적으로 리뷰 비율 3%로 추정
        estimated_sales = int(review_count / 0.03) if review_count > 0 else 0
        return estimated_sales
    
    def get_bestsellers(self, category: str = 'all', limit: int = 50) -> Dict:
        """
        쿠팡 베스트셀러 조회
        
        Args:
            category: 카테고리 (all, kitchen, electronics, etc.)
            limit: 최대 결과 수
            
        Returns:
            베스트셀러 리스트
        """
        try:
            path = '/v2/providers/affiliate_open_api/apis/openapi/v1/products/bestcategories'
            params = {'limit': limit}
            
            if category != 'all':
                params['categoryId'] = self._get_category_id(category)
            
            query_string = urlencode(params)
            
            headers = {
                'Authorization': self._generate_signature('GET', path, query_string),
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}{path}?{query_string}"
            logger.info(f"[Coupang API] Getting bestsellers: {category}")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"[Coupang API] Bestseller error: {response.status_code}")
                return {'products': [], 'error': 'API error'}
            
            data = response.json()
            products = []
            
            for idx, item in enumerate(data.get('data', [])[:limit]):
                product = {
                    'product_id': item.get('productId', ''),
                    'title': item.get('productName', ''),
                    'price': item.get('productPrice', 0),
                    'sales_count': self._estimate_sales(item),
                    'review_count': item.get('reviewCount', 0),
                    'rating': item.get('productRating', 0),
                    'rank': idx + 1,
                    'category': category,
                    'bestseller': True
                }
                products.append(product)
            
            logger.info(f"[Coupang API] Found {len(products)} bestsellers")
            
            return {
                'products': products,
                'total_count': len(products),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"[Coupang API] Bestseller exception: {str(e)}")
            return {'products': [], 'error': str(e)}
    
    def _get_category_id(self, category: str) -> str:
        """카테고리명 → 카테고리 ID 매핑"""
        category_map = {
            'kitchen': '029834',
            'electronics': '029999',
            'home': '029834',
            'beauty': '029999',
            'sports': '029999'
        }
        return category_map.get(category, '029834')


# ============================================================================
# 2. 네이버 쇼핑 API 확장 - 리뷰 & 판매 추이
# ============================================================================

class NaverMarketAnalyzer:
    """네이버 쇼핑 시장 분석기 (확장)"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = 'https://openapi.naver.com/v1/search/shop.json'
    
    def search_with_analytics(self, keyword: str, display: int = 100) -> Dict:
        """
        네이버 쇼핑 검색 + 상세 분석
        
        Returns:
            {
                'products': [...],
                'market_summary': {
                    'avg_price': 15000,
                    'avg_review_count': 50,
                    'avg_rating': 4.2,
                    'total_sellers': 80,
                    'competition_level': 'medium'  # low/medium/high
                }
            }
        """
        try:
            headers = {
                'X-Naver-Client-Id': self.client_id,
                'X-Naver-Client-Secret': self.client_secret
            }
            
            params = {
                'query': keyword,
                'display': display,
                'sort': 'sim'  # 정확도순
            }
            
            logger.info(f"[Naver API] Searching: {keyword}")
            
            response = requests.get(self.base_url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"[Naver API] Error {response.status_code}")
                return {'products': [], 'error': 'API error'}
            
            data = response.json()
            items = data.get('items', [])
            
            products = []
            total_price = 0
            total_reviews = 0
            
            for item in items:
                # HTML 태그 제거
                title = self._clean_html(item.get('title', ''))
                price = int(item.get('lprice', 0))
                
                product = {
                    'title': title,
                    'price': price,
                    'link': item.get('link', ''),
                    'image': item.get('image', ''),
                    'mall_name': item.get('mallName', ''),
                    'product_id': item.get('productId', ''),
                    'category': item.get('category1', '')
                }
                
                products.append(product)
                total_price += price
            
            # 시장 요약
            market_summary = {
                'avg_price': int(total_price / len(products)) if products else 0,
                'price_range': {
                    'min': min([p['price'] for p in products]) if products else 0,
                    'max': max([p['price'] for p in products]) if products else 0
                },
                'total_sellers': len(products),
                'competition_level': self._calculate_competition_level(len(products))
            }
            
            logger.info(f"[Naver API] Found {len(products)} products, avg price: ₩{market_summary['avg_price']:,}")
            
            return {
                'products': products,
                'market_summary': market_summary,
                'total_count': len(products),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"[Naver API] Exception: {str(e)}")
            return {'products': [], 'error': str(e)}
    
    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거"""
        import re
        clean = re.sub('<.*?>', '', text)
        return clean
    
    def _calculate_competition_level(self, seller_count: int) -> str:
        """경쟁 강도 계산"""
        if seller_count < 20:
            return 'low'
        elif seller_count < 50:
            return 'medium'
        else:
            return 'high'


# ============================================================================
# 3. OpenAI GPT-4 시장 분석 엔진
# ============================================================================

class AIMarketAnalyzer:
    """OpenAI 기반 시장 분석"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gpt-4o-mini"
    
    def analyze_market_opportunity(
        self, 
        keyword: str,
        coupang_data: Dict,
        naver_data: Dict,
        aliexpress_price: float
    ) -> Dict:
        """
        시장 기회 종합 분석
        
        Args:
            keyword: 제품 키워드
            coupang_data: 쿠팡 데이터
            naver_data: 네이버 데이터
            aliexpress_price: AliExpress 가격
            
        Returns:
            {
                'recommendation_score': 85,  # 0-100점
                'market_demand': 'high',     # low/medium/high
                'competition': 'medium',      # low/medium/high
                'profit_potential': 'high',   # low/medium/high
                'trend_analysis': '여름 성수기 제품...',
                'risks': ['경쟁 많음', '...'],
                'opportunities': ['높은 수요', '...'],
                'detailed_report': '상세 분석 보고서...'
            }
        """
        try:
            import openai
            openai.api_key = self.api_key
            
            # 데이터 요약
            coupang_summary = self._summarize_coupang(coupang_data)
            naver_summary = self._summarize_naver(naver_data)
            
            # GPT-4 프롬프트
            prompt = f"""
당신은 월 5억 이상 매출을 내는 대한민국 최고의 이커머스 전문가입니다.
다음 데이터를 분석하여 이 제품의 드롭쉬핑 사업성을 평가해주세요.

📦 제품 키워드: {keyword}

📊 쿠팡 시장 데이터:
{coupang_summary}

📊 네이버 시장 데이터:
{naver_summary}

💰 AliExpress 공급가: ${aliexpress_price:.2f}

🎯 분석 요청사항:
1. 시장 수요 분석 (high/medium/low)
2. 경쟁 강도 평가 (high/medium/low)
3. 수익성 잠재력 (high/medium/low)
4. 계절성/트렌드 분석
5. 리스크 요인 (3가지)
6. 기회 요인 (3가지)
7. 종합 추천 점수 (0-100점)
8. 상세 분석 보고서 (200자 이내)

응답 형식 (JSON):
{{
    "recommendation_score": 85,
    "market_demand": "high",
    "competition": "medium",
    "profit_potential": "high",
    "trend_analysis": "여름 성수기 진입으로 수요 급증 예상. 최근 3개월간 검색량 40% 증가.",
    "risks": ["경쟁사 다수", "가격 민감도 높음", "계절 상품"],
    "opportunities": ["높은 재구매율", "SNS 마케팅 용이", "신규 시장 확대"],
    "detailed_report": "이 제품은 현재 쿠팡 베스트셀러 상위권에 위치하며, 월평균 500개 이상 판매되고 있습니다. 네이버 쇼핑에서도 80개 이상의 판매자가 경쟁 중이나, 평균 가격이 높아 저가 전략으로 진입 가능합니다. AliExpress 공급가 대비 마진율 40% 이상 확보 가능하며, 리뷰 평점 4.5점으로 품질 신뢰도가 높습니다. 여름 성수기를 앞두고 있어 지금이 진입 적기입니다."
}}
"""
            
            logger.info(f"[OpenAI] Analyzing market for: {keyword}")
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': '당신은 데이터 기반 의사결정을 하는 이커머스 전문가입니다. 항상 JSON 형식으로 답변합니다.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 파싱
            # 코드 블록 제거
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            analysis = json.loads(result_text)
            
            logger.info(f"[OpenAI] Analysis complete. Score: {analysis.get('recommendation_score', 0)}")
            
            return {
                **analysis,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"[OpenAI] Analysis failed: {str(e)}")
            return {
                'recommendation_score': 0,
                'error': str(e),
                'success': False
            }
    
    def _summarize_coupang(self, data: Dict) -> str:
        """쿠팡 데이터 요약"""
        if not data.get('products'):
            return "데이터 없음"
        
        products = data['products']
        top_3 = products[:3]
        
        summary = f"총 {len(products)}개 제품\n"
        summary += "베스트셀러 Top 3:\n"
        
        for idx, p in enumerate(top_3, 1):
            summary += f"{idx}. {p.get('title', 'N/A')[:30]} - ₩{p.get('price', 0):,} "
            summary += f"(판매: {p.get('sales_count', 0):,}개, 리뷰: {p.get('review_count', 0)}개, "
            summary += f"평점: {p.get('rating', 0):.1f}점)\n"
        
        return summary
    
    def _summarize_naver(self, data: Dict) -> str:
        """네이버 데이터 요약"""
        if not data.get('market_summary'):
            return "데이터 없음"
        
        summary_data = data['market_summary']
        
        summary = f"총 {summary_data.get('total_sellers', 0)}개 판매자\n"
        summary += f"평균 가격: ₩{summary_data.get('avg_price', 0):,}\n"
        summary += f"가격 범위: ₩{summary_data['price_range']['min']:,} ~ ₩{summary_data['price_range']['max']:,}\n"
        summary += f"경쟁 강도: {summary_data.get('competition_level', 'unknown')}\n"
        
        return summary


# ============================================================================
# 4. 통합 분석 함수
# ============================================================================

def analyze_product_market_intelligence(
    keyword: str,
    aliexpress_price: float,
    coupang_access_key: str,
    coupang_secret_key: str,
    naver_client_id: str,
    naver_client_secret: str,
    openai_api_key: str
) -> Dict:
    """
    제품 시장 인텔리전스 종합 분석
    
    Returns:
        {
            'success': True,
            'keyword': '실리콘 주방용품',
            'coupang_analysis': {...},
            'naver_analysis': {...},
            'ai_analysis': {...},
            'final_recommendation': {
                'score': 85,
                'verdict': 'strongly_recommend',  # strongly_recommend/recommend/neutral/not_recommend
                'summary': '상세 요약...'
            }
        }
    """
    logger.info(f"[Market Intelligence] Starting analysis for: {keyword}")
    
    # 1. 쿠팡 분석
    coupang_analyzer = CoupangMarketAnalyzer(coupang_access_key, coupang_secret_key)
    coupang_data = coupang_analyzer.search_products(keyword, limit=50)
    
    # 2. 네이버 분석
    naver_analyzer = NaverMarketAnalyzer(naver_client_id, naver_client_secret)
    naver_data = naver_analyzer.search_with_analytics(keyword, display=100)
    
    # 3. OpenAI 분석
    ai_analyzer = AIMarketAnalyzer(openai_api_key)
    ai_analysis = ai_analyzer.analyze_market_opportunity(
        keyword, coupang_data, naver_data, aliexpress_price
    )
    
    # 4. 최종 판단
    score = ai_analysis.get('recommendation_score', 0)
    
    if score >= 80:
        verdict = 'strongly_recommend'
    elif score >= 60:
        verdict = 'recommend'
    elif score >= 40:
        verdict = 'neutral'
    else:
        verdict = 'not_recommend'
    
    logger.info(f"[Market Intelligence] Analysis complete. Final score: {score}, Verdict: {verdict}")
    
    return {
        'success': True,
        'keyword': keyword,
        'coupang_analysis': coupang_data,
        'naver_analysis': naver_data,
        'ai_analysis': ai_analysis,
        'final_recommendation': {
            'score': score,
            'verdict': verdict,
            'summary': ai_analysis.get('detailed_report', '')
        }
    }
