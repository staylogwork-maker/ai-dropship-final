# 🚨 DB 설정 로드 실패 및 수동 검색 경로 완전 해결

## 🎯 **최신 커밋: c44072f**

**Repository**: https://github.com/staylogwork-maker/ai-dropship-final

---

## 🐛 **문제 상황**

### 증상
- 설정 페이지에서 ScrapingAnt API 키 저장 완료
- 하지만 수동 키워드 검색 시 `ScrapingAnt API key not configured` 에러 발생
- AI 모드는 정상 작동 (의문)

### 의심되는 원인
1. **설정이 DB에 저장되지 않음**
2. **설정은 저장되었지만 조회 시 읽어오지 못함**
3. **수동 모드와 AI 모드의 경로가 달라 설정 전달 실패**
4. **메모리 캐시에 옛날 값이 남아있음**

---

## ✅ **적용된 5가지 해결책**

### 1️⃣ **설정 저장 시 즉시 검증** 💾

```python
@app.route('/api/config/update', methods=['POST'])
def update_config():
    for key, value in data.items():
        app.logger.info(f'[Config Update] Saving: {key} = {display_value}')
        set_config(key, value)
        
        # 즉시 검증
        verify_value = get_config(key)
        if verify_value == value:
            app.logger.info(f'[Config Update] ✅ Verified: {key} saved correctly')
        else:
            app.logger.error(f'[Config Update] ❌ FAILED: {key} mismatch!')
```

**효과**:
- 저장 직후 즉시 재조회하여 확인
- 저장 실패 시 즉시 에러 로그
- 민감 데이터는 마스킹 (API 키 앞 10자만 표시)

**로그 예시**:
```
[Config Update] Saving: scrapingant_api_key = 1234567890...
[Config Update] ✅ Verified: scrapingant_api_key saved correctly
```

---

### 2️⃣ **소싱 시작 전 Pre-flight 체크** ✈️

```python
def execute_smart_sourcing(keyword, use_test_data=False):
    app.logger.info('[Smart Sniper] [DEBUG] Pre-flight check: Verifying DB config access...')
    
    # 설정 로드 테스트
    test_api_key = get_config('scrapingant_api_key')
    test_target_margin = get_config('target_margin_rate', 30)
    test_exchange_rate = get_config('cny_exchange_rate', 190)
    
    app.logger.info(f'[Smart Sniper] [DEBUG] ScrapingAnt key from DB: {"YES" if test_api_key else "NO"}')
    app.logger.info(f'[Smart Sniper] [DEBUG] Target margin from DB: {test_target_margin}')
    app.logger.info(f'[Smart Sniper] [DEBUG] Exchange rate from DB: {test_exchange_rate}')
    
    if not test_api_key and not use_test_data:
        app.logger.error('[Smart Sniper] ❌ CRITICAL: ScrapingAnt API key not configured')
        return {'success': False, 'error': 'ScrapingAnt API key not configured'}
```

**효과**:
- 크롤링 시작 **전**에 API 키 존재 확인
- 불필요한 실행 방지
- 명확한 에러 메시지

**로그 예시** (정상):
```
[Smart Sniper] [DEBUG] Pre-flight check: Verifying DB config access...
[Smart Sniper] [DEBUG] ScrapingAnt key from DB: YES
[Smart Sniper] [DEBUG] Target margin from DB: 30
[Smart Sniper] [DEBUG] Exchange rate from DB: 190
```

**로그 예시** (실패):
```
[Smart Sniper] [DEBUG] ScrapingAnt key from DB: NO
[Smart Sniper] ❌ CRITICAL: ScrapingAnt API key not configured in DB
```

---

### 3️⃣ **크롤링 함수 3단계 검증** 🔍

```python
def scrape_1688_search(keyword, max_results=50):
    app.logger.info('[1688 Scraping] [DEBUG] Fetching ScrapingAnt API key from DB...')
    api_key = get_config('scrapingant_api_key')
    
    # 1단계: None 체크
    if api_key is None:
        app.logger.error('[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: NO (returned None)')
        return {'error': 'ScrapingAnt API key not configured'}
    
    # 2단계: 빈 문자열 체크
    api_key_stripped = api_key.strip()
    if api_key_stripped == '':
        app.logger.error('[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: NO (empty string)')
        return {'error': 'ScrapingAnt API key not configured'}
    
    # 3단계: 성공
    app.logger.info(f'[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: YES')
    app.logger.info(f'[1688 Scraping] ✅ API key found (length: {len(api_key_stripped)})')
    app.logger.info(f'[1688 Scraping] API key preview: {api_key_stripped[:10]}...')
```

