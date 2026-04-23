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
    """올리브영 베스트 랭킹을 Playwright로 크롤링 (탭 클릭 방식)"""

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

        # 1) 베스트 페이지 접속
        print("\n🌐 올리브영 베스트 페이지 접속 중...")
        page.goto(
            "https://www.oliveyoung.co.kr/store/main/getBestList.do",
            wait_until="networkidle",
            timeout=60000,
        )
        page.wait_for_timeout(5000)

        # 2) 카테고리 탭 목록 수집
        #    올리브영은 상단에 카테고리 탭이 있고 클릭하면 목록이 바뀜
        cat_tabs = page.query_selector_all(
            "ul.cate_list li a, "              # 카테고리 탭 셀렉터 후보 1
            "div.best_tab_area a, "            # 후보 2
            ".tab_list li a, "                 # 후보 3
            "nav.category a, "                 # 후보 4
            "[class*='cate'] li a, "           # 후보 5
            "[class*='tab'] li a"              # 후보 6
        )

        # 중복 제거
        seen = set()
        unique_tabs = []
        for tab in cat_tabs:
            try:
                text = tab.inner_text().strip()
                if text and text not in seen and len(text) < 20:
                    seen.add(text)
                    unique_tabs.append(tab)
            except:
                pass

        if unique_tabs:
            print(f"📂 카테고리 탭 {len(unique_tabs)}개 발견: {list(seen)}")
        else:
            print("⚠️ 카테고리 탭을 찾지 못함 — 전체 랭킹만 수집합니다")

        # 3) 먼저 현재 페이지(전체)에서 수집
        all_products = extract_products(page, "전체")
        results.extend(all_products)
        print(f"✅ [전체] {len(all_products)}개 상품 수집")

        # 4) 각 카테고리 탭 클릭하여 수집
        for tab in unique_tabs:
            try:
                cat_name = tab.inner_text().strip()
                if cat_name in ("전체", ""):
                    continue

                # 탭 클릭
                tab.click()
                page.wait_for_timeout(3000)
                # 네트워크 안정화 대기
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass

                # 상품 수집
                products = extract_products(page, cat_name)
                results.extend(products)
                print(f"✅ [{cat_name}] {len(products)}개 상품 수집")

            except Exception as e:
                print(f"❌ [{cat_name}] 실패: {e}")

        # 5) 탭 클릭이 안 된 경우, URL 파라미터 방식도 시도
        if len(results) <= len(all_products):
            print("\n🔄 탭 클릭 방식 실패 — URL 파라미터 방식 시도...")
            results = list(all_products)  # 전체는 유지

            # 페이지 소스에서 카테고리 번호 추출 시도
            page_content = page.content()
            import re
            cat_numbers = re.findall(r"dispCatNo['\"]?\s*[:=]\s*['\"]?(\d+)", page_content)
            cat_numbers = list(dict.fromkeys(cat_numbers))  # 중복 제거, 순서 유지

            if cat_numbers:
                print(f"📂 페이지에서 카테고리 번호 {len(cat_numbers)}개 발견")
                for cat_no in cat_numbers[:20]:
                    try:
                        url = f"https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo={cat_no}"
                        page.goto(url, wait_until="networkidle", timeout=30000)
                        page.wait_for_timeout(3000)

                        # 카테고리명 추출
                        active_tab = page.query_selector(
                            "ul.cate_list li.on a, "
                            "[class*='cate'] li.active a, "
                            "[class*='tab'] li.on a, "
                            ".active [class*='cate']"
                        )
                        cat_name = active_tab.inner_text().strip() if active_tab else f"카테고리_{cat_no}"

                        products = extract_products(page, cat_name)
                        if products:
                            results.extend(products)
                            print(f"✅ [{cat_name}] {len(products)}개 상품 수집 (번호: {cat_no})")
                        else:
                            print(f"⚠️ [{cat_name}] 0개 (번호: {cat_no})")

                    except Exception as e:
                        print(f"❌ [카테고리_{cat_no}] 실패: {e}")

        browser.close()

    return results


def extract_products(page, category):
    """현재 페이지에서 상품 목록 추출"""
    products = []

    # 여러 셀렉터 시도
    list_selectors = [
        "ul.cate_prd_list li",
        "ul.best_list li",
        ".prd_list li",
        "[class*='prd_list'] li",
        "[class*='best'] li",
        ".product_list li",
    ]

    items = []
    for sel in list_selectors:
        items = page.query_selector_all(sel)
        if len(items) > 0:
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
                text = el.inner_text().strip()
                if text:
                    product["brand"] = text
                    break

        # 상품명
        for sel in [".tx_name", ".prd_name", "[class*='name']"]:
            el = item.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text:
                    product["name"] = text
                    break

        # 가격
        for sel in [".tx_cur .tx_num", ".prd_price", "[class*='price'] [class*='num']"]:
            el = item.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text:
                    product["price"] = text
                    break

        # 원가
        for sel in [".tx_org .tx_num", "[class*='org'] [class*='num']"]:
            el = item.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text:
                    product["original_price"] = text
                    break

        # 할인율
        for sel in [".tx_sale_per", "[class*='sale']", "[class*='discount']"]:
            el = item.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text:
                    product["discount"] = text
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

        # 이름이 있는 항목만 추가
        if product["name"]:
            products.append(product)

    return products


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

    # 카테고리별 통계
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
