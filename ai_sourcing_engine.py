#!/usr/bin/env python3
"""
AI Sourcing Engine - Complete AI-Powered Dropshipping System
Integrates Coupang + Naver + OpenAI for intelligent product recommendations
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import all necessary modules
from ai_market_analyzer import AIMarketAnalyzer
from coupang_api import analyze_coupang_market
from naver_api_enhanced import analyze_naver_market_enhanced
from product_matcher import clean_product_title, translate_english_to_korean

logger = logging.getLogger(__name__)


class AISourcer:
    """
    Complete AI-powered sourcing system
    
    Workflow:
    1. Search AliExpress for products
    2. Analyze Coupang market (sales, reviews, ratings)
    3. Analyze Naver market (competition, price trends)
    4. Use OpenAI GPT-4 for intelligent analysis
    5. Generate comprehensive recommendation reports
    """
    
    def __init__(
        self,
        openai_api_key: str,
        coupang_access_key: str = None,
        coupang_secret_key: str = None,
        naver_client_id: str = None,
        naver_client_secret: str = None
    ):
        """Initialize AI Sourcing Engine"""
        
        self.openai_api_key = openai_api_key
        self.coupang_access_key = coupang_access_key
        self.coupang_secret_key = coupang_secret_key
        self.naver_client_id = naver_client_id
        self.naver_client_secret = naver_client_secret
        
        # Initialize AI analyzer
        self.ai_analyzer = AIMarketAnalyzer(openai_api_key)
        
        logger.info("[AI Sourcer] ✅ Initialized")
        logger.info(f"  - OpenAI: {'✅' if openai_api_key else '❌'}")
        logger.info(f"  - Coupang: {'✅' if coupang_access_key else '❌'}")
        logger.info(f"  - Naver: {'✅' if naver_client_id else '❌'}")
    
    def analyze_product(
        self,
        product_info: Dict[str, Any],
        blue_ocean_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete AI analysis for a single product
        
        Args:
            product_info: AliExpress product data
            blue_ocean_category: Optional blue ocean category keyword
        
        Returns:
            Comprehensive analysis report with AI recommendations
        """
        
        product_title = product_info.get('title', 'Unknown')
        logger.info(f"[AI Sourcer] 🤖 Starting AI analysis for: {product_title[:50]}...")
        
        # Step 1: Generate Korean keyword
        korean_keyword = self._generate_korean_keyword(product_info, blue_ocean_category)
        
        if not korean_keyword:
            logger.error("[AI Sourcer] ❌ Failed to generate Korean keyword")
            return {
                'success': False,
                'error': 'Could not generate Korean keyword for market analysis',
                'product_title': product_title
            }
        
        logger.info(f"[AI Sourcer] 📝 Korean keyword: {korean_keyword}")
        
        # Step 2: Collect Coupang market data
        coupang_data = self._collect_coupang_data(korean_keyword)
        
        # Step 3: Collect Naver market data
        naver_data = self._collect_naver_data(korean_keyword)
        
        # Step 4: Calculate profitability
        profitability = self._calculate_profitability(product_info, naver_data)
        
        # Step 5: AI Market Demand Analysis
        logger.info("[AI Sourcer] 🧠 Running AI demand analysis...")
        demand_analysis = self.ai_analyzer.analyze_market_demand(
            product_info,
            coupang_data,
            naver_data
        )
        
        # Step 6: AI Competition Analysis
        logger.info("[AI Sourcer] 🧠 Running AI competition analysis...")
        competition_analysis = self.ai_analyzer.analyze_competition(
            product_info,
            coupang_data.get('products', []),
            naver_data.get('products', [])
        )
        
        # Step 7: AI Sales Prediction
        logger.info("[AI Sourcer] 🧠 Running AI sales prediction...")
        sales_prediction = self.ai_analyzer.predict_sales_potential(
            product_info,
            demand_analysis,
            competition_analysis,
            profitability
        )
        
        # Step 8: Generate Final Recommendation Report
        logger.info("[AI Sourcer] 📊 Generating final recommendation report...")
        recommendation = self.ai_analyzer.generate_recommendation_report(
            product_info,
            demand_analysis,
            competition_analysis,
            sales_prediction,
            profitability
        )
        
        # Compile complete analysis
        complete_analysis = {
            'success': True,
            'product': {
                'title': product_title,
                'title_cn': product_info.get('title', ''),
                'url': product_info.get('url', ''),
                'price_cny': product_info.get('price', 0),
                'image': product_info.get('image', ''),
                'category': product_info.get('category', 'Unknown')
            },
            'korean_keyword': korean_keyword,
            'blue_ocean_category': blue_ocean_category,
            'market_data': {
                'coupang': coupang_data,
                'naver': naver_data
            },
            'profitability': profitability,
            'ai_analysis': {
                'demand': demand_analysis,
                'competition': competition_analysis,
                'sales_prediction': sales_prediction,
                'recommendation': recommendation
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Log summary
        self._log_analysis_summary(complete_analysis)
        
        return complete_analysis
    
    def batch_analyze_products(
        self,
        products: List[Dict[str, Any]],
        blue_ocean_category: Optional[str] = None,
        max_products: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Batch analyze multiple products
        
        Args:
            products: List of AliExpress products
            blue_ocean_category: Optional category keyword
            max_products: Maximum products to analyze
        
        Returns:
            List of analysis reports sorted by recommendation score
        """
        
        logger.info(f"[AI Sourcer] 🚀 Starting batch analysis for {min(len(products), max_products)} products")
        
        results = []
        
        for idx, product in enumerate(products[:max_products], 1):
            logger.info(f"[AI Sourcer] Analyzing product {idx}/{min(len(products), max_products)}")
            
            analysis = self.analyze_product(product, blue_ocean_category)
            
            if analysis.get('success'):
                results.append(analysis)
            else:
                logger.warning(f"[AI Sourcer] ⚠️ Failed to analyze: {product.get('title', 'Unknown')[:50]}")
        
        # Sort by recommendation score
        results.sort(
            key=lambda x: x.get('ai_analysis', {}).get('recommendation', {}).get('overall_score', 0),
            reverse=True
        )
        
        logger.info(f"[AI Sourcer] ✅ Batch analysis complete: {len(results)} successful")
        
        return results
    
    # ============================================================================
    # Helper Methods: Data Collection
    # ============================================================================
    
    def _generate_korean_keyword(
        self,
        product_info: Dict[str, Any],
        blue_ocean_category: Optional[str] = None
    ) -> str:
        """Generate Korean keyword for market search"""
        
        if blue_ocean_category:
            # Use blue ocean category if provided
            logger.info(f"[AI Sourcer] Using Blue Ocean category: {blue_ocean_category}")
            return blue_ocean_category
        
        # Clean and translate product title
        product_title = product_info.get('title', '')
        cleaned_title = clean_product_title(product_title)
        
        # Translate to Korean
        korean_keyword = translate_english_to_korean(cleaned_title)
        
        # Validate Korean keyword
        if not korean_keyword or not any('\uac00' <= c <= '\ud7a3' for c in korean_keyword):
            # Fallback: use original title
            logger.warning("[AI Sourcer] Korean translation failed, using original title")
            korean_keyword = cleaned_title
        
        return korean_keyword
    
    def _collect_coupang_data(self, keyword: str) -> Dict[str, Any]:
        """Collect Coupang market data"""
        
        if not self.coupang_access_key or not self.coupang_secret_key:
            logger.warning("[AI Sourcer] ⚠️ Coupang API credentials not configured - skipping")
            return {
                'success': False,
                'error': 'Coupang API not configured',
                'products': [],
                'total_reviews': 0,
                'avg_rating': 0,
                'estimated_monthly_sales': 0,
                'price_range': {}
            }
        
        try:
            logger.info(f"[AI Sourcer] 📊 Collecting Coupang data for: {keyword}")
            result = analyze_coupang_market(keyword, self.coupang_access_key, self.coupang_secret_key)
            
            if result.get('success'):
                logger.info(f"[AI Sourcer] ✅ Coupang data collected: {len(result.get('products', []))} products")
            else:
                logger.warning(f"[AI Sourcer] ⚠️ Coupang data collection failed: {result.get('error', 'Unknown')}")
            
            return result
        
        except Exception as e:
            logger.error(f"[AI Sourcer] ❌ Coupang data collection error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'products': []
            }
    
    def _collect_naver_data(self, keyword: str) -> Dict[str, Any]:
        """Collect Naver market data"""
        
        if not self.naver_client_id or not self.naver_client_secret:
            logger.warning("[AI Sourcer] ⚠️ Naver API credentials not configured - skipping")
            return {
                'success': False,
                'error': 'Naver API not configured',
                'products': [],
                'total_products': 0,
                'price_analysis': {},
                'market_trend': 'unknown'
            }
        
        try:
            logger.info(f"[AI Sourcer] 📊 Collecting Naver data for: {keyword}")
            result = analyze_naver_market_enhanced(keyword, self.naver_client_id, self.naver_client_secret)
            
            if result.get('success'):
                logger.info(f"[AI Sourcer] ✅ Naver data collected: {result.get('total_products', 0)} products")
            else:
                logger.warning(f"[AI Sourcer] ⚠️ Naver data collection failed: {result.get('error', 'Unknown')}")
            
            return result
        
        except Exception as e:
            logger.error(f"[AI Sourcer] ❌ Naver data collection error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'products': []
            }
    
    def _calculate_profitability(
        self,
        product_info: Dict[str, Any],
        naver_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate profitability metrics"""
        
        # Get AliExpress price
        price_cny = product_info.get('price', 0)
        
        # Constants
        cny_to_krw = 190
        exchange_buffer = 1.05
        shipping_cost = 5000
        customs_tax_rate = 0.10
        customs_threshold = 150000
        naver_fee_rate = 0.06
        
        # Calculate cost
        base_cost_krw = price_cny * cny_to_krw * exchange_buffer
        total_cost = base_cost_krw + shipping_cost
        
        # Get Naver average price
        naver_avg_price = naver_data.get('price_analysis', {}).get('avg_price', 0)
        
        if naver_avg_price == 0:
            logger.warning("[AI Sourcer] ⚠️ No Naver price data available")
            return {
                'success': False,
                'error': 'No market price data available',
                'total_cost': int(total_cost),
                'target_price': 0,
                'profit_margin': 0,
                'profit_per_unit': 0
            }
        
        # Calculate target price (competitive)
        target_price = int(naver_avg_price * 0.95)  # 5% below average
        
        # Add customs tax if applicable
        if target_price > customs_threshold:
            total_cost += target_price * customs_tax_rate
        
        # Calculate Naver net revenue
        naver_fee = target_price * naver_fee_rate
        net_revenue = target_price - naver_fee
        
        # Calculate profit
        profit_per_unit = net_revenue - total_cost
        profit_margin = (profit_per_unit / net_revenue * 100) if net_revenue > 0 else 0
        
        logger.info(f"[AI Sourcer] 💰 Profitability:")
        logger.info(f"  - Cost: ₩{int(total_cost):,}")
        logger.info(f"  - Target price: ₩{target_price:,}")
        logger.info(f"  - Profit: ₩{int(profit_per_unit):,} ({profit_margin:.1f}%)")
        
        return {
            'success': True,
            'price_cny': price_cny,
            'cny_to_krw_rate': cny_to_krw,
            'base_cost_krw': int(base_cost_krw),
            'shipping_cost': shipping_cost,
            'total_cost': int(total_cost),
            'target_price': target_price,
            'naver_fee': int(naver_fee),
            'net_revenue': int(net_revenue),
            'profit_per_unit': int(profit_per_unit),
            'profit_margin': round(profit_margin, 2),
            'market_avg_price': naver_avg_price,
            'is_profitable': profit_margin >= 25
        }
    
    def _log_analysis_summary(self, analysis: Dict[str, Any]):
        """Log analysis summary"""
        
        recommendation = analysis.get('ai_analysis', {}).get('recommendation', {})
        profitability = analysis.get('profitability', {})
        sales_prediction = analysis.get('ai_analysis', {}).get('sales_prediction', {})
        
        logger.info("[AI Sourcer] ========================================")
        logger.info(f"[AI Sourcer] 📊 ANALYSIS SUMMARY")
        logger.info(f"[AI Sourcer] Product: {analysis.get('product', {}).get('title', 'Unknown')[:50]}...")
        logger.info(f"[AI Sourcer] Korean Keyword: {analysis.get('korean_keyword', 'N/A')}")
        logger.info(f"[AI Sourcer] Overall Score: {recommendation.get('overall_score', 0)}/100")
        logger.info(f"[AI Sourcer] Recommendation: {recommendation.get('recommendation', 'UNKNOWN')}")
        logger.info(f"[AI Sourcer] Profit Margin: {profitability.get('profit_margin', 0):.1f}%")
        logger.info(f"[AI Sourcer] Est. Monthly Sales: {sales_prediction.get('estimated_monthly_sales', 0)} units")
        logger.info(f"[AI Sourcer] Success Probability: {sales_prediction.get('success_probability', 0)}%")
        logger.info("[AI Sourcer] ========================================")


def generate_markdown_report(analysis: Dict[str, Any]) -> str:
    """
    Generate markdown report from AI analysis
    
    Args:
        analysis: Complete analysis dict from AISourcer
    
    Returns:
        Formatted markdown report
    """
    
    product = analysis.get('product', {})
    profitability = analysis.get('profitability', {})
    ai_analysis = analysis.get('ai_analysis', {})
    recommendation = ai_analysis.get('recommendation', {})
    demand = ai_analysis.get('demand', {})
    competition = ai_analysis.get('competition', {})
    sales = ai_analysis.get('sales_prediction', {})
    coupang_data = analysis.get('market_data', {}).get('coupang', {})
    naver_data = analysis.get('market_data', {}).get('naver', {})
    
    # Build markdown
    report = f"""# 🤖 AI 소싱 분석 보고서

**제품명**: {product.get('title', 'Unknown')}  
**분석 일시**: {analysis.get('timestamp', 'N/A')}  
**한글 키워드**: {analysis.get('korean_keyword', 'N/A')}

---

## 📊 종합 평가

**추천도**: {recommendation.get('overall_score', 0)}/100점  
**최종 의견**: **{recommendation.get('recommendation', 'UNKNOWN')}**  
**신뢰도**: {recommendation.get('confidence_level', 'unknown')}

### 요약
{recommendation.get('executive_summary', 'N/A')}

---

## 💰 수익성 분석

| 항목 | 금액 |
|------|------|
| 알리 원가 | ¥{profitability.get('price_cny', 0)} |
| 한국 원가 | ₩{profitability.get('total_cost', 0):,} |
| 네이버 평균가 | ₩{profitability.get('market_avg_price', 0):,} |
| 목표 판매가 | ₩{profitability.get('target_price', 0):,} |
| 단위당 수익 | ₩{profitability.get('profit_per_unit', 0):,} |
| **수익률** | **{profitability.get('profit_margin', 0):.1f}%** |

**수익성**: {'✅ 양호 (25% 이상)' if profitability.get('is_profitable', False) else '❌ 부족 (25% 미만)'}

---

## 📈 시장 수요 분석

**수요 점수**: {demand.get('demand_score', 0)}/100  
**수요 수준**: {demand.get('demand_level', 'unknown')}  
**시장 트렌드**: {demand.get('market_trend', 'unknown')}  
**경쟁 수준**: {demand.get('competition_level', 'unknown')}  
**계절성**: {demand.get('seasonality', 'unknown')}

### 주요 인사이트
"""
    
    # Add insights
    insights = demand.get('key_insights', [])
    for insight in insights:
        report += f"- {insight}\n"
    
    report += f"""
---

## 🏆 경쟁 분석

**경쟁 점수**: {competition.get('competition_score', 0)}/100 (낮을수록 유리)  
**시장 포화도**: {competition.get('saturation_level', 'unknown')}  
**진입 난이도**: {competition.get('market_entry_difficulty', 'unknown')}

### 쿠팡 시장
- 총 상품수: {coupang_data.get('total_products', 0):,}개
- 평균 리뷰: {coupang_data.get('total_reviews', 0):,}개
- 평균 평점: {coupang_data.get('avg_rating', 0):.1f}/5.0
- 월 예상 판매: {coupang_data.get('estimated_monthly_sales', 0):,}개

### 네이버 시장
- 총 상품수: {naver_data.get('total_products', 0):,}개
- 가격대: ₩{naver_data.get('price_analysis', {}).get('min_price', 0):,} ~ ₩{naver_data.get('price_analysis', {}).get('max_price', 0):,}
- 시장 트렌드: {naver_data.get('market_trend', 'unknown')}

### 추천 가격 전략
{competition.get('price_positioning_strategy', 'N/A')}  
**추천 가격대**: ₩{competition.get('recommended_price_range', {}).get('min', 0):,} ~ ₩{competition.get('recommended_price_range', {}).get('max', 0):,}

---

## 🎯 판매 예측

**월 예상 판매량**: {sales.get('estimated_monthly_sales', 0)}개

### 시나리오별 예상
- 보수적: {sales.get('sales_range', {}).get('conservative', 0)}개
- 현실적: {sales.get('sales_range', {}).get('realistic', 0)}개
- 낙관적: {sales.get('sales_range', {}).get('optimistic', 0)}개

**월 예상 수익**: ₩{sales.get('profit_forecast_monthly', 0):,}  
**성공 확률**: {sales.get('success_probability', 0)}%  
**투자 회수 기간**: {sales.get('payback_period_days', 0)}일

### 성장 잠재력
- 단기: {sales.get('growth_potential', {}).get('short_term', 'unknown')}
- 장기: {sales.get('growth_potential', {}).get('long_term', 'unknown')}

### 리스크 요인
"""
    
    # Add risk factors
    risks = sales.get('risk_factors', [])
    for risk in risks:
        report += f"- {risk}\n"
    
    report += f"""
---

## ✅ 강점

"""
    
    # Add strengths
    strengths = recommendation.get('key_strengths', [])
    for strength in strengths:
        report += f"- {strength}\n"
    
    report += f"""
---

## ⚠️ 리스크

"""
    
    # Add risks
    key_risks = recommendation.get('key_risks', [])
    for risk in key_risks:
        report += f"- {risk}\n"
    
    report += f"""
---

## 📝 상세 분석

{recommendation.get('detailed_analysis', 'N/A')}

---

## 🎬 실행 계획

"""
    
    # Add action items
    action_items = recommendation.get('action_items', [])
    for idx, action in enumerate(action_items, 1):
        report += f"{idx}. {action}\n"
    
    report += f"""
---

## 🕐 수익 실현 예상 기간

{recommendation.get('timeline_to_profit', 'uncertain')}

---

*본 보고서는 AI 기반 시장 분석 결과이며, 실제 판매 성과는 다를 수 있습니다.*
"""
    
    return report