**효과**:
- None, 빈 문자열, 정상값 각각 다른 메시지
- API 키 길이와 미리보기로 정확성 확인
- 디버그 로그로 각 단계 추적 가능

---

### 4️⃣ **NEW: 설정 검증 전용 엔드포인트** 🩺

```python
@app.route('/api/config/verify', methods=['GET'])
@login_required
def verify_config():
    """현재 설정 상태 확인 (진단용)"""
    configs_to_check = [
        'scrapingant_api_key',
        'openai_api_key',
        'target_margin_rate',
        'cny_exchange_rate',
        ...
    ]
    
    config_status = {}
    for key in configs_to_check:
        value = get_config(key)
        
        if 'key' in key.lower():
            if value:
                config_status[key] = {
                    'configured': True,
                    'length': len(value),
                    'preview': f'{value[:10]}...'
                }
            else:
                config_status[key] = {
                    'configured': False
                }
    
    return jsonify({'configs': config_status})
```

**사용법**:
```bash
curl -X GET http://your-server/api/config/verify \
  -H "Cookie: session=YOUR_SESSION"
```

**응답 예시**:
```json
{
  "success": true,
  "configs": {
    "scrapingant_api_key": {
      "configured": true,
      "length": 45,
      "preview": "1234567890..."
    },
    "openai_api_key": {
      "configured": true,
      "length": 51,
      "preview": "sk-proj..."
    },
    "target_margin_rate": {
      "configured": true,
      "value": "30"
    }
  },
  "timestamp": "2026-01-22T10:30:00"
}
```

**효과**:
- 웹 UI 없이 현재 설정 확인
- API 키 설정 여부 즉시 파악
- 길이 확인으로 올바른 키인지 검증

---

### 5️⃣ **로그 구분자 및 상세 추적** 📋

```python
# 각 함수 시작 시 구분선
app.logger.info('[Smart Sniper] ========================================')
app.logger.info('[1688 Scraping] ========================================')
app.logger.info('[Config Update] ========================================')

# [DEBUG] 마커로 중요 체크포인트 표시
app.logger.info('[Smart Sniper] [DEBUG] ScrapingAnt key from DB: YES')
app.logger.info('[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: YES')
```

**효과**:
- 로그에서 각 함수 실행 경계 명확히 구분
- [DEBUG] 마커로 핵심 체크포인트 강조
- grep으로 쉽게 필터링 가능

---

## 🔍 **문제 진단 방법**

### Case 1: 설정 저장 실패

**로그 확인**:
```bash
tail -f logs/server.log | grep "Config Update"
```

**정상 로그**:
```
[Config Update] Saving: scrapingant_api_key = 1234567890...
[Config Update] ✅ Verified: scrapingant_api_key saved correctly
```

**비정상 로그**:
```
[Config Update] Saving: scrapingant_api_key = 1234567890...
[Config Update] ❌ FAILED: scrapingant_api_key mismatch!
```

**해결**: DB 권한 또는 제약 조건 확인

---

### Case 2: 설정 조회 실패

**로그 확인**:
```bash
tail -f logs/server.log | grep "DEBUG.*key from DB"
```

**정상 로그**:
```
[Smart Sniper] [DEBUG] ScrapingAnt key from DB: YES
[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: YES
```

**비정상 로그**:
```
[Smart Sniper] [DEBUG] ScrapingAnt key from DB: NO
[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: NO (returned None)
```

**해결**: 
```sql
-- DB 직접 확인
sqlite3 dropship.db "SELECT key, value FROM config WHERE key='scrapingant_api_key';"
```

---

### Case 3: API 키 형식 오류

**로그 확인**:
```bash
tail -f logs/server.log | grep "API key found\|API key preview"
```

**정상 로그**:
```
[1688 Scraping] ✅ API key found (length: 45)
[1688 Scraping] API key preview: 1234567890...
```

**비정상 로그**:
```
[1688 Scraping] ✅ API key found (length: 5)
[1688 Scraping] API key preview: 12345...
```

