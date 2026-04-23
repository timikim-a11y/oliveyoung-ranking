"""
올리브영 랭킹 크롤러
GitHub Actions에서 자동 실행됩니다.
수동 실행: python oliveyoung_scraper.py
"""

import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright


def scrape_oliveyoung():
    """올리브영 베스트 랭킹을 Playwright로 크롤링"""

    results = []

    # 올리브영 베스트 카테고리 (카테고리명, URL)
    categories = [
        ("전체",        "https://www.oliveyoung.co.kr/store/main/getBestList.do"),
        ("스킨케어",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010001"),
        ("메이크업",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010002"),
        ("바디케어",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010010"),
        ("헤어케어",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010008"),
        ("향수/디퓨저", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010003"),
        ("메이크업 툴", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010004"),
        ("맨즈케어",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010006"),
        ("더모코스메틱", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010013"),
        ("마스크팩",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010014"),
        ("클렌징",      "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010011"),
        ("선케어",      "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010012"),
        ("네일",        "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010005"),
        ("건강식품",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010009"),
        ("푸드",        "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010015"),
        ("구강용품",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010016"),
        ("위생용품",    "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010017"),
        ("헬스/건강용품","https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010018"),
        ("홈리빙/가전", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010019"),
        ("취미/팬시",   "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010020"),
        ("패션",        "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010021"),
    ]

    # 여러 셀렉터를 시도 (올리브영 사이트 구조 변경 대비)
    LIST_SELECTORS = [
        "ul.cate_prd_list li",
        ".prd_info",
        "ul.best_list li",
        ".prd_list li",
        "[class*='prd'] li",
    ]
    BRAND_SELECTORS = [".tx_brand", ".brand", "[class*='brand']"]
    NAME_SELECTORS  = [".tx_name", ".prd_name", "[class*='name']"]
    PRICE_SELECTORS = [".tx_cur .tx_num", ".price .tx_num", "[class*='price'] [class*='num']"]
    ORG_SELECTORS   = [".tx_org .tx_num", "[class*='org'] [class*='num']"]
    DISC_SELECTORS  = [".tx_sale_per", "[class*='sale']", "[class*='discount']"]

    def try_selectors(element, selectors):
        for sel in selectors:
            try:
                el = element.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    if text:
                        return text
            except:
                pass
        return ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        for cat_name, url in categories:
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(4000)

                # 여러 셀렉터로 상품 목록 탐색
                items = []
                used_selector = ""
                for sel in LIST_SELECTORS:
                    items = page.query_selector_all(sel)
                    if len(items) > 0:
                        used_selector = sel
                        break

                if not items:
                    print(f"⚠️ [{cat_name}] 상품 목록을 찾지 못함")
                    continue

                cat_count = 0
                for idx, item in enumerate(items, 1):
                    product = {
                        "rank": idx,
                        "category": cat_name,
                        "brand": try_selectors(item, BRAND_SELECTORS),
                        "name": try_selectors(item, NAME_SELECTORS),
                        "price": try_selectors(item, PRICE_SELECTORS),
                        "original_price": try_selectors(item, ORG_SELECTORS),
                        "discount": try_selectors(item, DISC_SELECTORS),
                        "image": "",
                        "url": "",
                    }

                    img = item.query_selector("img")
                    if img:
                        product["image"] = img.get_attribute("src") or img.get_attribute("data-src") or ""

                    link = item.query_selector("a")
                    if link:
                        href = link.get_attribute("href") or ""
                        if href and not href.startswith("http"):
                            href = "https://www.oliveyoung.co.kr" + href
                        product["url"] = href

                    if product["name"]:
                        results.append(product)
                        cat_count += 1

                print(f"✅ [{cat_name}] {cat_count}개 상품 수집 (셀렉터: {used_selector})")

            except Exception as e:
                print(f"❌ [{cat_name}] 실패: {e}")

        browser.close()

    return results


def save_results(data):
    """data/ 폴더에 날짜별로 저장"""
    os.makedirs("data", exist_ok=True)
    now = datetime.now()
    filename = now.strftime("%Y-%m-%d_%H%M") + ".json"
    filepath = os.path.join("data", filename)

    output = {
        "updated_at": now.isoformat(),
        "source": "oliveyoung.co.kr",
        "total_count": len(data),
        "products": data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    latest_path = os.path.join("data", "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 저장: {filepath} ({len(data)}개 상품)")
    print(f"📁 최신: {latest_path}")

    cat_stats = {}
    for p in data:
        cat = p.get("category", "기타")
        cat_stats[cat] = cat_stats.get(cat, 0) + 1
    print("\n📊 카테고리별 수집 현황:")
    for cat, count in sorted(cat_stats.items()):
        print(f"   {cat}: {count}개")


if __name__ == "__main__":
    print("=" * 50)
    print("🫒 올리브영 랭킹 크롤러")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    data = scrape_oliveyoung()

    if data:
        save_results(data)
        print(f"\n✅ 완료! 총 {len(data)}개 상품 수집")
    else:
        print("\n⚠️ 데이터를 가져오지 못했습니다")
