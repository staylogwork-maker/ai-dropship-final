#!/usr/bin/env python3
"""
모든 템플릿 파일의 fetch() 호출에 credentials: 'same-origin' 추가
"""

import re
import os

templates_dir = '/home/user/webapp/templates'
files = ['blue_ocean.html', 'config.html', 'dashboard.html', 'orders.html', 'product_detail.html', 'products.html']

for filename in files:
    filepath = os.path.join(templates_dir, filename)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # fetch 호출에서 credentials이 없는 경우만 추가
    # Pattern: fetch('url', { ... headers: {...}, ... })
    # 이미 credentials가 있는 경우는 건너뛰기
    
    # 패턴 1: headers가 마지막 속성인 경우
    pattern1 = r"(fetch\([^,]+,\s*\{[^}]*headers:\s*\{[^}]+\})([\s\n]*\})"
    
    def add_credentials(match):
        before = match.group(1)
        after = match.group(2)
        
        # 이미 credentials가 있으면 건너뛰기
        if 'credentials' in before:
            return match.group(0)
        
        return before + ",\n                    credentials: 'same-origin'" + after
    
    # 수정 적용
    new_content = re.sub(pattern1, add_credentials, content)
    
    # 변경사항이 있으면 저장
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ {filename}: credentials 추가 완료")
    else:
        print(f"ℹ️  {filename}: 변경 없음 (이미 credentials 있거나 fetch 없음)")

print("\n✅ 모든 파일 처리 완료!")
