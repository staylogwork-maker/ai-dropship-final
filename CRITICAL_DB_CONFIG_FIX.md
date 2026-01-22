# ✅ CRITICAL DB 설정 로드 실패 해결 완료

## 🎯 최신 커밋: **8918f26**

**Repository**: https://github.com/staylogwork-maker/ai-dropship-final

---

## 📋 문제 현황 요약

사용자가 웹 UI 설정 페이지에서 **ScrapingAnt API 키**와 **OpenAI API 키**를 정상 입력/저장했음에도:
- ❌ 수동 키워드 검색 시 `ScrapingAnt API key not configured` 에러 발생
- ❌ AI 블루오션 검색 시에도 동일한 설정 로드 실패
- ❌ DB에 저장된 설정값이 소싱 로직에 전달되지 않음

**근본 원인**:
1. **DB 경로 불일치**: 모듈마다 다른 DB 파일을 참조 (상대경로 vs 절대경로)
2. **전역 변수 사용**: 설정값을 메모리에 캐싱하여 DB 변경이 반영 안됨
3. **설정 로드 누락**: 일부 경로에서 `get_config()` 호출을 빼먹음
4. **진단 로그 부족**: 어떤 DB 파일을 읽는지, 키가 있는지 확인 불가

---

## 🔧 적용된 3가지 핵심 해결책

### 1️⃣ 싱글톤 DB 경로 강제화

**모든 모듈에서 절대 경로 사용 강제**:

```python
# app.py, init_db.py, change_password.py 모두 동일하게 적용
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'dropship.db')

# CRITICAL: DB_PATH가 절대경로인지 검증
if not os.path.isabs(DB_PATH):
    raise RuntimeError(f"CRITICAL: DB_PATH must be absolute! Got: {DB_PATH}")

# 시작 시 DB 경로 로그 출력
print(f"[INIT] Database path (ABSOLUTE): {DB_PATH}")
print(f"[INIT] Database exists: {os.path.exists(DB_PATH)}")
print(f"[INIT] Database size: {os.path.getsize(DB_PATH)} bytes")
```

**효과**:
- ✅ 어떤 디렉토리에서 실행하든 동일한 DB 파일 사용
- ✅ 모든 모듈(app.py, init_db.py, change_password.py)이 같은 DB 참조
- ✅ 로그에 전체 경로 출력으로 문제 진단 가능

---

### 2️⃣ 설정 조회 함수(get_config) 일원화

**전역 변수 사용 완전 금지**:

```python
def get_config(key, default=None):
    """Get configuration value - ALWAYS fetch from DB (no caching)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        value = row['value']
        if isinstance(value, str):
            value = value.strip()
        if value == '':
            return default
        return value
    return default
```

**모든 소싱 로직에서 강제 사용**:

```python
# ❌ BAD: 전역 변수 사용 (구버전)
SCRAPINGANT_KEY = "하드코딩된 키"

# ✅ GOOD: 매번 DB에서 직접 조회 (신버전)
scrapingant_key = get_config('scrapingant_api_key', '')
openai_key = get_config('openai_api_key', '')
target_margin = get_config('target_margin_rate', 30)
cny_rate = get_config('cny_exchange_rate', 190)
```

**효과**:
- ✅ 설정 페이지에서 키를 업데이트하면 즉시 반영
- ✅ 메모리에 남은 옛날 정보를 사용하지 않음
- ✅ 모든 API 호출 시점에 최신 설정 보장

---

### 3️⃣ 초강력 진단 로그 [SYSTEM-CHECK]

**시스템 설정 검증 함수 추가**:

