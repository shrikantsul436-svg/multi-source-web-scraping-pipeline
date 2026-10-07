from processing.validation import validate_record

GOOD_BOOK = {
    "source": "Books to Scrape", "source_url": "https://books.toscrape.com/x",
    "name_or_title": "T", "price": 10.0, "rating": 3,
}


def test_valid_book():
    assert validate_record(GOOD_BOOK) == []


def test_bad_records_report_reasons():
    bad = {**GOOD_BOOK, "name_or_title": None, "source_url": "ftp://x",
           "price": -1, "rating": 9, "source": "Nope"}
    problems = validate_record(bad)
    for reason in ("unknown_source", "missing_name", "invalid_url",
                   "invalid_price", "invalid_rating"):
        assert reason in problems


def test_quote_needs_author():
    quote = {"source": "Quotes to Scrape", "source_url": "https://q/",
             "name_or_title": "Hi", "author": None}
    assert validate_record(quote) == ["missing_author"]