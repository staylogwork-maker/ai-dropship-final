# 🔧 젠스파크 UI 긴급 수정 명세서

## 📋 문제 상황
**[상품 관리]** 페이지(`/products`)에서 상품 리스트는 보이지만, **상품명을 클릭해도 상세 페이지로 이동하지 않음**.

---

## 🎯 요구사항 (2가지)

### 1️⃣ 상품명 링크화
- **대상**: `templates/products.html` 파일의 36-41번 라인
- **현재 코드**:
```html
<td class="px-6 py-4 text-sm text-gray-900">
    <div class="font-medium">{{ product.title_kr or product.title_cn }}</div>
    <a href="{{ product.original_url }}" target="_blank" class="text-blue-600 hover:underline text-xs">
        1688 원본 링크 →
    </a>
</td>
```

- **수정 후**:
```html
<td class="px-6 py-4 text-sm text-gray-900">
    <div class="font-medium">
        <a href="/products/{{ product.id }}" class="text-gray-900 hover:text-blue-600 hover:underline">
            {{ product.title_kr or product.title_cn }}
        </a>
    </div>
    <a href="{{ product.original_url }}" target="_blank" class="text-blue-600 hover:underline text-xs">
        1688 원본 링크 →
    </a>
</td>
```

---

### 2️⃣ [작업] 컬럼에 [수정] 버튼 추가
- **대상**: `templates/products.html` 파일의 68-81번 라인
- **현재 코드**:
```html
<td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
    {% if product.status == 'pending' %}
    <button onclick="generateContent({{ product.id }})" class="text-blue-600 hover:text-blue-900 mr-3">
        📝 콘텐츠 생성
    </button>
    <button onclick="approveProduct({{ product.id }})" class="text-green-600 hover:text-green-900">
        ✅ 승인
    </button>
    {% elif product.status == 'approved' %}
    <button onclick="registerToMarketplace({{ product.id }})" class="text-purple-600 hover:text-purple-900">
        🚀 마켓 등록
    </button>
    {% endif %}
</td>
```

- **수정 후**:
```html
<td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
    <a href="/products/{{ product.id }}" class="text-indigo-600 hover:text-indigo-900 mr-3">
        ✏️ 수정
    </a>
    {% if product.status == 'pending' %}
    <button onclick="generateContent({{ product.id }})" class="text-blue-600 hover:text-blue-900 mr-3">
        📝 콘텐츠 생성
    </button>
    <button onclick="approveProduct({{ product.id }})" class="text-green-600 hover:text-green-900">
        ✅ 승인
    </button>
    {% elif product.status == 'approved' %}
    <button onclick="registerToMarketplace({{ product.id }})" class="text-purple-600 hover:text-purple-900">
        🚀 마켓 등록
    </button>
    {% endif %}
</td>
```

---

## 🚀 백엔드 API 추가 (app.py)

### 1️⃣ 상품 상세/수정 페이지 라우트 추가
**위치**: `app.py` 파일의 `@app.route('/products')` 함수 바로 아래 (약 2431번 라인)

