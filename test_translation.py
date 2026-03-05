#!/usr/bin/env python3
"""
AI Translation Test
"""

from aliexpress_matcher import translate_keyword_to_english

# Test cases
test_keywords = [
    "차량용 USB 공기청정기",
    "반려동물 자동 급식기",
    "무선 블루투스 이어폰",
    "고압 세척기",
    "측정 장비",
    "반도체 IC칩"
]

print("\n" + "="*60)
print("AI Translation Test - Korean → English")
print("="*60 + "\n")

for korean in test_keywords:
    english = translate_keyword_to_english(korean)
    print(f"✅ {korean:25s} → {english}")

print("\n" + "="*60)
print("Test completed!")
print("="*60)
