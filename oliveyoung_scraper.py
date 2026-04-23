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

    # 크롤링할 카테고리 (카테고리명, URL)
    categories = [
        ("전체", "https://www.oliveyoung.co.kr/store/main/getBestList.do"),
        ("스킨케어", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010001"),
        ("메이크업", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010002"),
        ("클렌징", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010011"),
        ("선케어", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010012"),
        ("바디케어", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010010"),
        ("헤어케어", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010008"),
        ("향수/디퓨저", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010003"),
        ("건강식품", "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=10000010009"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
        )
        page = context.new_page()

        for cat_name, url in categories:
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)

                # 상품 목록 추출
                items = page.query_selector_all("ul.cate_prd_list li")

                for idx, item in enumerate(items, 1):
                    product = {
                        "rank": idx,
                        "category": cat_name,
                        "brand": "",
                        "name": "",
                        "price": "",
                        "original_price": "",
                        "discount": "",
                        "image": "",
                        "url": "",
                    }

                    brand = item.query_selector(".tx_brand")
                    if brand:
                        product["brand"] = brand.inner_text().strip()

                    name = item.query_selector(".tx_name")
                    if name:
                        product["name"] = name.inner_text().strip()

                    price = item.query_selector(".tx_cur .tx_num")
                    if price:
                        product["price"] = price.inner_text().strip()

                    org_price = item.query_selector(".tx_org .tx_num")
                    if org_price:
                        product["original_price"] = org_price.inner_text().strip()

                    discount = item.query_selector(".tx_sale_per")
                    if discount:
                        product["discount"] = discount.inner_text().strip()

                    img = item.query_selector("img")
                    if img:
                        product["image"] = img.get_attribute("src") or ""

                    link = item.query_selector("a")
                    if link:
                        href = link.get_attribute("href") or ""
                        if href and not href.startswith("http"):
                            href = "https://www.oliveyoung.co.kr" + href
                        product["url"] = href

                    results.append(product)

                print(f"✅ [{cat_name}] {len(items)}개 상품 수집")

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

    # latest.json도 항상 덮어쓰기 (대시보드 연동용)
    latest_path = os.path.join("data", "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 저장: {filepath} ({len(data)}개 상품)")
    print(f"📁 최신: {latest_path}")


if __name__ == "__main__":
    print("=" * 50)
    print("🫒 올리브영 랭킹 크롤러")
    print("=" * 50)

    data = scrape_oliveyoung()

    if data:
        save_results(data)
        print(f"\n✅ 완료! 총 {len(data)}개 상품 수집")
    else:
        print("\n⚠️ 데이터를 가져오지 못했습니다")
