#!/usr/bin/env python3
"""
AI Market Analyzer - OpenAI GPT-4 Powered Market Intelligence
Analyzes Coupang/Naver market data to provide intelligent product recommendations
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai

logger = logging.getLogger(__name__)


class AIMarketAnalyzer:
    """
    AI-powered market analyzer using OpenAI GPT-4
    Provides intelligent insights on product demand, competition, and sales potential
    """
    
    def __init__(self, openai_api_key: str):
        """Initialize with OpenAI API key"""
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
        logger.info("[AI Analyzer] Initialized with OpenAI GPT-4")
    
    def analyze_market_demand(
        self,
        product_info: Dict[str, Any],
        coupang_data: Dict[str, Any],
        naver_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze market demand using AI
        
        Args:
            product_info: AliExpress product information
            coupang_data: Coupang market data (sales, reviews, ratings)
            naver_data: Naver market data (search volume, price range)
        
        Returns:
            Dict with AI analysis results including:
            - demand_score: 1-100 demand rating
            - competition_level: low/medium/high
            - market_trend: rising/stable/declining
            - seasonality: seasonal insights
            - recommendation: detailed recommendation text
            - confidence_score: AI confidence level
        """
        
        logger.info(f"[AI Analyzer] Starting market demand analysis for: {product_info.get('title', 'Unknown')[:50]}...")
        
        # Build comprehensive market context
        context = self._build_market_context(product_info, coupang_data, naver_data)
        
        # Generate AI analysis using GPT-4
        prompt = self._create_demand_analysis_prompt(context)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert e-commerce market analyst specializing in Korean online marketplaces (Coupang, Naver Shopping).
