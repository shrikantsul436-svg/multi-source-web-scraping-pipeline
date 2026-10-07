import hashlib
import re


def _norm(text):
    """Lowercase, drop punctuation, collapse spaces."""
    text = re.sub(r"[^\w\s]", "", str(text or "").lower())
    return " ".join(text.split())


def make_fingerprint(rec):
    """Hash of the identifying fields, ignoring case, punctuation, spacing.

    Books:  source + title + price  (two listings can share a title)
    Quotes: source + author + first 50 characters of the text
    """
    if rec["source"] == "Books to Scrape":
        price = rec.get("price")
        price_part = f"{price:.2f}" if price is not None else ""
        parts = [_norm(rec["source"]), _norm(rec["name_or_title"]), price_part]
    else:
        parts = [
            _norm(rec["source"]),
            _norm(rec.get("author")),
            _norm(rec["name_or_title"][:50]),
        ]
    key = "|".join(parts)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def find_duplicates(records):
    """Return (unique, duplicates). The first occurrence is kept."""
    seen, unique, dupes = set(), [], []
    for rec in records:
        fp = make_fingerprint(rec)
        if fp in seen:
            dupes.append(rec)
        else:
            seen.add(fp)
            unique.append(rec)
    return unique, dupes