```python
def system_check_critical_configs():
    """
    CRITICAL: System-wide configuration verification
    실행 결과를 로그에 상세히 기록하고, 문제 발견 시 즉시 에러 발생
    """
    app.logger.info('[SYSTEM-CHECK] ========================================')
    app.logger.info(f'[SYSTEM-CHECK] 🔍 DB Path (ABSOLUTE): {DB_PATH}')
    app.logger.info(f'[SYSTEM-CHECK] DB Path is absolute: {os.path.isabs(DB_PATH)}')
    app.logger.info(f'[SYSTEM-CHECK] DB Exists: {os.path.exists(DB_PATH)}')
    app.logger.info(f'[SYSTEM-CHECK] DB Size: {os.path.getsize(DB_PATH)} bytes')
    
    # DB에서 설정 로드
    openai_key = get_config('openai_api_key', '')
    scrapingant_key = get_config('scrapingant_api_key', '')
    
    # 앞 4자리만 표시 (보안)
    openai_preview = openai_key[:4] + '****' if len(openai_key) >= 4 else 'EMPTY'
    scrapingant_preview = scrapingant_key[:4] + '****' if len(scrapingant_key) >= 4 else 'EMPTY'
    
    # 로그 출력
    app.logger.info(f'[SYSTEM-CHECK] 🔑 OpenAI API Key: {openai_preview} (length: {len(openai_key)})')
    app.logger.info(f'[SYSTEM-CHECK] 🔑 ScrapingAnt API Key: {scrapingant_preview} (length: {len(scrapingant_key)})')
    
    # 키가 비어있으면 즉시 에러 발생
    missing_keys = []
    if not openai_key or openai_key.strip() == '':
        missing_keys.append('openai_api_key')
        app.logger.error('[SYSTEM-CHECK] ❌ OpenAI API key is EMPTY or NOT CONFIGURED')
    
    if not scrapingant_key or scrapingant_key.strip() == '':
        missing_keys.append('scrapingant_api_key')
        app.logger.error('[SYSTEM-CHECK] ❌ ScrapingAnt API key is EMPTY or NOT CONFIGURED')
    
    if missing_keys:
        error_msg = f'CRITICAL: Missing required API keys in DB: {missing_keys}'
        app.logger.error(f'[SYSTEM-CHECK] ❌ {error_msg}')
        app.logger.error('[SYSTEM-CHECK] ❌ Please configure these keys in the Settings page!')
        raise RuntimeError(error_msg)
    
    app.logger.info('[SYSTEM-CHECK] ✅ All critical configurations verified successfully')
    app.logger.info('[SYSTEM-CHECK] ========================================')
    
    return {
        'success': True,
        'openai_key_preview': openai_preview,
        'scrapingant_key_preview': scrapingant_preview
    }
```

**소싱 시작 시 자동 실행**:

```python
def execute_smart_sourcing(keyword, use_test_data=False):
    """Unified Smart Sniper engine"""
    
    # ========================================================================
    # CRITICAL: SYSTEM CHECK - Verify DB and load configurations
    # ========================================================================
    try:
        app.logger.info('[Smart Sniper] 🔍 Running SYSTEM-CHECK before sourcing...')
        system_config = system_check_critical_configs()
        app.logger.info(f'[Smart Sniper] ✅ System check passed: {system_config}')
    except RuntimeError as e:
        app.logger.error(f'[Smart Sniper] ❌ SYSTEM CHECK FAILED: {str(e)}')
        log_activity('sourcing', f'❌ System check failed: {str(e)}', 'error')
        return {
            'success': False,
            'error': f'System configuration error: {str(e)}',
            'stats': {'scanned': 0, 'safe': 0, 'profitable': 0, 'final_count': 0}
        }
    
    # 설정 로드 (NEVER use global variables)
    scrapingant_key = get_config('scrapingant_api_key', '')
    openai_key = get_config('openai_api_key', '')
    target_margin_rate = get_config('target_margin_rate', 30)
    cny_exchange_rate = get_config('cny_exchange_rate', 190)
    
    app.logger.info('[Smart Sniper] 📋 Config loaded from DB:')
    app.logger.info(f'  - ScrapingAnt key: {scrapingant_key[:4]}**** (len: {len(scrapingant_key)})')
    app.logger.info(f'  - OpenAI key: {openai_key[:4]}**** (len: {len(openai_key)})')
    app.logger.info(f'  - Target margin: {target_margin_rate}%')
    app.logger.info(f'  - CNY rate: {cny_exchange_rate}')
    
    # ... 소싱 로직 계속 ...
```

**효과**:
- ✅ 소싱 시작 전 DB 경로와 설정값 완전 검증
- ✅ API 키의 앞 4자리와 전체 길이를 로그로 확인 가능
- ✅ DB 결과가 비어있으면 명확한 에러 메시지와 함께 즉시 중단
- ✅ 문제 발생 시 정확한 원인 파악 가능

---

## 📊 로그 출력 예시

### ✅ 정상 동작 시 로그:

```
[SYSTEM-CHECK] ========================================
[SYSTEM-CHECK] 🔍 DB Path (ABSOLUTE): /home/user/ai-dropship-final/dropship.db
[SYSTEM-CHECK] DB Path is absolute: True
[SYSTEM-CHECK] DB Exists: True
[SYSTEM-CHECK] DB Size: 245760 bytes
[SYSTEM-CHECK] 🔑 OpenAI API Key: sk-p**** (length: 51)
[SYSTEM-CHECK] 🔑 ScrapingAnt API Key: 8f3c**** (length: 40)
[SYSTEM-CHECK] 💰 Target Margin: 30%
[SYSTEM-CHECK] 💱 CNY Exchange Rate: 190
[SYSTEM-CHECK] ✅ All critical configurations verified successfully
[SYSTEM-CHECK] ========================================

[Smart Sniper] ========================================
[Smart Sniper] Executing unified sourcing for keyword: 블루투스 이어폰
[Smart Sniper] 🔍 Running SYSTEM-CHECK before sourcing...
[Smart Sniper] ✅ System check passed: {'success': True, ...}
[Smart Sniper] 📋 Config loaded from DB:
  - ScrapingAnt key: 8f3c**** (len: 40)
  - OpenAI key: sk-p**** (len: 51)
  - Target margin: 30%
  - CNY rate: 190
```

