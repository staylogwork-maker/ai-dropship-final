# 🚀 빠른 배포 가이드

## 📦 저장소 정보
- **Repository**: https://github.com/staylogwork-maker/ai-dropship-final
- **Commit**: cbc60ee
- **Files**: 15개 (2,987줄)

## ⚡ 5분 안에 시작하기

### 1️⃣ 클론 및 설치
```bash
git clone https://github.com/staylogwork-maker/ai-dropship-final.git
cd ai-dropship-final
./run_server.sh
```

### 2️⃣ API 키 설정
```bash
# .env 파일 편집
nano .env

# 필수 항목:
SCRAPINGANT_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
NAVER_CLIENT_ID=your_id_here
NAVER_CLIENT_SECRET=your_secret_here
COUPANG_ACCESS_KEY=your_key_here
COUPANG_SECRET_KEY=your_secret_here
SERVER_STATIC_IP=your_static_ip_here
```

### 3️⃣ 서버 시작
```bash
source venv/bin/activate
python3 app.py
```

### 4️⃣ 접속
- URL: http://localhost:5000
- 계정: admin / admin123
- ⚠️ 첫 로그인 후 비밀번호 변경 필수!

---

## 📊 구현된 기능 체크리스트

### ✅ Module 1: 인프라 & 보안
- [x] Flask 백엔드 + SQLite 데이터베이스
- [x] 세션 인증 (Flask-Login)
- [x] bcrypt 비밀번호 해싱
- [x] 자동 배포 스크립트 (run_server.sh)

### ✅ Module 2: AI 소싱 엔진
- [x] ScrapingAnt API 통합
- [x] browser=true + cookies_persistence=true (캡차 우회)
- [x] 안전 필터 (식품/유아동/화장품/가품 제외)
- [x] 3단계 분석 (스캔 → 필터 → 수익성)
- [x] TOP 3 자동 선정

### ✅ Module 3: 수익성 계산기
- [x] 실시간 CNY→KRW 환율 적용
- [x] 전체 비용 시뮬레이션 (매입가+배송+관부가세+수수료)
- [x] 목표 마진율 자동 필터링
- [x] 옵션별 최고가 기준 방어

### ✅ Module 4: AI 콘텐츠 생성
- [x] GPT-4 마케팅 카피 (Hook-Problem-Solution)
- [x] 이미지 처리 (중국어→한국어 텍스트 오버레이)
- [x] 메타데이터 제거 및 자체 호스팅
- [x] 공지사항 이미지 자동 부착
- [x] 하이브리드 에디터 (드래그앤드롭 지원)

### ✅ Module 5: 주문 관리 시스템
- [x] PCCC (개인통관고유부호) 검증
- [x] 네이버 API 동적 서명 (bcrypt + timestamp)
- [x] 쿠팡 API IP 화이트리스팅 지원
- [x] 양방향 동기화 (발주완료 → 송장입력 → 배송완료)
- [x] 주문 시점 환율 고정 저장

### ✅ Module 6: 리스크 방어
- [x] 매일 자동 재고 체크 (새벽 2시)
- [x] 품절/삭제 상품 자동 감지
- [x] 마켓 상품 자동 '품절' 처리
- [x] 24시간 이내 배송 마감 경고

### ✅ Module 7: 세무 자동화
- [x] 주문별 환율 고정 저장 (audit 대응)
- [x] 배송 완료 시 자동 세무 기록 생성
- [x] 엑셀 자동 다운로드 (국세청 양식)
- [x] 판매대장 자동 집계

### ✅ Module 8: 관리자 대시보드
- [x] 실시간 활동 로그 스트리밍 (SSE)
- [x] 웹 기반 설정 관리 (코드 수정 불필요)
- [x] 1-by-1 상품 승인 방식
- [x] 실시간 통계 카드
- [x] 긴급 주문 하이라이트

---

## 🔧 핵심 기술 구현 상세

### 1. Naver API 동적 서명
```python
# 타임스탬프 + HTTP 메서드 + 경로 조합
message = f"{timestamp}.POST./v1/products"

# HMAC-SHA256 서명 생성
signature = hmac.new(
    client_secret.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()
```

### 2. ScrapingAnt 안티봇 우회
```python
params = {
    'browser': 'true',              # 브라우저 에뮬레이션
    'cookies_persistence': 'true'   # 쿠키 유지 (로그인 상태)
}
```

### 3. 이미지 경량 처리
```python
# GPU 비용 절감: AI Inpainting 대신 Box Overlay 사용
draw.rectangle([x, y, x+w, y+h], fill=(255, 255, 255, 200))
draw.text((x+5, y+5), korean_text, fill=(0, 0, 0, 255))
```

### 4. 환율 고정 저장
```python
# 주문 생성 시 환율 고정 (세무 소명용)
cursor.execute('''
    INSERT INTO orders (applied_exchange_rate, ...)
    VALUES (?, ...)
''', (current_exchange_rate, ...))
```

---

## 📈 코드 통계

- **총 파일**: 15개
- **총 코드 라인**: 2,987줄
- **Python 파일**: 2개 (app.py: 1,216줄)
- **HTML 템플릿**: 6개
- **README**: 488줄 (완전 상세 문서)

---

## 🎯 다음 단계

### 운영 환경 배포
```bash
# 1. 프로덕션 서버에 클론
git clone https://github.com/staylogwork-maker/ai-dropship-final.git

# 2. Gunicorn 설치
pip install gunicorn

# 3. 프로덕션 모드 실행
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 데이터베이스 마이그레이션 (대용량 트래픽 대비)
```bash
# PostgreSQL로 마이그레이션
# 1. PostgreSQL 설치
# 2. app.py에서 DB 연결 문자열 변경
# 3. init_db.py 실행
```

### Nginx 리버스 프록시 설정
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## ⚠️ 중요 체크리스트

- [ ] .env 파일에 모든 API 키 입력
- [ ] 쿠팡 개발자센터에서 서버 IP 화이트리스트 등록
- [ ] 관리자 비밀번호 변경 (admin123 → 강력한 암호)
- [ ] 정기 데이터베이스 백업 설정
- [ ] 환율은 매일 수동/자동 업데이트
- [ ] 1688 로그인 쿠키 갱신 (주기적)

---

## 📞 문의 및 지원

- **GitHub**: https://github.com/staylogwork-maker/ai-dropship-final
- **Issues**: https://github.com/staylogwork-maker/ai-dropship-final/issues

---

## 🎉 완료!

모든 모듈의 구현 및 GitHub Push가 완료되었습니다.

**서버에서 배포를 시작하세요.**
