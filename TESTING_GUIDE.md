# 🧪 AI 소싱 시스템 테스트 가이드

**작성일**: 2026-03-05  
**커밋**: a8688d5

---

## 빠른 테스트 시나리오

### 시나리오 1: 최소 설정 (OpenAI만)

**목표**: OpenAI API만으로 AI 분석 가능 여부 확인

**설정**:
```bash
# 1. OpenAI API 키만 설정
OpenAI API Key: sk-...
```

**테스트 순서**:
```bash
# 1. 일반 소싱 실행
POST /api/sourcing/start
{
  "keyword": "마우스 패드",
  "mode": "direct"
}

# 예상 결과: 3개 제품 저장됨

# 2. AI 분석 실행
POST /api/sourcing/ai-analyze
{}

# 예상 결과:
# - Coupang 데이터: 없음 (API 미설정)
# - Naver 데이터: 없음 (API 미설정)
# - AI 분석: OpenAI만으로 제한적 분석
# - 보고서: 생성됨 (fallback 데이터 사용)
```

**검증**:
- [ ] AI 분석 API 호출 성공 (200 OK)
- [ ] 보고서 3개 생성됨
- [ ] 각 보고서에 overall_score 존재
- [ ] markdown_report 생성됨
- [ ] Coupang/Naver 데이터는 비어있어도 정상

---

### 시나리오 2: 표준 설정 (OpenAI + Naver)

**목표**: Naver 시장 데이터 포함 분석

**설정**:
```bash
OpenAI API Key: sk-...
Naver Client ID: ...
Naver Client Secret: ...
```

**테스트 순서**:
```bash
# 1. 일반 소싱
POST /api/sourcing/start
{
  "keyword": "실리콘 주방용품",
  "mode": "direct"
}

# 2. AI 분석
POST /api/sourcing/ai-analyze
{
  "keyword": "실리콘 주방용품"
}

# 예상 결과:
# - Naver 데이터: ✅ 가격 분석, 경쟁 수준, 트렌드
# - AI 분석: ✅ 시장 데이터 기반 정확한 분석
# - 보고서: ✅ 상세한 시장 인사이트 포함
```

**검증**:
- [ ] Naver API 호출 성공
- [ ] naver_data.total_products > 0
- [ ] price_analysis 존재
- [ ] market_trend 분석됨 (emerging/rising/stable 등)
- [ ] AI 분석 정확도 향상 확인

---

### 시나리오 3: 완전 설정 (All APIs)

**목표**: 모든 데이터 소스 활용한 최고 품질 분석

**설정**:
```bash
OpenAI API Key: sk-...
Coupang Access Key: ...
Coupang Secret Key: ...
Naver Client ID: ...
Naver Client Secret: ...
```

**테스트 순서**:
```bash
# 1. AI 소싱 (Blue Ocean 모드)
POST /api/sourcing/start
{
  "keyword": "",  # 빈 값 = AI가 키워드 추천
  "mode": "ai_discovery"
}

# 예상 결과:
# - GPT-4가 Blue Ocean 키워드 추천 (예: "무선 마우스패드")
# - 해당 키워드로 자동 소싱

# 2. AI 분석
POST /api/sourcing/ai-analyze
{}

# 예상 결과:
# - Coupang 데이터: ✅ 판매량, 리뷰, 평점, 베스트셀러
# - Naver 데이터: ✅ 가격, 경쟁, 트렌드
# - AI 분석: ✅ 최고 정확도의 종합 분석
# - 보고서: ✅ 완벽한 추천 보고서
```

**검증**:
- [ ] Blue Ocean 키워드 추천 성공
- [ ] Coupang 데이터 수집 성공
  - [ ] estimated_monthly_sales > 0
  - [ ] avg_rating > 0
  - [ ] top_products 존재
- [ ] Naver 데이터 수집 성공
- [ ] AI 분석 4단계 모두 성공:
  - [ ] demand_analysis
  - [ ] competition_analysis
  - [ ] sales_prediction
  - [ ] recommendation
- [ ] overall_score 80+ (높은 품질)

---

## 단위 테스트

### 1. Coupang API 테스트

```bash
cd /home/user/webapp

python3 << 'EOF'
from coupang_api import analyze_coupang_market

result = analyze_coupang_market(
    keyword="드라이기",
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY"
)

print("Success:", result.get('success'))
print("Total Products:", result.get('total_products', 0))
print("Total Reviews:", result.get('total_reviews', 0))
print("Avg Rating:", result.get('avg_rating', 0))
print("Est. Monthly Sales:", result.get('estimated_monthly_sales', 0))
EOF
```

