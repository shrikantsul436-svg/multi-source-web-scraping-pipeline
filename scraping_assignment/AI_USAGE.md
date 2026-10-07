# AI Usage

## 1. AI tools used

| Tool | Used for |
| --- | --- |
| Claude (claude.ai chat) | Project plan, first version of all code, unit tests, `main.py`, troubleshooting, and drafts of README.md and this file |

## 2. What AI was used for, by file

| File | AI-assisted? | Notes |
| --- | --- | --- |
| `scrapers/base_scraper.py` | Yes | Session with retries/backoff, fetch helper, pagination loop. Tested live (status 200). |
| `scrapers/books_scraper.py` | Yes | Listing and detail-page selectors. Verified on the live site (first book returned correct title, price, rating, category, description). |
| `scrapers/quotes_scraper.py` | Yes | Selectors and pagination. Verified live (text, author, tags). |
| `processing/cleaning.py` | Yes | Cleaning functions and mapping to the common data model. `strip_quotes` was corrected after review (see section 5). |
| `processing/validation.py` | Yes | Validation returning a list of problem reasons. |
| `processing/deduplication.py` | Yes | Fingerprint approach. The book key was changed after I found a problem in real data (see section 5). |
| `tests/` | Yes | 15 unit tests, all passing. |
| `main.py`, `check_output.py` | Yes | Orchestration, logging, stats, CSV/JSON output, output verification. |
| README.md, AI_USAGE.md | Drafted with AI | I supplied my real run results and findings, and edited the text. |

## 3. Representative prompts

1. "This is the assignment I received from a company ... analyse the whole requirement and give me a step-by-step guide from scratch."
2. (Pasted my PowerShell error from the setup commands and asked what to do.)
3. (Pasted my scraper test output and my pytest results.)
4. "Give me everything about the project that is defined in the PDFs."
5. (Pasted my log search output and the Star-Touched Queen check, and asked whether the result was correct.)

## 4. Important changes I made after reviewing AI output

- Changed the book duplicate key from `source + title` to `source + title + price` after verifying on the live site that two different listings share a title.
- Replaced `strip_quotes` with a version that removes only one wrapping pair of quotation marks.
- Rebuilt `tests/test_deduplication.py` as a complete file with the import, the original tests and the two new price-based tests.
- Removed `scratch_test.py` because pytest tried to run it as a test and it scraped the live site on import.
- Kept book detail-page scraping (about 1,000 extra requests) because the brief lists category as a required field.

## 5. Incorrect or incomplete AI suggestions I found

1. **Wrong shell commands for my OS.** The first setup commands used `&&`, `source venv/bin/activate` and `touch` (Linux/macOS). They failed in Windows PowerShell, so I used Windows equivalents.
2. **Title-only book duplicate key.** The suggested key merged two different books named *The Star-Touched Queen* (£46.02 and £32.30, different URLs). My first full run produced 1099 rows instead of 1100. I found it through the log, confirmed it against the live site, and added price to the key.
3. **`strip_quotes` removed too much.** It stripped every quote or apostrophe character at both ends of a quote, which could damage text such as a quote ending in an apostrophe. Fixed to remove one wrapping pair only, with a test.
4. **Unverified claims in the first README draft.** It stated exact retry delays ("1s, 2s, 4s") and that repeated description text was a site quirk, without checking either. I reworded the retry description and verified the description text myself.
5. **Ambiguous test instruction.** "Add these tests to the file" led to the test file losing its import line, causing `NameError` failures. Fixed by replacing the file with the complete version.

## 6. How the final solution was tested and verified

- Unit tests: `python -m pytest -v` for cleaning, validation and deduplication, 15 passed. Duplicate logic is proven with deliberately duplicated records.
- Live selector check: scraped one page of books with detail pages and two pages of quotes before the full run.
- Failure tests:
  - A DNS failure (my machine briefly could not resolve the site): 3 retries, then ERROR, then the source stopped without crashing.
  - A request to a non-existent URL: HTTP 404 logged as ERROR, no retry, returned an empty list.
  - A read timeout during the first full run was retried automatically and the run completed (`logs/scraper_run1.log`).
- First full run: 1000 books, 100 quotes, 1 duplicate removed, 1099 rows, reconciles true (`logs/summary_run1.json`). This led to the dedup key change.
- Final full run after the fix: [FILL: paste raw / rejected / duplicates / final from `output/summary_report.json`].
- `check_output.py` confirmed CSV row count equals the JSON final count, both sources present, ratings only 1 to 5, and categories filled: [FILL: result].
- Reconciliation: raw collected - rejected - duplicates removed = final count, `reconciles: true`.

## 7. My understanding (interview notes)

- **Why Requests + BeautifulSoup:** both sites are static server-rendered HTML.
- **Pagination:** follow `li.next > a`, `urljoin` makes the URL absolute, stop when it is absent.
- **Failed requests:** retries with backoff for temporary errors (429/5xx and connection problems); a persistent failure such as 404 is not retried and stops only that source; a failed detail page leaves category and description empty.
- **Missing fields:** every selector result is checked for `None`; fields become empty rather than invented.
- **Duplicates:** normalized fingerprint (lowercase, no punctuation, collapsed spaces, SHA-256) over source + title + price for books and source + author + first 50 characters for quotes; the first occurrence is kept.
- **Schema:** the brief's suggested columns plus `availability`; non-applicable fields stay empty.
- **For production:** scheduling, checkpoint/resume, concurrency with rate limiting, a database, config file, monitoring; dedup on a stable product ID.