import argparse
import csv
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from processing.cleaning import COLUMNS, clean_book, clean_quote
from processing.deduplication import find_duplicates
from processing.validation import validate_record
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

logger = logging.getLogger("main")


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    file_handler = logging.FileHandler(LOG_DIR / "scraper.log", mode="w", encoding="utf-8")
    console_handler = logging.StreamHandler()
    for handler in (file_handler, console_handler):
        handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [file_handler, console_handler]


def run_source(name, scrape_fn, clean_fn):
    """Scrape -> clean -> validate -> deduplicate one source.

    Never raises: a failure in this source is logged and recorded,
    so the other source can still run.
    """
    stats = {
        "raw_collected": 0,
        "cleaned": 0,
        "rejected": 0,
        "rejected_by_reason": {},
        "duplicates_removed": 0,
        "final": 0,
        "error": None,
    }
    reasons = Counter()
    final_records = []

    try:
        logger.info("=== Starting source: %s ===", name)
        raw_records = scrape_fn()
        stats["raw_collected"] = len(raw_records)

        valid = []
        for raw in raw_records:
            try:
                rec = clean_fn(raw)
            except Exception as exc:
                logger.warning("Cleaning failed (%s): %s", exc, raw)
                stats["rejected"] += 1
                reasons["cleaning_error"] += 1
                continue
            stats["cleaned"] += 1

            problems = validate_record(rec)
            if problems:
                logger.warning("Rejected %r: %s", rec.get("name_or_title"), problems)
                stats["rejected"] += 1       # a record counts once here...
                reasons.update(problems)     # ...but every reason is tallied
            else:
                valid.append(rec)

        final_records, dupes = find_duplicates(valid)
        stats["duplicates_removed"] = len(dupes)
        for d in dupes:
            logger.warning("Duplicate removed: %r", d["name_or_title"])
        stats["final"] = len(final_records)
    except Exception as exc:  # unexpected failure: keep the program alive
        logger.exception("Source %s failed: %s", name, exc)
        stats["error"] = str(exc)

    stats["rejected_by_reason"] = dict(reasons)
    logger.info("=== Finished %s: %s ===", name, stats)
    return final_records, stats


def write_csv(records, path):
    path.parent.mkdir(exist_ok=True)
    # utf-8-sig lets Excel display symbols correctly; other tools read it fine
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def write_json(data, path):
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def parse_args():
    p = argparse.ArgumentParser(description="Multi-source scraping pipeline")
    p.add_argument("--no-details", action="store_true",
                   help="skip book detail pages (fast, but category/description empty)")
    p.add_argument("--max-pages", type=int, default=None,
                   help="limit pages per source (for quick testing)")
    p.add_argument("--delay", type=float, default=0.5,
                   help="seconds to pause between requests (default 0.5)")
    return p.parse_args()


def main():
    args = parse_args()
    setup_logging()

    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    logger.info("Run started with settings: %s", vars(args))

    books = BooksScraper(fetch_details=not args.no_details, delay=args.delay)
    quotes = QuotesScraper(delay=args.delay)

    book_records, book_stats = run_source(
        "Books to Scrape", lambda: books.scrape(args.max_pages), clean_book)
    quote_records, quote_stats = run_source(
        "Quotes to Scrape", lambda: quotes.scrape(args.max_pages), clean_quote)

    final_records = book_records + quote_records
    write_csv(final_records, OUTPUT_DIR / "final_dataset.csv")

    per_source = {"Books to Scrape": book_stats, "Quotes to Scrape": quote_stats}
    total_reasons = Counter()
    for s in per_source.values():
        total_reasons.update(s["rejected_by_reason"])

    totals = {
        "raw_collected": sum(s["raw_collected"] for s in per_source.values()),
        "cleaned": sum(s["cleaned"] for s in per_source.values()),
        "rejected": sum(s["rejected"] for s in per_source.values()),
        "rejected_by_reason": dict(total_reasons),
        "duplicates_removed": sum(s["duplicates_removed"] for s in per_source.values()),
        "final_record_count": len(final_records),
    }
    totals["reconciles"] = (
        totals["raw_collected"] - totals["rejected"] - totals["duplicates_removed"]
        == totals["final_record_count"]
    )

    ended = datetime.now(timezone.utc)
    summary = {
        "run": {
            "started_at": started.isoformat(timespec="seconds"),
            "ended_at": ended.isoformat(timespec="seconds"),
            "duration_seconds": round(time.perf_counter() - t0, 1),
            "settings": vars(args),
        },
        "per_source": per_source,
        "totals": totals,
        "note": "A record rejected for several reasons counts once in 'rejected' "
                "but once per reason in 'rejected_by_reason'.",
    }
    write_json(summary, OUTPUT_DIR / "summary_report.json")

    logger.info("Done. %d rows written. Reconciles: %s",
                totals["final_record_count"], totals["reconciles"])


if __name__ == "__main__":
    main()