**예상 출력**:
```
Success: True
Total Products: 1247
Total Reviews: 15830
Avg Rating: 4.3
Est. Monthly Sales: 92450
```

---

### 2. Naver API 테스트

```bash
python3 << 'EOF'
from naver_api_enhanced import analyze_naver_market_enhanced

result = analyze_naver_market_enhanced(
    keyword="드라이기",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)

print("Success:", result.get('success'))
print("Total Products:", result.get('total_products', 0))
print("Avg Price:", result.get('price_analysis', {}).get('avg_price', 0))
print("Market Trend:", result.get('market_trend', 'unknown'))
print("Competition:", result.get('competition_analysis', {}).get('level', 'unknown'))
EOF
```

**예상 출력**:
```
Success: True
Total Products: 1589
Avg Price: 85400
Market Trend: stable
Competition: high
```

---

### 3. OpenAI 분석 테스트

```bash
python3 << 'EOF'
from ai_market_analyzer import AIMarketAnalyzer

analyzer = AIMarketAnalyzer(openai_api_key="YOUR_OPENAI_KEY")

# Mock data
product_info = {
    'title': 'Professional Hair Dryer',
    'price': 15.5,
    'category': 'Hair Dryer'
}

coupang_data = {
    'total_products': 1247,
    'total_reviews': 15830,
    'avg_rating': 4.3,
    'estimated_monthly_sales': 92450
}

naver_data = {
    'total_products': 1589,
    'avg_price': 85400,
    'market_trend': 'stable'
}

result = analyzer.analyze_market_demand(product_info, coupang_data, naver_data)

print("Demand Score:", result.get('demand_score', 0))
print("Demand Level:", result.get('demand_level', 'unknown'))
print("Competition:", result.get('competition_level', 'unknown'))
print("Confidence:", result.get('confidence_score', 0))
EOF
```

**예상 출력**:
```
Demand Score: 78
Demand Level: high
Competition: moderate
Confidence: 85
```

---

## 통합 테스트

### 전체 워크플로우 테스트

```bash
cd /home/user/webapp

python3 << 'EOF'
from ai_sourcing_engine import AISourcer

# Initialize
sourcer = AISourcer(
    openai_api_key="YOUR_OPENAI_KEY",
    coupang_access_key="YOUR_COUPANG_KEY",
    coupang_secret_key="YOUR_COUPANG_SECRET",
    naver_client_id="YOUR_NAVER_ID",
    naver_client_secret="YOUR_NAVER_SECRET"
)

# Mock product
product = {
    'title': 'Professional Hair Dryer 2400W',
    'url': 'https://example.com/product',
    'price': 15.5,
    'image': 'https://example.com/image.jpg',
    'category': 'Hair Dryer'
}

# Analyze
analysis = sourcer.analyze_product(product)

if analysis.get('success'):
    print("✅ Analysis Success!")
    print(f"Overall Score: {analysis['ai_analysis']['recommendation']['overall_score']}/100")
    print(f"Recommendation: {analysis['ai_analysis']['recommendation']['recommendation']}")
    print(f"Profit Margin: {analysis['profitability']['profit_margin']:.1f}%")
    print(f"Est. Monthly Sales: {analysis['ai_analysis']['sales_prediction']['estimated_monthly_sales']}")
else:
    print("❌ Analysis Failed")
    print(f"Error: {analysis.get('error')}")
EOF
```

**예상 출력**:
```
✅ Analysis Success!
Overall Score: 82/100
Recommendation: BUY
Profit Margin: 35.2%
Est. Monthly Sales: 45
```

---

## 에러 시나리오 테스트

### 1. OpenAI API 키 없음

```bash
POST /api/sourcing/ai-analyze
{}

# 예상:
{
  "success": false,
  "error": "AI sourcing not available",
  "reason": "OpenAI API key not configured"
}
```

---

### 2. 잘못된 OpenAI API 키

```bash
# 설정에서 잘못된 키 입력
OpenAI API Key: sk-invalid

POST /api/sourcing/ai-analyze
{}

# 예상:
{
  "success": false,
  "error": "OpenAI API error: Authentication failed"
}
```

---

### 3. Coupang API 미승인

```bash
# Coupang 키는 있지만 승인 안 됨 (월 15만원 미달)

POST /api/sourcing/ai-analyze
{}

# 예상:
# - Coupang 데이터 없음 (빈 객체)
# - Naver 데이터로만 분석 진행
# - AI 분석 정상 완료 (Fallback 로직)
{
  "success": true,
  "reports": [...]
}
```

