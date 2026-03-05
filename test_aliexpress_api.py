"""
AliExpress Open Platform API 테스트
공식 문서: https://openservice.aliexpress.com/doc/api.htm
"""
import hashlib
import hmac
import time
import requests
import json

def sign_api_request(app_secret, params):
    """
    AliExpress API 서명 생성
    """
    # 파라미터 정렬
    sorted_params = sorted(params.items())
    
    # 문자열 생성
    sign_str = app_secret
    for key, value in sorted_params:
        sign_str += f"{key}{value}"
    sign_str += app_secret
    
    # MD5 해시
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

def search_products(app_key, app_secret, keyword, page_size=10):
    """
    AliExpress 상품 검색
    """
    # API 엔드포인트
    api_url = "https://api-sg.aliexpress.com/sync"
    
    # 타임스탬프 (밀리초)
    timestamp = str(int(time.time() * 1000))
    
    # 파라미터
    params = {
        'method': 'aliexpress.affiliate.productdetail.get',
        'app_key': app_key,
        'timestamp': timestamp,
        'format': 'json',
        'v': '2.0',
        'sign_method': 'md5',
        'keywords': keyword,
        'page_size': str(page_size),
        'target_currency': 'USD',
        'target_language': 'EN'
    }
    
    # 서명 생성
    params['sign'] = sign_api_request(app_secret, params)
    
    print(f"🔥 API 호출 중: {keyword}")
    print(f"📡 URL: {api_url}")
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        
        print(f"📥 응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공! 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
            return data
        else:
            print(f"❌ 오류: {response.status_code}")
            print(f"응답: {response.text[:500]}")
            return None
    
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("AliExpress API 테스트")
    print("=" * 60)
    
    print("\n⚠️ API 키 입력 필요:")
    print("1. https://open.aliexpress.com 접속")
    print("2. Create App → Affiliate API")
    print("3. App Key & Secret 복사")
    print("\n사용 방법:")
    print("APP_KEY='your_key' APP_SECRET='your_secret' python3 test_aliexpress_api.py")
    print("\n또는 직접 수정:")
    
    # 여기에 API 키 입력
    APP_KEY = ""  # 입력 필요
    APP_SECRET = ""  # 입력 필요
    
    if APP_KEY and APP_SECRET:
        result = search_products(APP_KEY, APP_SECRET, "wireless earphones", 10)
    else:
        print("\n❌ APP_KEY와 APP_SECRET를 입력하세요!")
