# Multi-Source Web Scraping & Data Consolidation

A Python ETL pipeline that scrapes two public practice sites, cleans and validates the data, removes duplicates, and writes one consolidated CSV plus a JSON summary report.

```
Scrape (both sites) -> Clean -> Validate -> Deduplicate -> Consolidate -> Save files
```

| Source | URL | Content |
| --- | --- | --- |
| Books to Scrape | https://books.toscrape.com/ | ~1,000 books over 50 pages |
| Quotes to Scrape | https://quotes.toscrape.com/ | 100 quotes over 10 pages |

## 1. Python version

Developed and tested on Python **3.12.10** on Windows 11 / PowerShell. Works on 3.10 to 3.12.

## 2. Setup

```bash
python -m venv venv
# Windows:      venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
```

## 3. Dependencies

| Library | Purpose |
| --- | --- |
| `requests` | Downloads page HTML (with a retrying session) |
| `beautifulsoup4` | Searches the HTML with CSS selectors |
| `lxml` | Fast HTML parser used by BeautifulSoup |
| `pytest` | Unit tests |

Everything else (`csv`, `json`, `logging`, `re`, `hashlib`, `argparse`, `pathlib`, `datetime`, `urllib.parse`) is in the standard library. Exact versions are pinned in `requirements.txt`.

**Why Requests + BeautifulSoup?** Both sites are plain server-rendered HTML with no JavaScript needed, so a browser tool such as Selenium or Playwright would only add overhead.

## 4. How to run

```bash
python main.py                              # full run (about 10-20 minutes)
python main.py --no-details                 # fast: skips book detail pages (category/description empty)
python main.py --max-pages 2                # quick test: 2 pages per source
python main.py --delay 1.0                  # slower, more polite
python -m pytest -v                         # unit tests (no internet needed)
```

The full run is slow on purpose: it makes about 1,060 requests (50 book listing pages, 1,000 book detail pages, 10 quote pages) with a 0.5 s pause between each.

## 5. Project structure

```
scraping_assignment/
├── scrapers/
│   ├── base_scraper.py     # session, retries, timeout, delay, pagination loop
│   ├── books_scraper.py    # Books to Scrape selectors and parsing
│   └── quotes_scraper.py   # Quotes to Scrape selectors and parsing
├── processing/
│   ├── cleaning.py         # pure cleaning functions + mapping to the common model
│   ├── validation.py       # returns a list of problems per record
│   └── deduplication.py    # fingerprint + duplicate detection
├── tests/                  # unit tests for cleaning, validation, deduplication
├── output/                 # final_dataset.csv, summary_report.json
├── logs/                   # scraper.log
├── main.py                 # connects all stages, writes outputs
├── check_output.py         # verifies CSV vs JSON counts after a run
├── requirements.txt
├── README.md
└── AI_USAGE.md
```

Rule of thumb: code that touches the internet lives in `scrapers/`; code that only transforms data lives in `processing/`; `main.py` connects the stages.

## 6. Site exploration notes

| Item | Books to Scrape | Quotes to Scrape |
| --- | --- | --- |
| One record | `article.product_pod` | `div.quote` |
| Main text | `h3 > a` (full title is in the `title` attribute; visible text is cut with `...`) | `span.text` (wrapped in curly quotes) |
| Price | `p.price_color` (e.g. `£51.77`) | none |
| Rating | class on `p.star-rating` (e.g. `Three`) | none |
| Availability | `p.availability` | none |
| Author | none | `small.author` |
| Tags | none | `a.tag` (zero or more) |
| Link | `h3 > a[href]` (relative path) | `a[href^="/author/"]` (author page) |
| Category / description | **detail page only**: breadcrumb `ul.breadcrumb li a` (3rd link), `#product_description + p` | none |
| Next page | `li.next > a` | `li.next > a` |

Other observations: book links are relative and must be joined to the page URL; ratings are words, not numbers; prices carry a `£` symbol; the category and description are not on the listing page, so each book's own page must be visited.

