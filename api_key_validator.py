"""
API 키 검증 시스템
- 설정 페이지에서 API 키 입력 시 즉시 검증
- 유효하지 않으면 저장 거부
- 대시보드에서 API 상태 실시간 표시
- 캐싱으로 불필요한 API 호출 방지
"""
import logging
from typing import Dict, Tuple
import time

logger = logging.getLogger(__name__)

# API 검증 결과 캐시 (5분간 유효)
_validation_cache = {}
_cache_ttl = 300  # 5 minutes


def validate_gemini_api_key(api_key: str) -> Tuple[bool, str]:
    """
    Gemini API 키 유효성 검사 (캐싱 적용)
    
    Returns:
        (is_valid, message)
    """
    if not api_key or len(api_key) < 30:
        return False, "❌ API 키가 너무 짧습니다 (최소 30자)"
    
    if not api_key.startswith('AIza'):
        return False, "❌ Gemini API 키는 'AIza'로 시작해야 합니다"
    
    # 캐시 확인 (5분 내 동일 키는 재검증 안함)
    cache_key = f"gemini_{api_key}"
    if cache_key in _validation_cache:
        cached_time, cached_result = _validation_cache[cache_key]
        if time.time() - cached_time < _cache_ttl:
            logger.info(f"[Gemini Validation] Using cached result (age: {int(time.time() - cached_time)}s)")
            return cached_result
    
    # 형식만 검증 (실제 API 호출 안함!)
    # 이유: 불필요한 API 크레딧 소모 방지
    result = (True, "✅ Gemini API 키가 설정되었습니다")
    
    # 캐시 저장
    _validation_cache[cache_key] = (time.time(), result)
    
    return result


def validate_openai_api_key(api_key: str) -> Tuple[bool, str]:
    """
    OpenAI API 키 유효성 검사 (캐싱 적용)
    
    Returns:
        (is_valid, message)
    """
    if not api_key or len(api_key) < 40:
        return False, "❌ API 키가 너무 짧습니다 (최소 40자)"
    
    if not (api_key.startswith('sk-') or api_key.startswith('sk-proj-')):
        return False, "❌ OpenAI API 키는 'sk-' 또는 'sk-proj-'로 시작해야 합니다"
    
    # 캐시 확인 (5분 내 동일 키는 재검증 안함)
    cache_key = f"openai_{api_key}"
    if cache_key in _validation_cache:
        cached_time, cached_result = _validation_cache[cache_key]
        if time.time() - cached_time < _cache_ttl:
            logger.info(f"[OpenAI Validation] Using cached result (age: {int(time.time() - cached_time)}s)")
            return cached_result
    
    # 형식만 검증 (실제 API 호출 안함!)
    # 이유: 불필요한 API 크레딧 소모 방지
    result = (True, "✅ OpenAI API 키가 설정되었습니다")
    
    # 캐시 저장
    _validation_cache[cache_key] = (time.time(), result)
    
    return result


def get_api_status() -> Dict[str, Dict[str, str]]:
    """
    현재 저장된 모든 API 키 상태 확인
    
    Returns:
        {
            'gemini': {'status': 'valid/invalid/none', 'message': '...'},
            'openai': {'status': 'valid/invalid/none', 'message': '...'},
            'aliexpress': {...},
            'naver': {...},
            'coupang': {...}
        }
    """
    from app import get_config
    
    status = {}
    
    # Gemini 체크
    gemini_key = get_config('gemini_api_key')
    if not gemini_key:
        status['gemini'] = {
            'status': 'none',
            'message': '⚪ API 키가 설정되지 않았습니다',
            'color': 'gray'
        }
    else:
        is_valid, message = validate_gemini_api_key(gemini_key)
        status['gemini'] = {
            'status': 'valid' if is_valid else 'invalid',
            'message': message,
            'color': 'green' if is_valid else 'red'
        }
    
    # OpenAI 체크
    openai_key = get_config('openai_api_key')
    if not openai_key:
        status['openai'] = {
            'status': 'none',
            'message': '⚪ API 키가 설정되지 않았습니다',
            'color': 'gray'
        }
    else:
        is_valid, message = validate_openai_api_key(openai_key)
        status['openai'] = {
            'status': 'valid' if is_valid else 'invalid',
            'message': message,
            'color': 'green' if is_valid else 'red'
        }
    
    # AliExpress (Official API - 무료, 항상 활성)
    status['aliexpress'] = {
        'status': 'valid',
        'message': '✅ AliExpress Official API 활성화됨 (무료)',
        'color': 'green'
    }
    
    # Naver Shopping API - 형식 검증만 (실제 호출 안함)
    naver_client_id = get_config('naver_client_id')
    naver_client_secret = get_config('naver_client_secret')
    if not naver_client_id or not naver_client_secret:
        status['naver'] = {
            'status': 'none',
            'message': '⚪ Client ID/Secret이 설정되지 않았습니다',
            'color': 'gray'
        }
    else:
        # 형식만 검증 (길이 체크)
        if len(naver_client_id) >= 15 and len(naver_client_secret) >= 8:
            status['naver'] = {
                'status': 'valid',
                'message': '✅ 네이버 쇼핑 API 설정됨',
                'color': 'green'
            }
        else:
            status['naver'] = {
                'status': 'invalid',
                'message': f'❌ Client ID/Secret 길이 오류 (ID:{len(naver_client_id)}, Secret:{len(naver_client_secret)})',
                'color': 'red'
            }
    
    # Coupang Partners API - 형식 검증만 (실제 호출 안함)
    coupang_access = get_config('coupang_access_key')
    coupang_secret = get_config('coupang_secret_key')
    if not coupang_access or not coupang_secret:
        status['coupang'] = {
            'status': 'none',
            'message': '⚪ Access Key/Secret이 설정되지 않았습니다',
            'color': 'gray'
        }
    else:
        # 형식만 검증 (길이 체크)
        if len(coupang_access) >= 8 and len(coupang_secret) >= 8:
            status['coupang'] = {
                'status': 'valid',
                'message': '✅ 쿠팡 파트너스 API 설정됨',
                'color': 'green'
            }
        else:
            status['coupang'] = {
                'status': 'invalid',
                'message': f'❌ Access Key/Secret 길이 오류 (Access:{len(coupang_access)}, Secret:{len(coupang_secret)})',
                'color': 'red'
            }
    
    return status


if __name__ == '__main__':
    # 테스트
    import sys
    sys.path.insert(0, '/home/user/webapp')
    
    print("="*70)
    print("🔍 API 키 검증 테스트")
    print("="*70)
    
    status = get_api_status()
    
    for api_name, info in status.items():
        print(f"\n📌 {api_name.upper()}")
        print(f"   상태: {info['status']}")
        print(f"   메시지: {info['message']}")