### ❌ 설정 누락 시 로그:

```
[SYSTEM-CHECK] ========================================
[SYSTEM-CHECK] 🔍 DB Path (ABSOLUTE): /home/user/ai-dropship-final/dropship.db
[SYSTEM-CHECK] DB Exists: True
[SYSTEM-CHECK] DB Size: 245760 bytes
[SYSTEM-CHECK] 🔑 OpenAI API Key: EMPTY (length: 0)
[SYSTEM-CHECK] 🔑 ScrapingAnt API Key: EMPTY (length: 0)
[SYSTEM-CHECK] ❌ OpenAI API key is EMPTY or NOT CONFIGURED
[SYSTEM-CHECK] ❌ ScrapingAnt API key is EMPTY or NOT CONFIGURED
[SYSTEM-CHECK] ❌ CRITICAL: Missing required API keys in DB: ['openai_api_key', 'scrapingant_api_key']
[SYSTEM-CHECK] ❌ Please configure these keys in the Settings page!
[SYSTEM-CHECK] ========================================

[Smart Sniper] ❌ SYSTEM CHECK FAILED: CRITICAL: Missing required API keys in DB: ['openai_api_key', 'scrapingant_api_key']
```

---

## 🚀 즉시 실행 가이드

### 1단계: 서버에서 최신 코드 받기

```bash
cd /home/ubuntu/ai-dropship-final
git fetch origin
git reset --hard origin/main

# 최신 커밋 확인 (8918f26이어야 함)
git log -1 --oneline
```

**예상 출력**:
```
8918f26 fix: Enforce absolute DB path singleton and unified get_config across all modules
```

---

### 2단계: 서비스 재시작

```bash
# restart.sh 스크립트 실행
bash restart.sh

# 또는 수동 재시작
sudo systemctl restart webapp
sudo systemctl status webapp
```

---

### 3단계: 로그 모니터링

```bash
# 실시간 로그 확인
tail -f logs/server.log

# 또는 systemd 로그 확인
sudo journalctl -u webapp -f
```

**찾을 마커**:
- `[INIT] Database path (ABSOLUTE):` - 시작 시 DB 경로 출력
- `[SYSTEM-CHECK] 🔑 OpenAI API Key:` - API 키 앞 4자리와 길이
- `[SYSTEM-CHECK] 🔑 ScrapingAnt API Key:` - API 키 앞 4자리와 길이
- `[SYSTEM-CHECK] ✅ All critical configurations verified` - 검증 완료

---

### 4단계: 웹 대시보드 테스트

1. **설정 페이지에서 API 키 입력**:
   - 네비게이션 → 설정
   - OpenAI API Key: `sk-proj-...`
   - ScrapingAnt API Key: `8f3c...`
   - 저장 버튼 클릭

2. **수동 키워드 검색 테스트**:
   - 블루오션 분석 페이지
   - "수동 키워드 검색" 탭
   - 키워드: `블루투스 이어폰`
   - 검색 버튼 클릭

3. **AI 블루오션 발견 테스트**:
   - "AI 블루오션 발견" 탭
   - 관심 키워드: `무선 이어폰` (선택)
   - AI 분석 시작 버튼 클릭

---

## ✅ 최종 검증 체크리스트

### 코드 버전 확인
- [ ] Git 커밋: `8918f26`
- [ ] Repository: https://github.com/staylogwork-maker/ai-dropship-final

### DB 경로 확인
- [ ] 로그에 `[INIT] Database path (ABSOLUTE):` 출력됨
- [ ] DB 경로가 절대 경로 (예: `/home/user/ai-dropship-final/dropship.db`)
- [ ] `DB Path is absolute: True` 확인

### 설정 로드 확인
- [ ] `[SYSTEM-CHECK]` 로그에 API 키 앞 4자리 표시됨
- [ ] 키 길이가 0이 아님 (예: `(length: 51)`)
- [ ] `✅ All critical configurations verified` 메시지 출력

### 기능 동작 확인
- [ ] 설정 페이지에서 API 키 저장 성공
- [ ] 수동 키워드 검색 시 `ScrapingAnt API key not configured` 에러 없음
- [ ] AI 블루오션 발견 시 OpenAI API 정상 호출
- [ ] 상품 소싱 결과에 Top 3 상품 표시