## 7. How pagination works

`BaseScraper.scrape_all_pages` starts at the home page and, after parsing each page, looks for `li.next > a`. If found, `urljoin` converts its relative `href` into a full URL and the loop continues; if not found, it stops. No page count is hard-coded, so the scraper keeps working if the site gains or loses pages. If a page fails after retries, an error is logged and pagination for **that source only** stops.

## 8. Data model

One row per record, same columns for every row. Cells that do not apply are left empty (never filled with fake values such as a price of 0).

| Column | Books | Quotes |
| --- | --- | --- |
| `source` | Books to Scrape | Quotes to Scrape |
| `source_url` | Book detail page URL | URL of the page where the quote appeared |
| `name_or_title` | Book title | Quote text (curly quotes removed) |
| `category` | From the detail page (empty if unavailable) | empty |
| `price` | Number, e.g. 51.77 | empty |
| `rating` | Integer 1 to 5 | empty |
| `author` | empty | Author name |
| `tags` | empty | `tag1;tag2` (lowercase, sorted) |
| `description` | From the detail page (empty if unavailable) | empty |
| `availability` | e.g. `In stock` | empty |
| `scraped_at` | UTC ISO timestamp | UTC ISO timestamp |

**Why this schema:** it is the suggested schema from the brief plus `availability` (listed in the brief's description of the book data). Two different shapes fit one table because source-specific fields are simply empty for the other source.

## 9. Cleaning approach (`processing/cleaning.py`)

Small pure functions, tested without internet:

- `clean_text`: collapses all whitespace (spaces, tabs, newlines, `\xa0`); empty becomes `None`.
- `strip_quotes`: removes the curly quotation marks around quote text.
- `clean_price`: `£51.77` becomes `51.77` (float); no number gives `None`.
- `clean_rating`: `star-rating Three` becomes `3`.
- `clean_tags`: lowercase, de-duplicated, sorted, joined with `;`.
- `normalize_url`: makes URLs absolute and returns `None` unless they start with `http://` or `https://`.
- `clean_book` / `clean_quote`: map raw scraper dictionaries into the common data model.

Encoding is set to UTF-8 on every response so `£` does not become `Â£`.

## 10. Validation approach (`processing/validation.py`)

`validate_record` returns a **list of problems** (empty list = valid), so the summary can count rejections per reason.

| Reason | Rule |
| --- | --- |
| `unknown_source` | `source` must be one of the two known names |
| `missing_name` | `name_or_title` must not be empty |
| `invalid_url` | `source_url` must start with `http://` or `https://` |
| `invalid_price` | if present, a number >= 0 |
| `invalid_rating` | if present, an integer from 1 to 5 |
| `missing_price` | books must have a price |
| `missing_author` | quotes must have an author |

Invalid records are logged as warnings, counted, and left out of the final file; the program keeps running.

## 11. Deduplication approach (`processing/deduplication.py`)

A **fingerprint** is built from the identifying fields, lowercased, stripped of punctuation, with spaces collapsed, then hashed with SHA-256. A `set` of seen fingerprints detects repeats; the first occurrence is kept.

- Books: `source + title + price` (price formatted to 2 decimals)
- Quotes: `source + author + first 50 characters of the quote text`

So `"Example Book Title"`, `" Example Book Title "` and `"EXAMPLE BOOK TITLE"` count as one record when their price is also the same.

**Why price is part of the book key (a real finding):** my first full run keyed books on `source + title` only and removed one record, *The Star-Touched Queen*. Checking the live site showed two different listings with that title: £46.02 (`.../the-star-touched-queen_764/`) and £32.30 (`.../the-star-touched-queen_642/`). Title alone wrongly merged them, so price was added to the key. Genuine repeats (same title and same price) are still caught.

**Remove, not flag:** duplicates are dropped and counted in the summary, because the final dataset should contain one row per real item, and the count keeps the removal auditable (the log names each removed duplicate).

**Proof the logic works:** unit tests with deliberately duplicated records (case, spacing, punctuation) and with same-title/different-price records that must be kept. A production version would key on a stable product ID where one exists (here, the number at the end of the book URL).

## 12. Error handling and logging

| Failure | Behavior |
| --- | --- |
| Timeout, connection error, HTTP 429/500/502/503/504 | Session retries up to 3 times with exponential backoff (`backoff_factor=1.0`). A real read timeout during a run was retried successfully (see `logs/scraper_run1.log`) |
| HTTP error that persists (e.g. 404) | Logged as ERROR; pagination for that source stops, other source still runs |
| Book detail page fails | Book is kept, category/description left empty, error logged |
| Missing HTML element | Every `select_one` is checked for `None`; field becomes empty |
| One record fails to parse or clean | Logged as WARNING and skipped; rest of the page continues |
| Invalid values | Rejected by validation with a counted reason |
| Unexpected crash inside one source | Caught in `main.py`; recorded in the summary, other source still runs |

Logging goes to both the console and `logs/scraper.log` (INFO for each page/request, WARNING for each rejected record or duplicate, ERROR for each failed request). The log file is rewritten on each run.

## 13. Output description

| File | Contents |
| --- | --- |
| `output/final_dataset.csv` | One row per unique, valid record from both sources (UTF-8 with BOM so Excel displays text correctly; numeric prices; fixed column order) |
| `output/summary_report.json` | Per-source and total counts: raw collected, cleaned, rejected (with reasons), duplicates removed, final count, start/end time, duration, and a `reconciles` flag |
| `logs/scraper.log` | Time-stamped record of the run |

The numbers reconcile: **raw collected - rejected - duplicates removed = final record count**. A record rejected for several reasons counts once in `rejected` but once per reason in `rejected_by_reason`.

### Results of the submitted run

[FILL from your own summary_report.json after the full run]

| Metric | Books | Quotes | Total |
| --- | --- | --- | --- |
| Raw collected | | | |
| Cleaned | | | |
| Rejected | | | |
| Duplicates removed | | | |
| Final records | | | |

Run duration: [FILL] seconds. CSV row count matches the JSON final count: [FILL yes/no].

## 14. Assumptions

- The two practice sites keep their current HTML structure and `li.next > a` pagination.
- A quote's `source_url` is the page where it appeared (quotes have no individual page).
- A quote is identified by author plus the first 50 characters of its text; a book by its title plus price.
- Prices are in GBP (the site shows `£`); the symbol is dropped and the number stored.
- Quote tags are treated as case-insensitive.

## 15. Known limitations

- Scraping is sequential, so a full run takes about 10 to 20 minutes (a deliberate trade-off for politeness and simplicity).
- If a listing page still fails after retries, that source stops there and returns the records collected so far.
- No checkpoint/resume: an interrupted run starts again from the beginning.
- Book descriptions are stored exactly as returned by the page (for example, the first book's description contains a repeated passage); the text is kept as found rather than "fixed", so no data is invented.
- Book deduplication uses title + price: two listings with the same title and price but different URLs would be merged, and a repeat listed at a different price would not be caught.
- Layout changes on the sites would require updating the selectors in the scraper modules only.
- Category and description are empty when run with `--no-details`.

## 16. What I would change for production

- Run on a schedule (cron or a workflow tool) with alerts on failures.
- Checkpoint progress and support incremental scraping (only new or changed items).
- Concurrency with a rate limiter (async or a thread pool) for speed.
- Store results in a database (PostgreSQL or MongoDB) instead of only CSV.
- Settings in a config file or environment variables; structured logs and monitoring of selector breakage.
- Respect each real site's terms and robots rules and identify the scraper clearly.

## 17. AI usage summary

AI assistance (Claude) was used for planning, initial code, tests and documentation drafts. Everything was reviewed, run and tested before submission. Full details, prompts and corrections are in `AI_USAGE.md`.
