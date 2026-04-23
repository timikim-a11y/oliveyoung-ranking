"""
올리브영 랭킹 크롤러
GitHub Actions에서 자동 실행됩니다.
수동 실행: python oliveyoung_scraper.py
"""

import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright


# 올리브영 실제 카테고리 URL (2025년 4월 확인)
# 핵심: dispCatNo=900000100100001 (고정) + fltDispCatNo=카테고리번호
BASE = "https://www.oliveyoung.co.kr/store/main/getBestList.do"
PARAMS = "dispCatNo=900000100100001&pageIdx=1&rowsPerPage=100"

CATEGORIES = [
    ("전체",          ""),
    ("스킨케어",      "10000010001"),
    ("마스크팩",      "10000010009"),
    ("클렌징",        "10000010010"),
    ("선케어",        "10000010011"),
    ("메이크업",      "10000010002"),
    ("네일",          "10000010012"),
    ("뷰티소품",      "10000010006"),
    ("더모코스메틱",   "10000010008"),
    ("맨즈에딧",      "10000010007"),
    ("향수/디퓨저",   "10000010005"),
    ("헤어케어",      "10000010004"),
    ("바디케어",      "10000010003"),
    ("건강식품",      "10000020001"),
    ("푸드",          "10000020002"),
    ("구강용품",      "10000020003"),
    ("헬스/건강용품",  "10000020005"),
    ("위생용품",      "10000020004"),
    ("패션",          "10000030007"),
    ("홈리빙/가전",   "10000030005"),
    ("취미/팬시",     "10000030006"),
]


def build_url(flt_cat_no):
    """카테고리별 URL 생성"""
    url = f"{BASE}?{PARAMS}"
    if flt_cat_no:
        url += f"&fltDispCatNo={flt_cat_no}"
    return url


def extract_products(page, category):
    """현재 페이지에서 상품 목록 추출"""
    products = []

    # 여러 셀렉터 시도
    items = []
    for sel in ["ul.cate_prd_list li", "ul.best_list li", ".prd_list li", "[class*='prd_list'] li"]:
        items = page.query_selector_all(sel)
        if items:
            break

    if not items:
        return products

    for idx, item in enumerate(items, 1):
        product = {
            "rank": idx,
            "category": category,
            "brand": "",
            "name": "",
            "price": "",
            "original_price": "",
            "discount": "",
            "image": "",
            "url": "",
        }

        # 브랜드
        for sel in [".tx_brand", ".brand", "[class*='brand']"]:
            el = item.query_selector(sel)
            if el:
                t = el.inner_text().strip()
                if t:
                    product["brand"] = t
                    break

        # 상품명
        for sel in [".tx_name", ".prd_name", "[class*='name']"]:
            el = item.query_selector(sel)
            if el:
                t = el.inner_text().strip()
                if t:
                    product["name"] = t
                    break

        # 가격
        for sel in [".tx_cur .tx_num", ".prd_price", "[class*='price'] [class*='num']"]:
            el = item.query_selector(sel)
            if el:
                t = el.inner_text().strip()
                if t:
                    product["price"] = t
                    break

        # 원가
        for sel in [".tx_org .tx_num", "[class*='org'] [class*='num']"]:
            el = item.query_selector(sel)
            if el:
                t = el.inner_text().strip()
                if t:
                    product["original_price"] = t
                    break

        # 할인율
        for sel in [".tx_sale_per", "[class*='sale_per']", "[class*='discount']"]:
            el = item.query_selector(sel)
            if el:
                t = el.inner_text().strip()
                if t:
                    product["discount"] = t
                    break

        # 이미지
        img = item.query_selector("img")
        if img:
            product["image"] = img.get_attribute("src") or img.get_attribute("data-src") or ""

        # 링크
        link = item.query_selector("a")
        if link:
            href = link.get_attribute("href") or ""
            if href and not href.startswith("http"):
                href = "https://www.oliveyoung.co.kr" + href
            product["url"] = href

        if product["name"]:
            products.append(product)

    return products


def scrape_oliveyoung():
    """올리브영 베스트 랭킹을 Playwright로 크롤링"""

    results = []

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

        for cat_name, flt_cat_no in CATEGORIES:
            try:
                url = build_url(flt_cat_no)
                page.goto(url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(4000)

                products = extract_products(page, cat_name)
                results.extend(products)
                print(f"✅ [{cat_name}] {len(products)}개 상품 수집")

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
