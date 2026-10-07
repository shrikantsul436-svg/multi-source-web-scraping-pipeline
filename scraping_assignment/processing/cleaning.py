import re
from datetime import datetime, timezone
from urllib.parse import urljoin

COLUMNS = [
    "source", "source_url", "name_or_title", "category", "price",
    "rating", "author", "tags", "description", "availability", "scraped_at",
]

RATING_MAP = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def clean_text(value):
    """Collapse all whitespace (incl. non-breaking spaces). Empty -> None."""
    if value is None:
        return None
    text = " ".join(str(value).replace("\xa0", " ").split())
    return text or None


def strip_quotes(value):
    """Remove ONE wrapping pair of quotation marks, nothing more."""
    text = clean_text(value)
    if text is None:
        return None
    if text[0] in "\u201c\"":
        text = text[1:]
    if text and text[-1] in "\u201d\"":
        text = text[:-1]
    return clean_text(text)


def clean_price(raw):
    """'£51.77' -> 51.77. Returns None if no number is found."""
    if not raw:
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(raw).replace(",", ""))
    return float(match.group()) if match else None


def clean_rating(raw):
    """'star-rating Three' -> 3. Returns None if no rating word is found."""
    for word in str(raw or "").lower().split():
        if word in RATING_MAP:
            return RATING_MAP[word]
    return None


def clean_tags(tags):
    """['Love', 'books'] -> 'books;love' (lowercase, sorted, ';'-joined)."""
    if not tags:
        return None
    cleaned = {clean_text(t).lower() for t in tags if clean_text(t)}
    return ";".join(sorted(cleaned)) or None


def normalize_url(url, base=None):
    """Make a URL absolute. Returns None if it still isn't http(s)."""
    text = clean_text(url)
    if text is None:
        return None
    if base:
        text = urljoin(base, text)
    return text if text.startswith(("http://", "https://")) else None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_book(raw):
    """Turn a raw book dict from the scraper into the common data model."""
    return {
        "source": "Books to Scrape",
        "source_url": normalize_url(raw.get("url")),
        "name_or_title": clean_text(raw.get("title")),
        "category": clean_text(raw.get("category_raw")),
        "price": clean_price(raw.get("price_raw")),
        "rating": clean_rating(raw.get("rating_raw")),
        "author": None,
        "tags": None,
        "description": clean_text(raw.get("description_raw")),
        "availability": clean_text(raw.get("availability_raw")),
        "scraped_at": _now(),
    }


def clean_quote(raw):
    """Turn a raw quote dict from the scraper into the common data model."""
    return {
        "source": "Quotes to Scrape",
        "source_url": normalize_url(raw.get("page_url")),
        "name_or_title": strip_quotes(raw.get("text")),
        "category": None,
        "price": None,
        "rating": None,
        "author": clean_text(raw.get("author")),
        "tags": clean_tags(raw.get("tags_raw")),
        "description": None,
        "availability": None,
        "scraped_at": _now(),
    }
