from processing.cleaning import (
    clean_text, strip_quotes, clean_price, clean_rating,
    clean_tags, normalize_url, clean_book, clean_quote,
)


def test_clean_text():
    assert clean_text("  Hello \n World ") == "Hello World"
    assert clean_text("a\xa0b") == "a b"
    assert clean_text("   ") is None
    assert clean_text(None) is None


def test_strip_quotes():
    assert strip_quotes("\u201cHello there\u201d") == "Hello there"


def test_clean_price():
    assert clean_price("£51.77") == 51.77
    assert clean_price("£1,051.77") == 1051.77
    assert clean_price("free") is None
    assert clean_price(None) is None


def test_clean_rating():
    assert clean_rating("star-rating Three") == 3
    assert clean_rating("star-rating") is None


def test_clean_tags():
    assert clean_tags(["Love", "books", "love"]) == "books;love"
    assert clean_tags([]) is None


def test_normalize_url():
    assert normalize_url("/page/2/", base="https://quotes.toscrape.com/") == \
        "https://quotes.toscrape.com/page/2/"
    assert normalize_url("not a url") is None


def test_clean_book_and_quote():
    book = clean_book({
        "title": " A  Book ", "url": "https://books.toscrape.com/x",
        "price_raw": "£10.50", "rating_raw": "star-rating Four",
        "availability_raw": "\n In stock \n",
    })
    assert book["name_or_title"] == "A Book"
    assert book["price"] == 10.5 and book["rating"] == 4
    assert book["availability"] == "In stock"
    assert book["author"] is None

    quote = clean_quote({
        "text": "\u201cHi\u201d", "author": "Bob",
        "tags_raw": ["B", "a"], "page_url": "https://quotes.toscrape.com/",
    })
    assert quote["name_or_title"] == "Hi" and quote["tags"] == "a;b"
    assert quote["price"] is None

def test_strip_quotes_only_removes_wrapping_pair():
    assert strip_quotes("\u201cHe said \u2018hi\u2019\u201d") == "He said \u2018hi\u2019"
    assert strip_quotes("\u201cIt's the dogs'\u201d") == "It's the dogs'"