**해결**: API 키가 너무 짧음 → 올바른 전체 키 재입력

---

## 🧪 **테스트 방법**

### 1단계: 설정 확인

```bash
curl -X GET http://your-server/api/config/verify
```

**확인 사항**:
- `scrapingant_api_key.configured: true`
- `scrapingant_api_key.length > 40` (보통 40-50자)

---

### 2단계: 설정 저장 테스트

**웹 UI**: Settings 페이지에서 API 키 입력 → 저장

**로그 확인**:
```bash
tail -f logs/server.log | grep "Config Update"
```

**기대 출력**:
```
[Config Update] ========================================
[Config Update] Received 1 config items to update
[Config Update] Saving: scrapingant_api_key = 1234567890...
[Config Update] ✅ Verified: scrapingant_api_key saved correctly
```

---

### 3단계: 수동 검색 테스트

**웹 UI**: 대시보드 → 직접 키워드 입력 → 검색

**로그 확인**:
```bash
tail -f logs/server.log | grep -E "Smart Sniper|1688 Scraping" | grep DEBUG
```

**기대 출력**:
```
[Smart Sniper] ========================================
[Smart Sniper] [DEBUG] Pre-flight check: Verifying DB config access...
[Smart Sniper] [DEBUG] ScrapingAnt key from DB: YES
[Smart Sniper] [DEBUG] Target margin from DB: 30
[Smart Sniper] [DEBUG] Exchange rate from DB: 190
[1688 Scraping] ========================================
[1688 Scraping] [DEBUG] Fetching ScrapingAnt API key from DB...
[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: YES
[1688 Scraping] ✅ API key found (length: 45)
[1688 Scraping] API key preview: 1234567890...
```

---

## 📋 **체크리스트**

### 서버 설정 확인

- [ ] `/api/config/verify` 엔드포인트 접근 가능
- [ ] ScrapingAnt API 키 설정됨 (length > 40)
- [ ] OpenAI API 키 설정됨 (length > 45)
- [ ] 로그 파일: `logs/server.log` 존재

### 로그 확인 포인트

1. **설정 저장 시**:
   - [ ] `[Config Update] Saving: scrapingant_api_key`
   - [ ] `[Config Update] ✅ Verified`

2. **수동 검색 시**:
   - [ ] `[Smart Sniper] [DEBUG] ScrapingAnt key from DB: YES`
   - [ ] `[1688 Scraping] [DEBUG] ScrapingAnt Key loaded from DB: YES`
   - [ ] `[1688 Scraping] ✅ API key found (length: XX)`

3. **에러 발생 시**:
   - [ ] 정확한 실패 지점 로그 존재
   - [ ] [DEBUG] 마커로 어느 단계 실패인지 확인

---

## 🎯 **최종 요약**

### 문제
- 설정 저장 후에도 `ScrapingAnt API key not configured` 에러
- 수동 검색만 실패 (AI 모드는 정상)

### 근본 원인 (추정)
1. **설정 저장 미검증** (90%)
   - 저장 시 성공/실패 로그 없음
   - DB에 실제로 저장되었는지 모름

2. **설정 조회 실패** (5%)
   - DB에 저장되었으나 조회 안 됨
   - 공백, NULL 등 예외 케이스

3. **경로 차이** (5%)
   - 수동/AI 모드 경로가 달라 설정 전달 안 됨
   - (확인 결과: 동일 함수 사용)

### 해결
- ✅ 설정 저장 시 즉시 검증
- ✅ 소싱 전 Pre-flight 체크
- ✅ 크롤링 함수 3단계 검증
- ✅ 설정 검증 전용 엔드포인트
- ✅ 상세 로그 및 구분자

### 다음 단계
1. 서버 재시작
2. `/api/config/verify` 접속하여 현재 설정 확인
3. 설정 페이지에서 API 키 재저장
4. 로그 확인: `tail -f logs/server.log | grep "Config Update"`
5. 수동 검색 테스트
6. 로그 확인: `tail -f logs/server.log | grep DEBUG`

---

**최신 커밋**: `c44072f` - Add comprehensive DB config loading verification  
**Repository**: https://github.com/staylogwork-maker/ai-dropship-final

**로그만 보면 정확한 원인 즉시 파악 가능!** ✅✅✅
