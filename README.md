# 🚀 AI Dropshipping ERP System

**완전 자동화된 상용 수준의 드롭쉬핑 솔루션**

1688에서 수익성 높은 상품을 AI가 자동 발굴하고, 콘텐츠를 생성하여 네이버/쿠팡에 등록하는 완전 자동화 시스템입니다.

---

## 📋 목차

- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [설치 방법](#설치-방법)
- [환경 설정](#환경-설정)
- [사용 방법](#사용-방법)
- [모듈 상세](#모듈-상세)
- [보안 고려사항](#보안-고려사항)
- [트러블슈팅](#트러블슈팅)

---

## 🎯 주요 기능

### 1️⃣ AI 소싱 엔진 (트래픽 헌터)
- **1688 자동 스크래핑**: ScrapingAnt API로 슬라이드 캡차 우회
- **3단계 필터링**: 초기스캔(50개) → 안전필터 → 수익성 분석 → TOP 3 선정
- **안전 필터**: 식품/유아동/화장품/가품 자동 제외
- **트래픽 분석**: 최근 7일 급증 상품 탐지

### 2️⃣ 정밀 수익 계산기
- **실시간 환율 적용**: CNY → KRW 자동 계산
- **전체 비용 시뮬레이션**: 매입가 + 배송비 + 관부가세 + 마켓수수료
- **목표 마진 자동 필터**: 설정한 마진율 이하 상품 자동 탈락
- **가격 방어**: 옵션 중 최고가 기준으로 역마진 방지

### 3️⃣ AI 콘텐츠 생성
- **GPT-4 마케팅 카피**: Hook-Problem-Solution 구조
- **이미지 번역**: 중국어 텍스트 영역 자동 감지 → 한국어 오버레이
- **하이브리드 에디터**: 드래그앤드롭으로 이미지/텍스트 수정 가능
- **공지사항 자동 부착**: 해외직구 규정 이미지 자동 추가

### 4️⃣ 양방향 주문 관리
- **PCCC 자동 검증**: 개인통관고유부호 형식 검사
- **실시간 API 동기화**:
  - 발주 완료 → 마켓 "상품 준비 중"
  - 송장 입력 → 마켓 "배송 중"
- **1688 원본 링크**: 주문에서 바로 원본 상품 접근

### 5️⃣ 리스크 방어 시스템
- **재고 봇 (Daily)**: 매일 1688 품절/삭제 상품 자동 감지
- **가격 방어**: 옵션별 최고가 기준으로 매입가 산정
- **배송 마감 알림**: 24시간 이내 주문 빨간색 경고

### 6️⃣ 세무 자동화
- **환율 고정 저장**: 주문 발생 시점의 환율을 DB에 영구 저장
- **엑셀 자동 생성**: 국세청 소명 양식으로 판매대장 다운로드
- **실시간 집계**: 판매가/매입가/수수료/순수익 자동 계산

### 7️⃣ 실시간 대시보드
- **라이브 로그**: 백엔드 작업 상태 실시간 스트리밍
- **웹 기반 설정**: 코드 수정 없이 마진율/환율/API 키 변경
- **1-by-1 승인**: 관리자 최종 확인 후 마켓 등록

---

## 🛠 기술 스택

- **Backend**: Python 3.8+, Flask
- **Database**: SQLite (경량화)
- **Frontend**: Vanilla JS, Tailwind CSS
- **APIs**:
  - ScrapingAnt (1688 스크래핑)
  - OpenAI GPT-4 (콘텐츠 생성)
  - Naver Commerce API (스마트스토어)
  - Coupang Wing API (쿠팡)

---

## 📦 설치 방법

### 자동 설치 (권장)

```bash
# 1. 저장소 클론
git clone https://github.com/YOUR_USERNAME/ai-dropship-final.git
cd ai-dropship-final

# 2. 자동 설치 스크립트 실행
./run_server.sh

# 3. .env 파일 수정 (API 키 입력)
nano .env

# 4. 서버 시작
source venv/bin/activate
python3 app.py
```

### 수동 설치

```bash
# 1. 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 데이터베이스 초기화
python3 init_db.py

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력

# 5. 서버 시작
python3 app.py
```

서버가 시작되면 http://localhost:5000 에서 접속 가능합니다.

---

## ⚙️ 환경 설정

`.env` 파일을 생성하고 다음 항목을 설정하세요:

```bash
# 관리자 계정
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123

# API Keys (필수)
SCRAPINGANT_API_KEY=your_scrapingant_key
OPENAI_API_KEY=your_openai_key

# Naver Commerce API
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret

# Coupang API (IP 화이트리스팅 필수!)
COUPANG_ACCESS_KEY=your_coupang_key
COUPANG_SECRET_KEY=your_coupang_secret
SERVER_STATIC_IP=123.456.789.012

# 수익성 설정
TARGET_MARGIN_RATE=30         # 목표 마진율 (%)
CNY_EXCHANGE_RATE=190         # 위안 환율
EXCHANGE_RATE_BUFFER=1.05     # 환율 버퍼 (안전마진)
SHIPPING_COST_BASE=5000       # 기본 배송비
CUSTOMS_TAX_RATE=0.10         # 관부가세율 (10%)
NAVER_FEE_RATE=0.06           # 네이버 수수료 (6%)
COUPANG_FEE_RATE=0.11         # 쿠팡 수수료 (11%)
```

---

## 🎮 사용 방법

### 1. 로그인
- URL: http://localhost:5000/login
- 기본 계정: `admin` / `admin123`
- ⚠️ 첫 로그인 후 반드시 비밀번호 변경!

### 2. AI 소싱 시작
1. 대시보드에서 **"AI 소싱 시작"** 버튼 클릭
2. 검색 키워드 입력 (예: "무선이어폰", "스마트워치")
3. AI가 자동으로:
   - 1688에서 50개 상품 스캔
   - 안전 필터 적용 (식품/유아동/화장품 제외)
   - 수익성 분석 후 TOP 3 선정

### 3. 콘텐츠 생성 및 승인
1. **상품 관리** 페이지로 이동
2. 상품별 **"콘텐츠 생성"** 버튼 클릭
   - GPT-4가 마케팅 카피 자동 작성
   - 이미지 처리 (중국어 → 한국어)
3. 내용 확인 후 **"승인"** 버튼 클릭

### 4. 마켓 등록
1. 승인된 상품에서 **"마켓 등록"** 버튼 클릭
2. 등록할 마켓 선택 (naver / coupang)
3. API를 통해 자동 등록

### 5. 주문 처리
1. **주문 관리** 페이지에서 신규 주문 확인
2. **"발주완료"** 클릭 → 1688에서 발주
3. **"송장입력"** 클릭 → 송장번호 입력
4. **"배송완료"** 클릭 → 세무 자료 자동 생성

### 6. 세무 자료 다운로드
- 주문 관리 페이지 상단 **"세무자료 엑셀 다운로드"**
- 국세청 소명 양식으로 자동 생성

---

## 📚 모듈 상세

### Module 1: 인증 & 보안
- Flask-Login 기반 세션 인증
- bcrypt 비밀번호 해싱
- CSRF 보호

### Module 2: AI 소싱 엔진
- **ScrapingAnt 설정**:
  ```python
  params = {
      'browser': 'true',           # 브라우저 에뮬레이션
      'cookies_persistence': 'true' # 쿠키 유지 (로그인 유지)
  }
  ```
- **안전 필터 키워드**:
  - 식품: 食品, 零食, 糖果, 饼干, 巧克力, 饮料
  - 유아동: 婴儿, 儿童, 宝宝, 玩具, 奶瓶, 尿布
  - 화장품: 化妆品, 护肤, 面膜, 口红, 眼影
  - 가품: Nike, Adidas, Gucci, LV, Disney, Supreme

### Module 3: 수익 계산
```python
순수익 = 판매가 - (매입가 * 환율 * 버퍼 + 배송비 + 관부가세 + 마켓수수료)

# 예시:
매입가: 50 CNY
환율: 190 KRW
버퍼: 1.05 (5% 안전마진)
→ 매입가(KRW) = 50 * 190 * 1.05 = 9,975원

배송비: 5,000원
관부가세: 9,975 * 0.10 = 998원
총 원가: 9,975 + 5,000 + 998 = 15,973원

목표 마진: 30%
→ 판매가 = 15,973 / (1 - 0.30) = 22,819원
→ 실제 판매가: 22,900원 (100원 단위 반올림)

마켓 수수료(6%): 22,900 * 0.06 = 1,374원
최종 순수익: 22,900 - 15,973 - 1,374 = 5,553원
```

### Module 4: Naver API 인증
네이버 커머스 API는 **동적 서명(Signature)** 방식을 사용합니다:

```python
# 타임스탬프 + HTTP 메서드 + 경로 조합
message = f"{timestamp}.POST./v1/products"

# HMAC-SHA256 서명 생성
signature = hmac.new(
    client_secret.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

# Base64 인코딩
signature_b64 = base64.b64encode(signature.encode())
```

### Module 5: Coupang API 주의사항
⚠️ **IP 화이트리스팅 필수**

쿠팡 API는 보안을 위해 IP 화이트리스트를 사용합니다:
1. 서버의 **고정 IP (Static IP)** 확인
2. 쿠팡 개발자센터에서 IP 등록
3. `.env` 파일에 `SERVER_STATIC_IP` 설정

### Module 6: 재고 모니터링
매일 새벽 2시에 자동 실행:
```python
schedule.every().day.at("02:00").do(run_stock_monitor)
```

감지 항목:
- 상품 삭제 (404 응답)
- 품절 표시 (下架, 已下架, 缺货 텍스트)

감지 시 자동 처리:
- 마켓 상품을 '품절' 상태로 변경
- 로그 기록

---

## 🔒 보안 고려사항

### 1. API 키 관리
- `.env` 파일은 `.gitignore`에 포함 (Git에 업로드 금지)
- 프로덕션 환경에서는 환경변수 또는 Secrets Manager 사용

### 2. 비밀번호
- 초기 비밀번호: `admin123`
- **반드시 첫 로그인 후 변경**
- bcrypt로 해싱되어 DB에 저장

### 3. PCCC (개인통관고유부호)
- 형식: `P + 12자리 숫자` (예: P123456789012)
- 주문 생성 시 자동 검증
- 잘못된 형식은 주문 거부

### 4. 데이터베이스
- SQLite 사용 (파일: `dropship.db`)
- 정기적으로 백업 권장
- 프로덕션에서는 PostgreSQL/MySQL 고려

---

## 🐛 트러블슈팅

### 문제 1: ScrapingAnt 403 Forbidden
**원인**: 1688의 슬라이드 캡차 차단

**해결**:
```python
params = {
    'browser': 'true',              # ✅ 필수
    'cookies_persistence': 'true'   # ✅ 필수
}
```

### 문제 2: Naver API 401 Unauthorized
**원인**: 잘못된 서명(Signature) 생성

**확인사항**:
1. Client ID / Secret 정확한지 확인
2. 타임스탬프가 밀리초 단위인지 확인
3. HTTP 메서드와 경로가 정확한지 확인

### 문제 3: Coupang API 접근 불가
**원인**: IP 화이트리스팅 누락

**해결**:
1. 서버 IP 확인: `curl ifconfig.me`
2. 쿠팡 개발자센터에서 IP 등록
3. `.env`에 `SERVER_STATIC_IP` 설정

### 문제 4: 이미지 처리 실패
**원인**: 한국어 폰트 누락

**해결**:
```bash
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk

# CentOS/RHEL
sudo yum install google-noto-sans-cjk-fonts
```

### 문제 5: 데이터베이스 초기화 필요
```bash
# 기존 DB 백업
cp dropship.db dropship.db.backup

# DB 재초기화
python3 init_db.py
```

---

## 📊 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (Web UI)                  │
│        Tailwind CSS + Vanilla JS + Jinja2               │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/REST
┌─────────────────────▼───────────────────────────────────┐
│                  Flask Backend (app.py)                 │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Module 1: Auth & Security (Flask-Login, bcrypt)   │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Module 2: AI Sourcing (ScrapingAnt, Safety Filter)│ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Module 3: Profit Calculator (Real-time Exchange)  │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Module 4: Content Generator (GPT-4, Image Process)│ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Module 5: OMS (Naver/Coupang API, PCCC Validator) │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Module 6: Risk Defense (Stock Bot, Price Defense) │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Module 7: Tax Automation (Excel Export)           │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Module 8: Dashboard (Live Logs, Config Manager)   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              SQLite Database (dropship.db)              │
│  ┌──────────┬──────────┬──────────┬──────────┬────────┐ │
│  │  users   │ products │  orders  │   tax    │ logs   │ │
│  └──────────┴──────────┴──────────┴──────────┴────────┘ │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   External APIs                         │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │ 1688 via │ OpenAI   │  Naver   │     Coupang      │  │
│  │Scraping  │  GPT-4   │ Commerce │       Wing       │  │
│  │   Ant    │          │   API    │        API       │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📈 성능 최적화

### 이미지 처리
- GPU 사용 최소화 (비용 절감)
- Text Detection → Box Overlay → Text Insert 방식
- 무거운 AI Inpainting 대신 경량 방식 사용

### 데이터베이스
- SQLite 사용 (초기 단계)
- 인덱스 자동 생성 (primary key, foreign key)
- 대용량 트래픽 시 PostgreSQL 마이그레이션 권장

### API 호출 최적화
- 배치 처리로 API 호출 횟수 최소화
- 실패 시 재시도 로직 (exponential backoff)

---

## 🔄 업데이트 로드맵

### v1.1 (예정)
- [ ] 멀티 키워드 배치 소싱
- [ ] 상품 재고 자동 업데이트
- [ ] 텔레그램 알림 연동

### v1.2 (예정)
- [ ] 11번가/G마켓 API 추가
- [ ] 고급 이미지 편집기
- [ ] 대시보드 차트 추가

### v2.0 (장기)
- [ ] PostgreSQL 마이그레이션
- [ ] 멀티 계정 지원
- [ ] AI 자동 가격 조정

---

## 📞 지원 및 문의

- **GitHub Issues**: [https://github.com/YOUR_USERNAME/ai-dropship-final/issues](https://github.com/YOUR_USERNAME/ai-dropship-final/issues)
- **이메일**: support@yourdomain.com

---

## 📜 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## ⚠️ 면책 조항

1. 이 시스템은 개발자 도구이며, 사용자는 각국의 전자상거래 법규를 준수할 책임이 있습니다.
2. API 사용 시 각 플랫폼(Naver, Coupang, 1688)의 이용약관을 확인하세요.
3. 개인통관고유부호(PCCC) 처리 시 개인정보보호법을 준수하세요.
4. 세무 자료는 참고용이며, 정확한 세무 신고는 세무사와 상담하세요.

---

**🎉 이제 AI 드롭쉬핑으로 완전 자동화된 수익 창출을 시작하세요!**

