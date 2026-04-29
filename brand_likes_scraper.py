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
#  브랜드 추가/삭제는 여기서만 하면 됩니다
#  ("브랜드명", "올리브영 브랜드코드")
# ══════════════════════════════════════════════
BRANDS = [
    ("마녀공장", "A001924"),
    ("토리든", "A001491"),
    ("라운드랩", "A001556"),
    ("넘버즈인", "A001687"),
    ("아누아", "A001633"),
    ("롬앤", "A001420"),
    ("클리오", "A000246"),
    ("달바", "A001374"),
    ("조선미녀", "A001684"),
    ("에스트라", "A000606"),
    ("코스알엑스", "A000840"),
    ("닥터지", "A000441"),
    ("메디힐", "A000651"),
    ("VT", "A000939"),
    ("이니스프리", "A000052"),
    ("라네즈", "A000031"),
    ("바닐라코", "A000273"),
    ("스킨푸드", "A000107"),
    ("페리페라", "A001002"),
    ("아이소이", "A000508"),
    ("미샤", "A000077"),
    ("헤라", "A000017"),
    ("비플레인", "A001594"),
    ("센카", "A001289"),
    ("구달", "A001179"),
    ("ONE THING", "A001685"),
    ("아비브", "A001397"),
    ("CNP", "A000667"),
    ("셀퓨전씨", "A000887"),
    ("불랑네이처", "A001869"),
]


def build_brand_url(brand_code):
    return f"https://www.oliveyoung.co.kr/store/display/getBrandShopDetail.do?onlBrndCd={brand_code}"


def extract_like_count(page):
    """페이지에서 좋아요 수 추출"""
    # 여러 패턴 시도
    # 패턴 1: "27,159명이 XX을 좋아합니다" 텍스트에서 숫자 추출
    try:
        content = page.content()
        # "N명이" 패턴
        m = re.search(r'([\d,]+)\s*명이.*좋아합니다', content)
        if m:
            return int(m.group(1).replace(",", ""))
    except:
        pass

    # 패턴 2: 좋아요 관련 셀렉터
    for sel in [
        ".brand_like_num",
        "[class*='like'] [class*='num']",
        "[class*='like'] span",
        ".like_count",
        "[class*='wish'] [class*='num']",
    ]:
        el = page.query_selector(sel)
        if el:
            text = el.inner_text().strip()
            nums = re.findall(r'[\d,]+', text)
            if nums:
                return int(nums[0].replace(",", ""))

    # 패턴 3: 페이지 전체 텍스트에서 "N명이" 패턴
    try:
        body_text = page.inner_text("body")
        m = re.search(r'([\d,]+)\s*명이', body_text)
        if m:
            return int(m.group(1).replace(",", ""))
    except:
        pass

    return None


def scrape_brand_likes():
    """모든 브랜드의 좋아요 수 크롤링"""
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="ko-KR",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        for brand_name, brand_code in BRANDS:
            try:
                url = build_brand_url(brand_code)
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)

                like_count = extract_like_count(page)

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

    # latest도 저장
    latest_path = os.path.join("brand_data", "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 저장: {filepath} ({len(data)}개 브랜드)")
    print(f"📁 최신: {latest_path}")

    # 통계
    valid = [d for d in data if d["likes"] is not None]
    if valid:
        top = sorted(valid, key=lambda x: x["likes"], reverse=True)[:5]
        print("\n🏆 좋아요 TOP 5:")
        for i, b in enumerate(top, 1):
            print(f"   {i}. {b['brand']}: {b['likes']:,}명")


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
