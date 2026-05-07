"""
올리브영 랭킹 크롤러
GitHub Actions에서 자동 실행됩니다.
수동 실행: python oliveyoung_scraper.py
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

KST = timezone(timedelta(hours=9))

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
    url = f"{BASE}?{PARAMS}"
    if flt_cat_no:
        url += f"&fltDispCatNo={flt_cat_no}"
    return url


def extract_product_id(url):
    """URL에서 상품 고유 ID 추출 (goodsNo 파라미터)"""
    if not url:
        return ""
    m = re.search(r'goodsNo=([A-Za-z0-9]+)', url)
    if m:
        return m.group(1)
    # URL 경로에서 추출 시도
    m = re.search(r'/([A-Za-z0-9]{10,})', url)
    if m:
        return m.group(1)
    return ""


def detect_status(item):
    """
    상품의 판매 상태를 감지
    - 할인: 원가와 판매가가 다르거나, 할인율 표시가 있으면
    - 품절: 품절 관련 클래스나 텍스트가 있으면
    - 정상판매: 위 두 경우가 아니면
    """
    # 품절 체크
    for sel in [".soldout", "[class*='soldout']", "[class*='sold_out']", ".restocked", "[class*='품절']"]:
        el = item.query_selector(sel)
        if el:
            return "품절"

    # 품절 텍스트 체크
    try:
        text = item.inner_text()
        if "품절" in text and "품절해제" not in text:
            return "품절"
    except:
        pass

    # 할인 체크: 할인율이 있거나, 원가 표시가 있으면
    for sel in [".tx_sale_per", "[class*='sale_per']", "[class*='discount']"]:
        el = item.query_selector(sel)
        if el:
            t = el.inner_text().strip()
            if t and ("%" in t or "할인" in t):
                return "할인"

    # 원가가 있으면 할인
    for sel in [".tx_org", "[class*='org_price']", "del", "s"]:
        el = item.query_selector(sel)
        if el:
            t = el.inner_text().strip()
            if t:
                return "할인"

    return "정상판매"


def try_text(item, selectors):
    for sel in selectors:
        el = item.query_selector(sel)
        if el:
            t = el.inner_text().strip()
            if t:
                return t
    return ""


def extract_products(page, category):
    products = []
    items = []
    for sel in ["ul.cate_prd_list li", "ul.best_list li", ".prd_list li", "[class*='prd_list'] li"]:
        items = page.query_selector_all(sel)
        if items:
            break
    if not items:
        return products

    for idx, item in enumerate(items, 1):
        # 링크 & 상품 ID
        url = ""
        link = item.query_selector("a")
        if link:
            href = link.get_attribute("href") or ""
            if href and not href.startswith("http"):
                href = "https://www.oliveyoung.co.kr" + href
            url = href

        product_id = extract_product_id(url)

        # 상태 감지
        status = detect_status(item)

        product = {
            "rank": idx,
            "category": category,
            "id": product_id,
            "brand": try_text(item, [".tx_brand", ".brand", "[class*='brand']"]),
            "name": try_text(item, [".tx_name", ".prd_name", "[class*='name']"]),
            "price": try_text(item, [".tx_cur .tx_num", ".prd_price", "[class*='price'] [class*='num']"]),
            "original_price": try_text(item, [".tx_org .tx_num", "[class*='org'] [class*='num']"]),
            "discount": try_text(item, [".tx_sale_per", "[class*='sale_per']", "[class*='discount']"]),
            "status": status,
            "image": "",
            "url": url,
        }

        img = item.query_selector("img")
        if img:
            product["image"] = img.get_attribute("src") or img.get_attribute("data-src") or ""

        if product["name"]:
            products.append(product)

    return products


def scrape_oliveyoung():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="ko-KR",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        for cat_name, flt_cat_no in CATEGORIES:
            try:
                page.goto(build_url(flt_cat_no), wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(4000)
                products = extract_products(page, cat_name)
                results.extend(products)
                # 상태별 카운트
                sc = {}
                for pr in products:
                    sc[pr["status"]] = sc.get(pr["status"], 0) + 1
                status_str = ", ".join(f"{k}:{v}" for k, v in sc.items())
                print(f"✅ [{cat_name}] {len(products)}개 ({status_str})")
            except Exception as e:
                print(f"❌ [{cat_name}] 실패: {e}")
        browser.close()
    return results


def save_results(data):
    os.makedirs("data", exist_ok=True)
    now = datetime.now(KST)
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

    # ★ 파일 목록 index 생성 (GitHub API 호출 대체)
    all_files = sorted([
        f for f in os.listdir("data")
        if f.endswith(".json") and f not in ("latest.json", "_index.json", ".gitkeep")
    ])
    index_path = os.path.join("data", "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(all_files, f)
    print(f"\n📁 저장: {filepath} ({len(data)}개 상품)")
    print(f"📁 최신: {latest_path}")
    print(f"📁 인덱스: {index_path} ({len(all_files)}개 파일)")

    cat_stats = {}
    for pr in data:
        cat_stats[pr.get("category", "기타")] = cat_stats.get(pr.get("category", "기타"), 0) + 1
    print("\n📊 카테고리별 수집 현황:")
    for cat, count in sorted(cat_stats.items()):
        print(f"   {cat}: {count}개")


if __name__ == "__main__":
    print("=" * 50)
    print("🫒 올리브영 랭킹 크롤러")
    print(f"⏰ 실행 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    print("=" * 50)
    data = scrape_oliveyoung()
    if data:
        save_results(data)
        print(f"\n✅ 완료! 총 {len(data)}개 상품 수집")
    else:
        print("\n⚠️ 데이터를 가져오지 못했습니다")