**추가할 코드**:
```python
@app.route('/products/<int:product_id>')
@login_required
def product_detail(product_id):
    """Product detail and edit page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sourced_products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        flash('상품을 찾을 수 없습니다', 'error')
        return redirect('/products')
    
    return render_template('product_detail.html', product=product)

@app.route('/api/products/<int:product_id>/update', methods=['POST'])
@login_required
def update_product(product_id):
    """Update product information"""
    try:
        data = request.get_json()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Update product fields
        cursor.execute('''
            UPDATE sourced_products 
            SET title_kr = ?, 
                title_cn = ?,
                price_krw = ?,
                profit_margin = ?,
                estimated_profit = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data.get('title_kr'),
            data.get('title_cn'),
            data.get('price_krw'),
            data.get('profit_margin'),
            data.get('estimated_profit'),
            product_id
        ))
        
        conn.commit()
        conn.close()
        
        log_activity('product_update', f'상품 수정: ID {product_id}', 'success')
        
        return jsonify({'success': True, 'message': '상품이 수정되었습니다'})
        
    except Exception as e:
        app.logger.error(f'[Product Update] ❌ Error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

## 📄 프론트엔드 템플릿 생성

### 새 파일: `templates/product_detail.html`

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>상품 수정 - AI Dropshipping ERP</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    {% include 'nav.html' %}
    
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="mb-8">
            <a href="/products" class="text-blue-600 hover:underline mb-2 inline-block">← 상품 목록으로 돌아가기</a>
            <h1 class="text-4xl font-bold text-gray-800 mb-2">✏️ 상품 수정</h1>
            <p class="text-gray-600">상품 정보를 수정하고 저장하세요</p>
        </div>
        
        <!-- Product Edit Form -->
        <div class="bg-white rounded-lg shadow-lg p-8 max-w-4xl">
            <form id="productForm" onsubmit="saveProduct(event)">
                <!-- Product ID (Hidden) -->
                <input type="hidden" id="productId" value="{{ product.id }}">
                
                <!-- Product Image -->
                {% if product.images_json %}
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">상품 이미지</label>
                    <img src="{{ product.images_json|from_json|first }}" alt="Product" class="w-48 h-48 object-cover rounded-lg border border-gray-300">
                </div>
                {% endif %}
                
                <!-- Korean Title -->
                <div class="mb-6">
                    <label for="title_kr" class="block text-sm font-medium text-gray-700 mb-2">
                        한글 상품명 <span class="text-red-500">*</span>
                    </label>
                    <input type="text" id="title_kr" name="title_kr" 
                           value="{{ product.title_kr or '' }}"
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                           required>
                </div>
                
                <!-- Chinese Title -->
                <div class="mb-6">
                    <label for="title_cn" class="block text-sm font-medium text-gray-700 mb-2">
                        중국어 상품명 (원본)
                    </label>
                    <input type="text" id="title_cn" name="title_cn" 
                           value="{{ product.title_cn or '' }}"
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                           readonly>
                </div>
                
                <!-- Price CNY (Read-only) -->
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        중국 가격 (CNY)
                    </label>
                    <input type="text" value="{{ product.price_cny }} 元"
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
                           readonly>
                </div>
                
                <!-- Price KRW -->
                <div class="mb-6">
                    <label for="price_krw" class="block text-sm font-medium text-gray-700 mb-2">
                        판매가 (KRW) <span class="text-red-500">*</span>
                    </label>
                    <input type="number" id="price_krw" name="price_krw" 
                           value="{{ product.price_krw }}"
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                           required>
                </div>
                
                <!-- Profit Margin -->
                <div class="mb-6">
                    <label for="profit_margin" class="block text-sm font-medium text-gray-700 mb-2">
                        마진율 (%)
                    </label>
                    <input type="number" step="0.1" id="profit_margin" name="profit_margin" 
                           value="{{ product.profit_margin }}"
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                </div>
                
                <!-- Estimated Profit -->
                <div class="mb-6">
                    <label for="estimated_profit" class="block text-sm font-medium text-gray-700 mb-2">
                        예상 수익 (KRW)
                    </label>
                    <input type="number" id="estimated_profit" name="estimated_profit" 
                           value="{{ product.estimated_profit }}"
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                </div>
                
                <!-- Original URL (Read-only) -->
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        1688 원본 링크
                    </label>
                    <a href="{{ product.original_url }}" target="_blank" class="text-blue-600 hover:underline">
                        {{ product.original_url }}
                    </a>
                </div>
                
                <!-- Status (Read-only) -->
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        상태
                    </label>
                    <span class="px-3 py-1 inline-flex text-sm font-semibold rounded-full 
                        {% if product.status == 'pending' %}bg-yellow-100 text-yellow-800
                        {% elif product.status == 'approved' %}bg-green-100 text-green-800
                        {% else %}bg-gray-100 text-gray-800{% endif %}">
                        {{ product.status }}
                    </span>
                </div>
                
                <!-- Safety Status -->
                <div class="mb-8">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        안전 상태
                    </label>
                    <span class="px-3 py-1 inline-flex text-sm font-semibold rounded-full 
                        {% if product.safety_status == 'passed' %}bg-green-100 text-green-800
                        {% else %}bg-red-100 text-red-800{% endif %}">
                        {{ product.safety_status }}
                    </span>
                </div>
                
                <!-- Action Buttons -->
                <div class="flex justify-end space-x-4">
                    <a href="/products" class="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
                        취소
                    </a>
                    <button type="submit" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                        💾 저장
                    </button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        async function saveProduct(event) {
            event.preventDefault();
            
            const productId = document.getElementById('productId').value;
            const formData = {
                title_kr: document.getElementById('title_kr').value,
                title_cn: document.getElementById('title_cn').value,
                price_krw: parseInt(document.getElementById('price_krw').value),
                profit_margin: parseFloat(document.getElementById('profit_margin').value),
                estimated_profit: parseInt(document.getElementById('estimated_profit').value)
            };
            
            try {
                const response = await fetch(`/api/products/${productId}/update`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ 상품이 저장되었습니다!');
                    window.location.href = '/products';
                } else {
                    alert('❌ 실패: ' + (result.error || '알 수 없는 오류'));
                }
            } catch (error) {
                alert('❌ 오류: ' + error.message);
            }
        }
    </script>
</body>
</html>
```

---

## ✅ 수정 체크리스트

### 프론트엔드 (젠스파크가 수행)
- [ ] `templates/products.html` 36-41번 라인 수정 (상품명 링크화)
- [ ] `templates/products.html` 68-81번 라인 수정 ([수정] 버튼 추가)
- [ ] `templates/product_detail.html` 새 파일 생성

### 백엔드 (이미 구현됨 - 확인만 필요)
- [ ] `app.py`에 `/products/<int:product_id>` 라우트 추가
- [ ] `app.py`에 `/api/products/<int:product_id>/update` API 추가

---

## 🔍 테스트 방법

1. **로그인** → `/products` 페이지 접속
2. **상품명 클릭** → 상세 페이지(`/products/1`)로 이동 확인
3. **[수정] 버튼 클릭** → 상세 페이지로 이동 확인
4. **상품 정보 수정** → 저장 버튼 클릭 → 목록으로 돌아가기
5. **수정된 내용** → 목록에서 확인

---

## 📌 중요 참고사항

- **링크 경로**: `/products/{{ product.id }}`
- **API 경로**: `/api/products/<int:product_id>/update`
- **템플릿 위치**: `templates/product_detail.html`
- **데이터베이스 테이블**: `sourced_products`
- **인증 필수**: `@login_required` 데코레이터 사용

---

## 🎯 예상 소요 시간
- **프론트엔드 수정**: 3-5분
- **백엔드 API 추가**: 5-10분
- **테스트 및 확인**: 2-3분
- **총 소요 시간**: **10-18분**

---

## 📞 문의사항
수정 중 문제가 발생하면 즉시 보고하세요.
