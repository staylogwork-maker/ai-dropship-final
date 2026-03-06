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
        model = genai.GenerativeModel('gemini-2.5-flash')  # ✅ 작동하는 최신 모델
        
        # 간단한 테스트 요청
        response = model.generate_content("Say 'OK' if you can read this")
        
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
            return False, "⚠️ 할당량 초과. 잠시 후 다시 시도하세요."
        else:
            return False, f"❌ 검증 실패: {error_msg[:100]}"


def validate_openai_api_key(api_key: str) -> Tuple[bool, str]:
    """
    OpenAI API 키 유효성 검사
    
    Returns:
        (is_valid, message)
    """
    if not api_key or len(api_key) < 40:
        return False, "❌ API 키가 너무 짧습니다 (최소 40자)"
    
    if not (api_key.startswith('sk-') or api_key.startswith('sk-proj-')):
        return False, "❌ OpenAI API 키는 'sk-' 또는 'sk-proj-'로 시작해야 합니다"
    
    try:
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        # 간단한 테스트 요청 (최소 비용)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5
        )
        
        if response.choices[0].message.content:
            return True, "✅ OpenAI API 키가 유효합니다"
        else:
            return False, "❌ API 응답이 비어있습니다"
            
    except openai.AuthenticationError:
        return False, "❌ 인증 실패. API 키가 유효하지 않거나 만료되었습니다."
    except openai.PermissionDeniedError:
        return False, "❌ 권한 없음. API 키 권한을 확인하세요."
    except openai.RateLimitError:
        return False, "⚠️ 할당량 초과 또는 크레딧 부족. 계정을 확인하세요."
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            return False, "❌ 인증 실패. API 키를 다시 확인하세요."
        elif "429" in error_msg:
            return False, "⚠️ 요청 한도 초과. 잠시 후 다시 시도하세요."
        else:
            return False, f"❌ 검증 실패: {error_msg[:100]}"


def get_api_status() -> Dict[str, Dict[str, str]]:
    """
    현재 저장된 모든 API 키 상태 확인
    
    Returns:
        {
            'gemini': {'status': 'valid/invalid/none', 'message': '...'},
            'openai': {'status': 'valid/invalid/none', 'message': '...'}
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
