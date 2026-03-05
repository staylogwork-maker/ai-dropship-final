#!/usr/bin/env python3
"""
Integration Module: Add AI Sourcing to app.py
This module contains the enhanced execute_smart_sourcing_with_ai function
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def execute_smart_sourcing_with_ai(
    keyword,
    aliexpress_products,
    get_config_func,
    get_db_func,
    log_activity_func,
    app_logger
):
    """
    Enhanced Smart Sourcing with AI Analysis
    
    This function extends the standard execute_smart_sourcing with:
    1. AI market analysis using OpenAI GPT-4
    2. Coupang market data (sales, reviews, ratings)
    3. Enhanced Naver market analysis
    4. Comprehensive recommendation reports
    
    Args:
        keyword: Search keyword
        aliexpress_products: List of AliExpress product data
        get_config_func: Function to get config values
        get_db_func: Function to get database connection
        log_activity_func: Function to log activities
        app_logger: Logger instance
    
    Returns:
        Dict with analysis results including AI recommendations
    """
    
    app_logger.info("[AI Sourcer] ========================================")
    app_logger.info("[AI Sourcer] 🤖 Starting AI-Powered Smart Sourcing")
    app_logger.info(f"[AI Sourcer] Keyword: {keyword}")
    app_logger.info(f"[AI Sourcer] Products to analyze: {len(aliexpress_products)}")
    app_logger.info("[AI Sourcer] ========================================")
    
    # Get API credentials
    openai_api_key = get_config_func('openai_api_key', '')
    coupang_access_key = get_config_func('coupang_access_key', '')
    coupang_secret_key = get_config_func('coupang_secret_key', '')
    naver_client_id = get_config_func('naver_client_id', '')
    naver_client_secret = get_config_func('naver_client_secret', '')
    
    # Check if AI sourcing is possible
    if not openai_api_key:
        app_logger.warning("[AI Sourcer] ⚠️ OpenAI API key not configured - AI analysis disabled")
        app_logger.warning("[AI Sourcer] Falling back to standard sourcing")
        return {
            'ai_enabled': False,
            'reason': 'OpenAI API key not configured'
        }
    
    # Import AI sourcing engine
    try:
        from ai_sourcing_engine import AISourcer, generate_markdown_report
        app_logger.info("[AI Sourcer] ✅ AI modules imported successfully")
    except ImportError as e:
        app_logger.error(f"[AI Sourcer] ❌ Failed to import AI modules: {str(e)}")
        return {
            'ai_enabled': False,
            'reason': f'Failed to import AI modules: {str(e)}'
        }
    
    # Initialize AI sourcer
    try:
        ai_sourcer = AISourcer(
            openai_api_key=openai_api_key,
            coupang_access_key=coupang_access_key,
            coupang_secret_key=coupang_secret_key,
            naver_client_id=naver_client_id,
            naver_client_secret=naver_client_secret
        )
        app_logger.info("[AI Sourcer] ✅ AI Sourcer initialized")
    except Exception as e:
        app_logger.error(f"[AI Sourcer] ❌ Failed to initialize AI Sourcer: {str(e)}")
        return {
            'ai_enabled': False,
            'reason': f'Failed to initialize: {str(e)}'
        }
    
    # Perform AI analysis on products (top 3 for cost efficiency)
    log_activity_func('ai_sourcing', '🤖 Running AI market analysis...', 'in_progress')
    
    try:
        analyses = ai_sourcer.batch_analyze_products(
            aliexpress_products,
            blue_ocean_category=keyword,
            max_products=3  # Limit to 3 for OpenAI API cost control
        )
        
        app_logger.info(f"[AI Sourcer] ✅ Analyzed {len(analyses)} products")
        
        # Generate reports
        reports = []
        for analysis in analyses:
            try:
                report = generate_markdown_report(analysis)
                reports.append({
                    'product_title': analysis['product']['title'],
                    'korean_keyword': analysis['korean_keyword'],
                    'overall_score': analysis['ai_analysis']['recommendation']['overall_score'],
                    'recommendation': analysis['ai_analysis']['recommendation']['recommendation'],
                    'profit_margin': analysis['profitability']['profit_margin'],
                    'estimated_monthly_sales': analysis['ai_analysis']['sales_prediction']['estimated_monthly_sales'],
                    'success_probability': analysis['ai_analysis']['sales_prediction']['success_probability'],
                    'markdown_report': report,
                    'full_analysis': analysis
                })
            except Exception as e:
                app_logger.error(f"[AI Sourcer] ⚠️ Failed to generate report for product: {str(e)}")
        
        app_logger.info(f"[AI Sourcer] ✅ Generated {len(reports)} comprehensive reports")
        
        log_activity_func('ai_sourcing', f'✅ AI analysis complete: {len(reports)} products with recommendations', 'success')
        
        return {
            'ai_enabled': True,
            'success': True,
            'total_analyzed': len(analyses),
            'reports': reports,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        app_logger.error(f"[AI Sourcer] ❌ AI analysis failed: {str(e)}")
        app_logger.exception(e)
        log_activity_func('ai_sourcing', f'❌ AI analysis failed: {str(e)}', 'error')
        
        return {
            'ai_enabled': True,
            'success': False,
            'error': str(e)
        }


def save_ai_analysis_to_db(
    analysis: Dict[str, Any],
    get_db_func,
    app_logger
) -> bool:
    """
    Save AI analysis results to database
    
    Args:
        analysis: Complete AI analysis dict
        get_db_func: Function to get database connection
        app_logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    
    try:
        conn = get_db_func()
        cursor = conn.cursor()
        
        product = analysis['product']
        profitability = analysis['profitability']
        recommendation = analysis['ai_analysis']['recommendation']
        sales_prediction = analysis['ai_analysis']['sales_prediction']
        
        # Prepare data
        title_cn = product['title_cn']
        title_kr = analysis['korean_keyword']
        original_url = product['url']
        price_cny = product['price_cny']
        price_krw = profitability['target_price']
        profit_margin = profitability['profit_margin']
        estimated_profit = profitability['profit_per_unit']
        
        # Build comprehensive market analysis JSON
        market_analysis_json = json.dumps({
            'korean_keyword': analysis['korean_keyword'],
            'blue_ocean_category': analysis.get('blue_ocean_category', ''),
            'ai_analysis': analysis['ai_analysis'],
            'market_data': analysis['market_data'],
            'profitability': profitability,
            'recommendation_score': recommendation['overall_score'],
            'recommendation': recommendation['recommendation'],
            'estimated_monthly_sales': sales_prediction['estimated_monthly_sales'],
            'success_probability': sales_prediction['success_probability'],
            'timestamp': analysis['timestamp']
        }, ensure_ascii=False)
        
        # Prepare images
        images_json = json.dumps([product.get('image', '')])
        
        # Insert into database
        cursor.execute('''
            INSERT INTO sourced_products 
            (original_url, title_cn, title_kr, price_cny, price_krw, profit_margin, 
             estimated_profit, safety_status, images_json, status,
             source_site, moq, traffic_score, keywords, market_analysis_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            original_url,
            title_cn,
            title_kr,
            price_cny,
            price_krw,
            profit_margin,
            estimated_profit,
            'ai_verified',  # Special status for AI-analyzed products
            images_json,
            'pending',
            'aliexpress',
            1,  # MOQ
            sales_prediction['estimated_monthly_sales'],  # Use AI prediction as traffic score
            analysis['korean_keyword'],
            market_analysis_json
        ))
        
        conn.commit()
        conn.close()
        
        app_logger.info(f"[AI Sourcer] ✅ Saved AI analysis to database: {title_cn[:50]}...")
        
        return True
    
    except Exception as e:
        app_logger.error(f"[AI Sourcer] ❌ Failed to save AI analysis to DB: {str(e)}")
        return False