Your task is to analyze product market data and provide actionable insights for dropshipping decisions.
Always respond in JSON format with precise, data-driven recommendations."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Parse AI response
            ai_response = response.choices[0].message.content
            logger.info(f"[AI Analyzer] Raw GPT-4 response: {ai_response[:200]}...")
            
            # Extract JSON from response
            analysis = self._parse_ai_response(ai_response)
            
            logger.info(f"[AI Analyzer] ✅ Analysis complete - Demand Score: {analysis.get('demand_score', 0)}/100")
            
            return analysis
            
        except Exception as e:
            logger.error(f"[AI Analyzer] ❌ OpenAI API error: {str(e)}")
            # Return fallback analysis
            return self._fallback_analysis(context)
    
    def analyze_competition(
        self,
        product_info: Dict[str, Any],
        coupang_competitors: List[Dict[str, Any]],
        naver_competitors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze competition landscape using AI
        
        Returns:
            Dict with competition analysis:
            - competition_score: 1-100 (lower = less competition)
            - dominant_brands: list of top brands
            - price_positioning: recommended pricing strategy
            - differentiation_opportunities: how to stand out
            - market_saturation: saturation level assessment
        """
        
        logger.info(f"[AI Analyzer] Analyzing competition for: {product_info.get('title', 'Unknown')[:50]}...")
        
        context = {
            'product': product_info,
            'coupang_competitors': coupang_competitors[:10],  # Top 10 only
            'naver_competitors': naver_competitors[:10],
            'total_coupang_listings': len(coupang_competitors),
            'total_naver_listings': len(naver_competitors)
        }
        
        prompt = self._create_competition_analysis_prompt(context)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert competition analyst for Korean e-commerce markets.
Analyze competitor data and provide strategic insights for new market entrants.
Focus on pricing strategy, market positioning, and differentiation opportunities."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1200
            )
            
            ai_response = response.choices[0].message.content
            analysis = self._parse_ai_response(ai_response)
            
            logger.info(f"[AI Analyzer] ✅ Competition analysis complete - Score: {analysis.get('competition_score', 0)}/100")
            
            return analysis
            
        except Exception as e:
            logger.error(f"[AI Analyzer] ❌ Competition analysis error: {str(e)}")
            return self._fallback_competition_analysis(context)
    
    def predict_sales_potential(
        self,
        product_info: Dict[str, Any],
        demand_analysis: Dict[str, Any],
        competition_analysis: Dict[str, Any],
        pricing_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Predict sales potential using AI model
        
        Returns:
            Dict with sales prediction:
            - estimated_monthly_sales: predicted unit sales per month
            - revenue_forecast: estimated monthly revenue (KRW)
            - profit_forecast: estimated monthly profit (KRW)
            - success_probability: 0-100% likelihood of success
            - risk_factors: list of potential risks
            - growth_potential: short-term and long-term growth outlook
        """
        
        logger.info(f"[AI Analyzer] Predicting sales potential for: {product_info.get('title', 'Unknown')[:50]}...")
        
        context = {
            'product': product_info,
            'demand': demand_analysis,
            'competition': competition_analysis,
            'pricing': pricing_info
        }
        
        prompt = self._create_sales_prediction_prompt(context)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert sales forecaster for Korean e-commerce.
Based on market data, predict realistic sales volumes and revenue.
Provide conservative estimates with clear reasoning and risk assessment."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for numerical predictions
                max_tokens=1200
            )
            
            ai_response = response.choices[0].message.content
            prediction = self._parse_ai_response(ai_response)
            
            logger.info(f"[AI Analyzer] ✅ Sales prediction complete - Est. monthly sales: {prediction.get('estimated_monthly_sales', 0)} units")
            
            return prediction
            
        except Exception as e:
            logger.error(f"[AI Analyzer] ❌ Sales prediction error: {str(e)}")
            return self._fallback_sales_prediction(context)
    
    def generate_recommendation_report(
        self,
        product_info: Dict[str, Any],
        demand_analysis: Dict[str, Any],
        competition_analysis: Dict[str, Any],
        sales_prediction: Dict[str, Any],
        profitability: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive recommendation report
        
        Returns:
            Dict with full recommendation:
            - overall_score: 1-100 recommendation score
            - recommendation: BUY / CONSIDER / AVOID
            - executive_summary: brief summary (2-3 sentences)
            - detailed_analysis: comprehensive analysis report
            - key_strengths: list of product strengths
            - key_risks: list of potential risks
            - action_items: recommended next steps
        """
        
        logger.info(f"[AI Analyzer] Generating recommendation report for: {product_info.get('title', 'Unknown')[:50]}...")
        
        context = {
            'product': product_info,
            'demand': demand_analysis,
            'competition': competition_analysis,
            'sales': sales_prediction,
            'profitability': profitability
        }
        
        prompt = self._create_recommendation_prompt(context)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert dropshipping consultant for Korean markets.
Synthesize all market data into a clear, actionable recommendation.
Provide honest, data-driven advice that protects the seller from bad decisions."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            ai_response = response.choices[0].message.content
            report = self._parse_ai_response(ai_response)
            
            logger.info(f"[AI Analyzer] ✅ Report generated - Recommendation: {report.get('recommendation', 'UNKNOWN')}")
            
            return report
            
        except Exception as e:
            logger.error(f"[AI Analyzer] ❌ Report generation error: {str(e)}")
            return self._fallback_recommendation(context)
    
    # ============================================================================
    # Helper Methods: Prompt Engineering
    # ============================================================================
    
    def _build_market_context(
        self,
        product_info: Dict[str, Any],
        coupang_data: Dict[str, Any],
        naver_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build comprehensive market context for AI analysis"""
        
        return {
            'product': {
                'title': product_info.get('title', 'Unknown'),
                'price_cny': product_info.get('price', 0),
                'category': product_info.get('category', 'Unknown')
            },
            'coupang': {
                'bestseller_rank': coupang_data.get('bestseller_rank', None),
                'review_count': coupang_data.get('total_reviews', 0),
                'avg_rating': coupang_data.get('avg_rating', 0),
                'monthly_sales': coupang_data.get('estimated_monthly_sales', 0),
                'price_range': coupang_data.get('price_range', {}),
                'top_sellers': coupang_data.get('top_products', [])[:3]
            },
            'naver': {
                'total_listings': naver_data.get('total_products', 0),
                'avg_price': naver_data.get('avg_price', 0),
                'price_range': naver_data.get('price_range', {}),
                'review_summary': naver_data.get('review_summary', {}),
                'trend': naver_data.get('trend', 'stable')
            }
        }
    
    def _create_demand_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for demand analysis"""
        
        return f"""Analyze the market demand for this product in Korean e-commerce:

**Product Information:**
- Title: {context['product']['title']}
- Price (CNY): ¥{context['product']['price_cny']}
- Category: {context['product']['category']}

**Coupang Market Data:**
- Bestseller Rank: {context['coupang'].get('bestseller_rank', 'N/A')}
- Total Reviews: {context['coupang']['review_count']:,}
- Average Rating: {context['coupang']['avg_rating']}/5.0
- Estimated Monthly Sales: {context['coupang']['monthly_sales']:,} units
- Price Range: ₩{context['coupang']['price_range'].get('min', 0):,} - ₩{context['coupang']['price_range'].get('max', 0):,}
- Top 3 Sellers: {json.dumps(context['coupang']['top_sellers'], ensure_ascii=False, indent=2)}

**Naver Shopping Data:**
- Total Listings: {context['naver']['total_listings']:,}
- Average Price: ₩{context['naver']['avg_price']:,}
- Market Trend: {context['naver']['trend']}
- Review Summary: {json.dumps(context['naver']['review_summary'], ensure_ascii=False)}

**Task:**
Analyze this data and provide a JSON response with:

```json
{{
  "demand_score": <1-100>,
  "demand_level": "low|moderate|high|very_high",
  "competition_level": "low|medium|high",
  "market_trend": "rising|stable|declining",
  "seasonality": "year_round|seasonal|holiday",
  "seasonal_months": ["month names if seasonal"],
  "key_insights": [
    "insight 1",
    "insight 2",
    "insight 3"
  ],
  "recommendation_summary": "2-3 sentence summary",
  "confidence_score": <0-100>
}}
```

Consider:
1. Review count indicates market maturity
2. High sales + high reviews = proven demand
3. Price range shows market positioning opportunities
4. Trend indicates future potential
"""
    
    def _create_competition_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for competition analysis"""
        
        return f"""Analyze the competition landscape for this product:

**Product:** {context['product'].get('title', 'Unknown')[:100]}

**Market Overview:**
- Total Coupang Listings: {context['total_coupang_listings']}
- Total Naver Listings: {context['total_naver_listings']}

**Top Coupang Competitors:**
{json.dumps(context['coupang_competitors'], ensure_ascii=False, indent=2)}

**Top Naver Competitors:**
{json.dumps(context['naver_competitors'], ensure_ascii=False, indent=2)}

**Task:**
Analyze competition and provide JSON:

```json
{{
  "competition_score": <1-100, lower = better>,
  "saturation_level": "low|moderate|high|saturated",
  "dominant_brands": ["brand1", "brand2"],
  "avg_competitor_price": <KRW>,
  "price_positioning_strategy": "budget|mid_range|premium",
  "recommended_price_range": {{
    "min": <KRW>,
    "max": <KRW>
  }},
  "differentiation_opportunities": [
    "opportunity 1",
    "opportunity 2"
  ],
  "market_entry_difficulty": "easy|moderate|hard|very_hard",
  "key_success_factors": [
    "factor 1",
    "factor 2"
  ]
}}
```
"""
    
    def _create_sales_prediction_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for sales prediction"""
        
        demand = context.get('demand', {})
        competition = context.get('competition', {})
        pricing = context.get('pricing', {})
        
        return f"""Predict sales potential based on market analysis:

**Product:** {context['product'].get('title', 'Unknown')[:100]}

**Demand Analysis:**
- Demand Score: {demand.get('demand_score', 0)}/100
- Competition Level: {demand.get('competition_level', 'unknown')}
- Market Trend: {demand.get('market_trend', 'unknown')}

**Competition Analysis:**
- Competition Score: {competition.get('competition_score', 0)}/100
- Market Saturation: {competition.get('saturation_level', 'unknown')}
- Entry Difficulty: {competition.get('market_entry_difficulty', 'unknown')}

**Pricing:**
- Our Cost: ₩{pricing.get('total_cost', 0):,}
- Target Price: ₩{pricing.get('target_price', 0):,}
- Profit Margin: {pricing.get('profit_margin', 0):.1f}%
- Profit per Unit: ₩{pricing.get('profit_per_unit', 0):,}

**Task:**
Provide realistic sales forecast in JSON:

```json
{{
  "estimated_monthly_sales": <units per month>,
  "sales_range": {{
    "conservative": <units>,
    "realistic": <units>,
    "optimistic": <units>
  }},
  "revenue_forecast_monthly": <KRW>,
  "profit_forecast_monthly": <KRW>,
  "success_probability": <0-100%>,
  "payback_period_days": <days to recover initial investment>,
  "risk_factors": [
    "risk 1",
    "risk 2"
  ],
  "growth_potential": {{
    "short_term": "low|moderate|high",
    "long_term": "low|moderate|high"
  }},
  "market_timing": "excellent|good|fair|poor"
}}
```

Be conservative but realistic. Consider Korean market dynamics.
"""
    
    def _create_recommendation_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for final recommendation"""
        
        return f"""Generate comprehensive recommendation report:

**Product:** {context['product'].get('title', 'Unknown')[:100]}
**Category:** {context['product'].get('category', 'Unknown')}

**Analysis Summary:**

**Demand Analysis:**
{json.dumps(context.get('demand', {}), ensure_ascii=False, indent=2)}

**Competition Analysis:**
{json.dumps(context.get('competition', {}), ensure_ascii=False, indent=2)}

**Sales Prediction:**
{json.dumps(context.get('sales', {}), ensure_ascii=False, indent=2)}

**Profitability:**
{json.dumps(context.get('profitability', {}), ensure_ascii=False, indent=2)}

**Task:**
Synthesize all data into actionable recommendation (JSON):

```json
{{
  "overall_score": <1-100>,
  "recommendation": "STRONG_BUY|BUY|CONSIDER|AVOID|STRONG_AVOID",
  "confidence_level": "low|moderate|high|very_high",
  "executive_summary": "2-3 sentence summary in Korean",
  "detailed_analysis": "Comprehensive analysis in Korean (5-7 sentences)",
  "key_strengths": [
    "strength 1",
    "strength 2",
    "strength 3"
  ],
  "key_risks": [
    "risk 1",
    "risk 2",
    "risk 3"
  ],
  "market_opportunity": "description of opportunity",
  "action_items": [
    "step 1",
    "step 2",
    "step 3"
  ],
  "timeline_to_profit": "immediate|1-2_weeks|1_month|2-3_months|uncertain"
}}
```

Provide honest, data-driven advice that protects the seller.
"""
    
    # ============================================================================
    # Helper Methods: Response Parsing
    # ============================================================================
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON"""
        try:
            # Try to find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # If no JSON found, return wrapped response
                logger.warning("[AI Analyzer] No JSON found in response, wrapping text")
                return {
                    'raw_response': response,
                    'error': 'Could not parse JSON from AI response'
                }
        except json.JSONDecodeError as e:
            logger.error(f"[AI Analyzer] JSON parse error: {str(e)}")
            return {
                'raw_response': response,
                'error': f'JSON parse error: {str(e)}'
            }
    
    # ============================================================================
    # Fallback Methods (when AI fails)
    # ============================================================================
    
    def _fallback_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis when AI fails"""
        logger.warning("[AI Analyzer] Using fallback demand analysis")
        
        coupang = context.get('coupang', {})
        naver = context.get('naver', {})
        
        # Simple rule-based scoring
        review_count = coupang.get('review_count', 0)
        monthly_sales = coupang.get('monthly_sales', 0)
        total_listings = naver.get('total_listings', 0)
        
        demand_score = min(100, (review_count / 100) * 50 + (monthly_sales / 50) * 50)
        
        return {
            'demand_score': int(demand_score),
            'demand_level': 'moderate' if demand_score > 50 else 'low',
            'competition_level': 'high' if total_listings > 1000 else 'moderate',
            'market_trend': 'stable',
            'seasonality': 'year_round',
            'key_insights': ['Automated fallback analysis'],
            'recommendation_summary': 'AI analysis unavailable - manual review recommended',
            'confidence_score': 30
        }
    
    def _fallback_competition_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback competition analysis"""
        logger.warning("[AI Analyzer] Using fallback competition analysis")
        
        total_competitors = context.get('total_coupang_listings', 0) + context.get('total_naver_listings', 0)
        
        return {
            'competition_score': min(100, total_competitors / 10),
            'saturation_level': 'high' if total_competitors > 500 else 'moderate',
            'dominant_brands': [],
            'market_entry_difficulty': 'moderate',
            'key_success_factors': ['Price competitiveness', 'Fast shipping', 'Good reviews']
        }
    
    def _fallback_sales_prediction(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback sales prediction"""
        logger.warning("[AI Analyzer] Using fallback sales prediction")
        
        return {
            'estimated_monthly_sales': 10,
            'success_probability': 50,
            'revenue_forecast_monthly': 0,
            'profit_forecast_monthly': 0,
            'risk_factors': ['AI prediction unavailable'],
            'growth_potential': {'short_term': 'moderate', 'long_term': 'moderate'}
        }
    
    def _fallback_recommendation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback recommendation"""
        logger.warning("[AI Analyzer] Using fallback recommendation")
        
        return {
            'overall_score': 50,
            'recommendation': 'CONSIDER',
            'confidence_level': 'low',
            'executive_summary': 'AI 분석을 사용할 수 없습니다. 수동 검토가 필요합니다.',
            'detailed_analysis': '자동 분석 시스템이 일시적으로 사용 불가능합니다. 제품에 대한 수동 시장 조사를 진행하시기 바랍니다.',
            'key_strengths': ['분석 불가'],
            'key_risks': ['AI 분석 실패'],
            'action_items': ['수동 시장 조사 수행', '경쟁사 가격 확인', '리뷰 분석']
        }
