"""식약처 묶음의약품정보 API 전체 크롤링 → JSON + CSV 저장."""

import json
import csv
import time
import urllib.request
from pathlib import Path

API_KEY = "3iGPxpCbDiTPYBMX63OlN2JFVhR2o62RGYp4l7GhVF3d3240QJeXKrMCxt7WQdrsqruqu%2B2Hz7%2BRORu9k1SuMA%3D%3D"
BASE_URL = "https://apis.data.go.kr/1471000/DrbBundleInfoService02/getDrbBundleList02"
NUM_OF_ROWS = 100
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

CSV_FIELDS = [
    "trustIndutyCode",
    "trustItemName",
    "trustMainingr",
    "trustQntList",
    "trustEntpName",
    "trustManuf",
    "trustItemPermitDate",
    "trustHiraMainingrCode",
    "trustHiraPrductCode",
    "trustAtcCode",
    "trustCancelName",
    "cnsgnItemSeq",
    "cnsgnItemName",
    "cnsgnEntpName",
    "cnsgnManuf",
    "cnsgnItemPermitDate",
    "cnsgnHiraPrductCode",
    "cnsgnCancelName",
]


def fetch_page(page_no: int) -> dict:
    url = (
        f"{BASE_URL}?serviceKey={API_KEY}"
        f"&pageNo={page_no}&numOfRows={NUM_OF_ROWS}&type=json"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def crawl_all() -> list[dict]:
    first = fetch_page(1)
    total = first["body"]["totalCount"]
    total_pages = (total + NUM_OF_ROWS - 1) // NUM_OF_ROWS
    print(f"Total items: {total}, pages: {total_pages}")

    all_items = []
    items_raw = first["body"].get("items", [])
    for item in items_raw:
        all_items.append(
            item.get("item", item)
            if isinstance(item, dict) and "item" in item
            else item
        )

    for page in range(2, total_pages + 1):
        try:
            data = fetch_page(page)
            items_raw = data["body"].get("items", [])
            for item in items_raw:
                all_items.append(
                    item.get("item", item)
                    if isinstance(item, dict) and "item" in item
                    else item
                )
            if page % 20 == 0:
                print(f"  page {page}/{total_pages} — {len(all_items)} items")
            time.sleep(0.2)
        except Exception as e:
            print(f"  ERROR page {page}: {e}, retrying after 3s...")
            time.sleep(3)
            try:
                data = fetch_page(page)
                items_raw = data["body"].get("items", [])
                for item in items_raw:
                    all_items.append(
                        item.get("item", item)
                        if isinstance(item, dict) and "item" in item
                        else item
                    )
            except Exception as e2:
                print(f"  RETRY FAILED page {page}: {e2}")

    print(f"Crawl complete: {len(all_items)} items")
    return all_items


def save_json(items: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"Saved JSON: {path} ({size_mb:.1f} MB)")


def save_csv(items: list[dict], path: Path):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            row = {k: (str(item.get(k) or "")).strip() for k in CSV_FIELDS}
            writer.writerow(row)
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"Saved CSV: {path} ({size_mb:.1f} MB)")


def print_stats(items: list[dict]):
    print("\n=== Field Population Stats ===")
    for field in CSV_FIELDS:
        populated = sum(1 for item in items if item.get(field))
        rate = populated / len(items) * 100 if items else 0
        print(f"  {field:<30s} {populated:>6d}/{len(items)} ({rate:.1f}%)")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    items = crawl_all()
    save_json(items, OUTPUT_DIR / "bundle_drug_info.json")
    save_csv(items, OUTPUT_DIR / "bundle_drug_info.csv")
    print_stats(items)


if __name__ == "__main__":
    main()
