import csv
import json
from collections import Counter

rows = list(csv.DictReader(open("output/final_dataset.csv", encoding="utf-8-sig")))
summary = json.load(open("output/summary_report.json", encoding="utf-8"))

print("CSV rows:", len(rows))
print("JSON final count:", summary["totals"]["final_record_count"])
print("By source:", Counter(r["source"] for r in rows))
print("Reconciles:", summary["totals"]["reconciles"])

books = [r for r in rows if r["source"] == "Books to Scrape"]
print("Books with price:", sum(1 for r in books if r["price"]))
print("Books with category:", sum(1 for r in books if r["category"]))
print("Ratings seen:", sorted({r["rating"] for r in books}))
