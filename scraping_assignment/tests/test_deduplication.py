from processing.deduplication import find_duplicates


def test_book_duplicates_ignore_case_and_spaces():
    base = {"source": "Books to Scrape", "author": None, "price": 10.0}
    records = [
        {**base, "name_or_title": "Example Book Title"},
        {**base, "name_or_title": "  Example Book Title "},
        {**base, "name_or_title": "EXAMPLE BOOK TITLE"},
    ]
    unique, dupes = find_duplicates(records)
    assert len(unique) == 1 and len(dupes) == 2


def test_quote_duplicates_need_same_author():
    q = {"source": "Quotes to Scrape", "name_or_title": "Same text here"}
    records = [{**q, "author": "A"}, {**q, "author": "a "}, {**q, "author": "B"}]
    unique, dupes = find_duplicates(records)
    assert len(unique) == 2 and len(dupes) == 1


def test_same_title_same_price_is_duplicate():
    base = {"source": "Books to Scrape", "author": None, "price": 46.02}
    records = [
        {**base, "name_or_title": "The Star-Touched Queen"},
        {**base, "name_or_title": "  the star-touched   queen "},
    ]
    unique, dupes = find_duplicates(records)
    assert len(unique) == 1 and len(dupes) == 1


def test_same_title_different_price_is_kept():
    base = {"source": "Books to Scrape", "author": None}
    records = [
        {**base, "name_or_title": "The Star-Touched Queen", "price": 46.02},
        {**base, "name_or_title": "The Star-Touched Queen", "price": 32.30},
    ]
    unique, dupes = find_duplicates(records)
    assert len(unique) == 2 and len(dupes) == 0