---

### 4. 제품 없음

```bash
# DB에 제품이 없을 때
POST /api/sourcing/ai-analyze
{
  "product_ids": [999, 1000, 1001]
}

# 예상:
{
  "success": false,
  "error": "No products found to analyze"
}
```

---

## 성능 테스트

### 응답 시간 측정

```bash
#!/bin/bash

echo "🚀 AI Sourcing Performance Test"
echo "================================"

# Test 1: Single product
echo -n "Test 1 - Single product (ID 1): "
START=$(date +%s)
curl -s -X POST http://localhost:5000/api/sourcing/ai-analyze \
  -H "Content-Type: application/json" \
  -d '{"product_ids": [1]}' \
  -b "session=..." > /dev/null
END=$(date +%s)
echo "$((END - START))s"

# Test 2: Batch 3 products
echo -n "Test 2 - Batch 3 products: "
START=$(date +%s)
curl -s -X POST http://localhost:5000/api/sourcing/ai-analyze \
  -H "Content-Type: application/json" \
  -d '{}' \
  -b "session=..." > /dev/null
END=$(date +%s)
echo "$((END - START))s"

# Test 3: Batch 10 products
echo -n "Test 3 - Batch 10 products: "
START=$(date +%s)
curl -s -X POST http://localhost:5000/api/sourcing/ai-analyze \
  -H "Content-Type: application/json" \
  -d '{"product_ids": [1,2,3,4,5,6,7,8,9,10]}' \
  -b "session=..." > /dev/null
END=$(date +%s)
echo "$((END - START))s"

echo "================================"
echo "Expected benchmarks:"
echo "- Single: 15-20s"
echo "- Batch 3: 45-60s"
echo "- Batch 10: 150-200s"
```

---

## 품질 검증 체크리스트

### AI 분석 품질

- [ ] **demand_score**: 1-100 범위 내
- [ ] **competition_score**: 1-100 범위 내
- [ ] **overall_score**: 1-100 범위 내
- [ ] **estimated_monthly_sales**: 양수 (0 이상)
- [ ] **success_probability**: 0-100% 범위
- [ ] **recommendation**: STRONG_BUY/BUY/CONSIDER/AVOID/STRONG_AVOID 중 하나
- [ ] **key_insights**: 최소 3개 이상
- [ ] **risk_factors**: 최소 2개 이상
- [ ] **action_items**: 최소 3개 이상

### 보고서 품질

- [ ] **executive_summary**: 한글, 2-3문장
- [ ] **detailed_analysis**: 한글, 5-7문장
- [ ] **markdown_report**: 완전한 마크다운 형식
- [ ] **markdown_report**: 표, 목록, 헤더 포함
- [ ] **전체 길이**: 최소 2000자 이상

### 데이터 품질

- [ ] **Coupang 데이터** (설정 시):
  - [ ] total_products > 0
  - [ ] avg_rating: 0-5 범위
  - [ ] estimated_monthly_sales > 0
  
- [ ] **Naver 데이터** (설정 시):
  - [ ] total_products > 0
  - [ ] avg_price > 0
  - [ ] market_trend: valid enum value
  
- [ ] **Profitability**:
  - [ ] profit_margin: 논리적 범위 (0-100%)
  - [ ] target_price > total_cost
  - [ ] profit_per_unit: 양수 또는 음수 (손실)

---

## 버그 리포트 템플릿

```markdown
## 🐛 버그 리포트

**발생 시간**: 2026-03-05 10:30 KST
**엔드포인트**: POST /api/sourcing/ai-analyze
**사용자**: admin

### 재현 단계
1. ...
2. ...
3. ...

### 예상 결과
...

### 실제 결과
...

### 에러 로그
```
...
```

### 환경
- OpenAI API: ✅ / ❌
- Coupang API: ✅ / ❌
- Naver API: ✅ / ❌
- Flask Version: ...
- Python Version: ...

### 추가 정보
...
```

---

## 다음 단계

### 테스트 완료 후

1. **문제 발견 시**:
   - 버그 리포트 작성
   - 로그 확인 (`flask.log`)
   - GitHub Issue 생성

2. **정상 작동 시**:
   - 프로덕션 배포 준비
   - 사용자 교육 문서 배포
   - 모니터링 설정

3. **추가 개선**:
   - 캐싱 구현 (반복 분석 최적화)
   - 배치 크기 자동 조정
   - 에러 복구 로직 강화

---

**테스트 담당자**: _______________  
**테스트 일자**: _______________  
**결과**: ✅ PASS / ❌ FAIL  
**비고**: _______________________________________
