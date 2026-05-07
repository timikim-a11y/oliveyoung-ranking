"""
올리브영 브랜드 좋아요 수 크롤러
매일 오전 9시(KST)에 자동 실행됩니다.
수동 실행: python brand_likes_scraper.py
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

KST = timezone(timedelta(hours=9))

# ══════════════════════════════════════════════
#  트래킹할 브랜드 목록
#  ("브랜드명", "올리브영 브랜드코드")
# ══════════════════════════════════════════════
BRANDS = [
    ("마녀공장", "A001924"),
    ("비플레인", "A002833"),
    ("메이크프렘", "A002310"),
    ("넘버즈인", "A003477"),
    ("메디힐", "A000688"),
    ("아누아", "A003377"),
    ("토리든", "A002820"),
    ("닥터지", "A000627"),
    ("메디큐브", "A001925"),
    ("브링그린", "A002253"),
]


def build_brand_url(brand_code):
    return f"https://www.oliveyoung.co.kr/store/display/getBrandShopDetail.do?onlBrndCd={brand_code}"


def scrape_brand_likes():
    """모든 브랜드의 좋아요 수 크롤링 — 매 브랜드마다 새 페이지"""
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for brand_name, brand_code in BRANDS:
            like_count = None
            try:
                # ★ 핵심: 매 브랜드마다 새 컨텍스트+페이지 열기
                # 이전 페이지 DOM이 남아있는 문제 방지
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    locale="ko-KR",
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()

                url = build_brand_url(brand_code)
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(4000)

                # 방법 1: "N명이 XX을(를) 좋아합니다" 텍스트에서 추출
                body_text = page.inner_text("body")

                # "27,158명이 마녀공장을 좋아합니다" 패턴
                pattern = r'([\d,]+)\s*명이\s*.+?좋아합니다'
                matches = re.findall(pattern, body_text)
                if matches:
                    # 가장 첫번째 매치 사용
                    like_count = int(matches[0].replace(",", ""))

                # 방법 2: 못 찾으면 "N명이" 패턴만으로
                if like_count is None:
                    m = re.search(r'([\d,]+)\s*명이', body_text)
                    if m:
                        num = int(m.group(1).replace(",", ""))
                        # 너무 작은 숫자(1~10)는 다른 텍스트일 가능성
                        if num > 10:
                            like_count = num

                # 방법 3: HTML 소스에서 직접 추출
                if like_count is None:
                    html = page.content()
                    m = re.search(r'([\d,]+)\s*명이.*?좋아합니다', html)
                    if m:
                        like_count = int(m.group(1).replace(",", ""))

                # 페이지 닫기 (메모리 정리)
                page.close()
                context.close()

                result = {
                    "brand": brand_name,
                    "code": brand_code,
                    "likes": like_count,
                    "url": url,
                }
                results.append(result)

                if like_count is not None:
                    print(f"✅ [{brand_name}] 좋아요: {like_count:,}명")
                else:
                    print(f"⚠️ [{brand_name}] 좋아요 수를 찾지 못함")

            except Exception as e:
                print(f"❌ [{brand_name}] 실패: {e}")
                results.append({
                    "brand": brand_name,
                    "code": brand_code,
                    "likes": None,
                    "url": build_brand_url(brand_code),
                })
                try:
                    page.close()
                    context.close()
                except:
                    pass

        browser.close()

    return results


def save_results(data):
    """brand_data/ 폴더에 날짜별로 저장"""
    os.makedirs("brand_data", exist_ok=True)
    now = datetime.now(KST)
    filename = now.strftime("%Y-%m-%d") + ".json"
    filepath = os.path.join("brand_data", filename)

    output = {
        "updated_at": now.isoformat(),
        "source": "oliveyoung.co.kr",
        "total_brands": len(data),
        "brands": data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    latest_path = os.path.join("brand_data", "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 저장: {filepath} ({len(data)}개 브랜드)")
    print(f"📁 최신: {latest_path}")

    # ★ 파일 목록 index 생성 (GitHub API 호출 대체)
    all_files = sorted([
        f for f in os.listdir("brand_data")
        if f.endswith(".json") and f not in ("latest.json", "_index.json", ".gitkeep")
    ])
    index_path = os.path.join("brand_data", "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(all_files, f)
    print(f"📁 인덱스: {index_path} ({len(all_files)}개 파일)")

    valid = [d for d in data if d["likes"] is not None]
    failed = [d for d in data if d["likes"] is None]

    if valid:
        top = sorted(valid, key=lambda x: x["likes"], reverse=True)[:5]
        print("\n🏆 좋아요 TOP 5:")
        for i, b in enumerate(top, 1):
            print(f"   {i}. {b['brand']}: {b['likes']:,}명")

    if failed:
        print(f"\n⚠️ 수집 실패 브랜드 ({len(failed)}개):")
        for b in failed:
            print(f"   - {b['brand']} ({b['code']})")


if __name__ == "__main__":
    print("=" * 50)
    print("🫒 올리브영 브랜드 좋아요 크롤러")
    print(f"⏰ 실행 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    print("=" * 50)

    data = scrape_brand_likes()

    if data:
        save_results(data)
        print(f"\n✅ 완료! {len(data)}개 브랜드 수집")
    else:
        print("\n⚠️ 데이터를 가져오지 못했습니다")