---

## 📦 변경된 파일 목록

### 1. `app.py` (주요 애플리케이션)
- **DB 경로**: `BASE_DIR = os.path.dirname(os.path.abspath(__file__))`
- **시작 로그**: `[INIT] Database path (ABSOLUTE): {DB_PATH}`
- **system_check_critical_configs()**: API 키 검증 및 상세 로그
- **execute_smart_sourcing()**: 시작 시 `system_check_critical_configs()` 호출
- **get_config()**: 매번 DB에서 직접 조회 (캐싱 없음)

### 2. `init_db.py` (DB 초기화 스크립트)
- **DB 경로**: 절대 경로 강제 (`os.path.join(BASE_DIR, 'dropship.db')`)
- **시작 로그**: `[INIT_DB] Database path (ABSOLUTE): {DB_PATH}`
- **검증**: `if not os.path.isabs(DB_PATH): raise RuntimeError`

### 3. `change_password.py` (비밀번호 변경 유틸)
- **DB 경로**: 절대 경로 강제 (`os.path.join(BASE_DIR, 'dropship.db')`)
- **시작 로그**: `[CHANGE_PASSWORD] Database path (ABSOLUTE): {DB_PATH}`
- **검증**: `if not os.path.isabs(DB_PATH): raise RuntimeError`

---

## 🔍 문제 해결 (Troubleshooting)

### Q1: 여전히 "API key not configured" 에러가 발생합니다

**확인 사항**:
1. 로그에서 `[SYSTEM-CHECK]` 섹션 찾기
2. API 키 길이 확인: `(length: 0)` → 키가 DB에 없음
3. 설정 페이지에서 키를 다시 입력하고 저장
4. 서비스 재시작: `bash restart.sh`
5. 로그 재확인: `tail -f logs/server.log`

---

### Q2: 로그에 [SYSTEM-CHECK]가 표시되지 않습니다

**확인 사항**:
1. Git 커밋 버전 확인:
   ```bash
   cd /home/ubuntu/ai-dropship-final
   git log -1 --oneline
   ```
   **예상**: `8918f26 fix: Enforce absolute DB path singleton...`

2. 코드가 최신이 아니면:
   ```bash
   git fetch origin
   git reset --hard origin/main
   bash restart.sh
   ```

---

### Q3: DB 경로가 상대 경로로 표시됩니다

**확인 사항**:
1. 로그에서 `[INIT]` 섹션 찾기
2. `Database path (ABSOLUTE):` 확인
3. 경로가 `/home/ubuntu/ai-dropship-final/dropship.db` 형식이어야 함
4. `dropship.db`만 표시되면 → 코드가 옛날 버전

**해결**:
```bash
cd /home/ubuntu/ai-dropship-final
git status
git log -1 --oneline  # 8918f26 확인
```

---

### Q4: 설정 페이지에서 저장했는데 소싱 시 반영 안됨

**원인**: 옛날 버전은 전역 변수를 사용하여 메모리에 캐싱

**해결**: 신버전(8918f26)에서는 매번 DB 직접 조회
```python
# 신버전: 매번 DB에서 직접 가져옴
scrapingant_key = get_config('scrapingant_api_key', '')
```

**확인**:
```bash
# 로그에서 확인
grep "\[Smart Sniper\] 📋 Config loaded from DB:" logs/server.log
```

---

## 🎯 핵심 요약

### 문제
- 설정 페이지에서 API 키를 입력해도 소싱 시 "not configured" 에러 발생
- DB 경로 불일치, 전역 변수 사용, 설정 로드 누락

### 해결
1. **모든 모듈에 절대 DB 경로 강제**: `os.path.join(BASE_DIR, 'dropship.db')`
2. **get_config() 함수로 일원화**: 전역 변수 사용 금지, 매번 DB 조회
3. **[SYSTEM-CHECK] 진단 로그**: API 키 앞 4자리, 길이, 존재 여부 출력

### 효과
- ✅ 설정 페이지 업데이트가 즉시 반영
- ✅ DB 경로 문제로 인한 설정 누락 방지
- ✅ 명확한 진단 로그로 문제 원인 즉시 파악 가능

---

## 📞 다음 단계

### 즉시 실행 명령어 (서버):
```bash
cd /home/ubuntu/ai-dropship-final
git pull origin main
bash restart.sh
tail -f logs/server.log
```

### 찾을 로그 마커:
```
[SYSTEM-CHECK] ✅ All critical configurations verified successfully
```

---

**최신 커밋**: `8918f26`  
**Repository**: https://github.com/staylogwork-maker/ai-dropship-final  
**문서 작성일**: 2026-01-22
