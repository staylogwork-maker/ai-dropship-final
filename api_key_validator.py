"""
API 키 검증 시스템
- 설정 페이지에서 API 키 입력 시 즉시 검증
- 유효하지 않으면 저장 거부
- 대시보드에서 API 상태 실시간 표시
"""
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


def validate_gemini_api_key(api_key: str) -> Tuple[bool, str]:
    """
    Gemini API 키 유효성 검사
    
    Returns:
        (is_valid, message)
    """
    if not api_key or len(api_key) < 30:
        return False, "❌ API 키가 너무 짧습니다 (최소 30자)"
    
    if not api_key.startswith('AIza'):
        return False, "❌ Gemini API 키는 'AIza'로 시작해야 합니다"
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        
        # gemini-2.0-flash (더 높은 무료 한도)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 간단한 테스트 요청 (최소 토큰)
        response = model.generate_content("OK")
        
        if response.text:
            return True, "✅ Gemini API 키가 유효합니다"
        else:
            return False, "❌ API 응답이 비어있습니다"
            
    except Exception as e:
        error_msg = str(e)
        
        if "API_KEY_INVALID" in error_msg:
            return False, "❌ 유효하지 않은 API 키입니다. 새로 발급받으세요."
        elif "PERMISSION_DENIED" in error_msg:
            return False, "❌ API가 활성화되지 않았습니다. Google AI Studio에서 활성화하세요."
        elif "429" in error_msg or "quota" in error_msg.lower():
            # 할당량 초과는 키가 유효하다는 의미
            return True, "✅ Gemini API 키 유효 (일시적 할당량 초과)"
        else:
            return False, f"❌ 검증 실패: {error_msg[:100]}"


def validate_openai_api_key(api_key: str) -> Tuple[bool, str]:
    """
    OpenAI API 키 유효성 검사 (requests 라이브러리 사용)
    
    Returns:
        (is_valid, message)
    """
    if not api_key or len(api_key) < 40:
        return False, "❌ API 키가 너무 짧습니다 (최소 40자)"
    
    if not (api_key.startswith('sk-') or api_key.startswith('sk-proj-')):
        return False, "❌ OpenAI API 키는 'sk-' 또는 'sk-proj-'로 시작해야 합니다"
    
    try:
        import requests
        
        # 직접 HTTP 요청 (OpenAI SDK 버그 회피)
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': 'OK'}],
                'max_tokens': 3
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "✅ OpenAI API 키가 유효합니다"
        elif response.status_code == 401:
            return False, "❌ 인증 실패. API 키가 유효하지 않거나 만료되었습니다."
        elif response.status_code == 429:
            return False, "⚠️ 할당량 초과 또는 크레딧 부족. 계정을 확인하세요."
        elif response.status_code == 403:
            return False, "❌ 권한 없음. API 키 권한을 확인하세요."
        else:
            error_text = response.text[:200]
            return False, f"❌ 검증 실패 (HTTP {response.status_code}): {error_text}"
            
    except Exception as e:
        return False, f"❌ 연결 실패: {str(e)[:100]}"


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
    
    # Naver Shopping API - 실제 API 호출 테스트
    naver_client_id = get_config('naver_client_id')
    naver_client_secret = get_config('naver_client_secret')
    if not naver_client_id or not naver_client_secret:
        status['naver'] = {
            'status': 'none',
            'message': '⚪ Client ID/Secret이 설정되지 않았습니다',
            'color': 'gray'
        }
    else:
        try:
            import requests
            # 실제 네이버 쇼핑 API 호출 (검색 1건)
            response = requests.get(
                'https://openapi.naver.com/v1/search/shop.json',
                headers={
                    'X-Naver-Client-Id': naver_client_id,
                    'X-Naver-Client-Secret': naver_client_secret
                },
                params={'query': '테스트', 'display': 1},
                timeout=5
            )
            
            if response.status_code == 200:
                status['naver'] = {
                    'status': 'valid',
                    'message': '✅ 네이버 쇼핑 API 정상 작동',
                    'color': 'green'
                }
            elif response.status_code == 401:
                status['naver'] = {
                    'status': 'invalid',
                    'message': '❌ 인증 실패 (Client ID/Secret 오류)',
                    'color': 'red'
                }
            elif response.status_code == 403:
                status['naver'] = {
                    'status': 'invalid',
                    'message': '❌ 권한 없음 (API 미승인 또는 만료)',
                    'color': 'red'
                }
            elif response.status_code == 429:
                status['naver'] = {
                    'status': 'valid',
                    'message': '⚠️ API 키 유효 (호출 한도 초과)',
                    'color': 'green'
                }
            else:
                status['naver'] = {
                    'status': 'invalid',
                    'message': f'❌ HTTP {response.status_code} 오류',
                    'color': 'red'
                }
        except Exception as e:
            status['naver'] = {
                'status': 'invalid',
                'message': f'❌ 연결 실패: {str(e)[:50]}',
                'color': 'red'
            }
    
    # Coupang Partners API - 실제 API 호출 테스트
    coupang_access = get_config('coupang_access_key')
    coupang_secret = get_config('coupang_secret_key')
    if not coupang_access or not coupang_secret:
        status['coupang'] = {
            'status': 'none',
            'message': '⚪ Access Key/Secret이 설정되지 않았습니다',
            'color': 'gray'
        }
    else:
        try:
            import requests
            import hmac
            import hashlib
            import time
            
            # Coupang API 서명 생성
            method = 'GET'
            path = '/v2/providers/affiliate_open_api/apis/openapi/v1/products/bestcategories/dpg'
            timestamp = str(int(time.time() * 1000))
            
            message = timestamp + method + path
            signature = hmac.new(
                coupang_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # API 호출
            response = requests.get(
                f'https://api-gateway.coupang.com{path}',
                headers={
                    'Authorization': f'CEA algorithm=HmacSHA256, access-key={coupang_access}, signed-date={timestamp}, signature={signature}',
                    'Content-Type': 'application/json'
                },
                timeout=5
            )
            
            if response.status_code == 200:
                status['coupang'] = {
                    'status': 'valid',
                    'message': '✅ 쿠팡 파트너스 API 정상 작동',
                    'color': 'green'
                }
            elif response.status_code == 401:
                status['coupang'] = {
                    'status': 'invalid',
                    'message': '❌ 인증 실패 (Access Key/Secret 오류)',
                    'color': 'red'
                }
            elif response.status_code == 403:
                status['coupang'] = {
                    'status': 'invalid',
                    'message': '❌ 권한 없음 (파트너 미승인)',
                    'color': 'red'
                }
            else:
                status['coupang'] = {
                    'status': 'invalid',
                    'message': f'❌ HTTP {response.status_code} 오류',
                    'color': 'red'
                }
        except Exception as e:
            status['coupang'] = {
                'status': 'invalid',
                'message': f'❌ 연결 실패: {str(e)[:50]}',
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
