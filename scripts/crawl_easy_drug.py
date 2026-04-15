"""식약처 e약은요 (의약품개요정보) API 전체 크롤링 → CSV + JSON 저장."""

import json
import csv
import time
import urllib.request
import urllib.parse
from pathlib import Path

API_KEY = "3iGPxpCbDiTPYBMX63OlN2JFVhR2o62RGYp4l7GhVF3d3240QJeXKrMCxt7WQdrsqruqu%2B2Hz7%2BRORu9k1SuMA%3D%3D"
BASE_URL = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
NUM_OF_ROWS = 100
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

FIELDS = [
    "itemSeq",
    "itemName",
    "entpName",
    "efcyQesitm",
    "useMethodQesitm",
    "atpnWarnQesitm",
    "atpnQesitm",
    "intrcQesitm",
    "seQesitm",
    "depositMethodQesitm",
    "openDe",
    "updateDe",
    "itemImage",
    "bizrno",
]


def fetch_page(page_no: int) -> dict:
    url = (
        f"{BASE_URL}?serviceKey={API_KEY}"
        f"&pageNo={page_no}&numOfRows={NUM_OF_ROWS}&type=json"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def crawl_all() -> list[dict]:
    # First call to get total count
    first = fetch_page(1)
    total = first["body"]["totalCount"]
    total_pages = (total + NUM_OF_ROWS - 1) // NUM_OF_ROWS
    print(f"Total items: {total}, pages: {total_pages}")

    all_items = []
    if first["body"].get("items"):
        all_items.extend(first["body"]["items"])

    for page in range(2, total_pages + 1):
        try:
            data = fetch_page(page)
            items = data["body"].get("items", [])
            all_items.extend(items)
            if page % 10 == 0:
                print(f"  page {page}/{total_pages} — {len(all_items)} items so far")
            time.sleep(0.15)  # Rate limit: ~6 req/sec
        except Exception as e:
            print(f"  ERROR page {page}: {e}, retrying...")
            time.sleep(2)
            try:
                data = fetch_page(page)
                all_items.extend(data["body"].get("items", []))
            except Exception as e2:
                print(f"  RETRY FAILED page {page}: {e2}")

    print(f"Crawl complete: {len(all_items)} items")
    return all_items


def save_json(items: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON: {path} ({path.stat().st_size / 1024:.1f} KB)")


def save_csv(items: list[dict], path: Path):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            # Normalize: replace None with empty string, strip whitespace
            row = {k: (item.get(k) or "").strip() for k in FIELDS}
            writer.writerow(row)
    print(f"Saved CSV: {path} ({path.stat().st_size / 1024:.1f} KB)")


def print_stats(items: list[dict]):
    print("\n=== Field Population Stats ===")
    for field in FIELDS:
        populated = sum(1 for item in items if item.get(field))
        rate = populated / len(items) * 100 if items else 0
        print(f"  {field:<25s} {populated:>5d}/{len(items)} ({rate:.1f}%)")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    items = crawl_all()
    save_json(items, OUTPUT_DIR / "easy_drug_info.json")
    save_csv(items, OUTPUT_DIR / "easy_drug_info.csv")
    print_stats(items)


if __name__ == "__main__":
    main()
