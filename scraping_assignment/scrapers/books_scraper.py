import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

START_URL = "https://books.toscrape.com/"


class BooksScraper(BaseScraper):
    source_name = "Books to Scrape"

    def __init__(self, fetch_details: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.fetch_details = fetch_details

    def scrape(self, max_pages=None):
        return self.scrape_all_pages(START_URL, self.parse_page, max_pages)

    def parse_page(self, soup, page_url):
        records = []
        for article in soup.select("article.product_pod"):
            try:
                records.append(self.parse_book(article, page_url))
            except Exception as exc:  # one bad record must not kill the page
                logger.warning("Skipping a book on %s: %s", page_url, exc)
        return records

    def parse_book(self, article, page_url):
        link = article.select_one("h3 > a")
        price = article.select_one("p.price_color")
        rating = article.select_one("p.star-rating")
        availability = article.select_one("p.availability")

        href = urljoin(page_url, link["href"]) if link and link.get("href") else None

        record = {
            "title": link.get("title") if link else None,  # full title, not the "..." text
            "url": href,
            "price_raw": price.get_text() if price else None,
            "rating_raw": " ".join(rating.get("class", [])) if rating else None,
            "availability_raw": availability.get_text() if availability else None,
            "category_raw": None,
            "description_raw": None,
            "page_url": page_url,
        }

        if self.fetch_details and href:
            record.update(self.parse_detail(href))
        return record

    def parse_detail(self, url):
        """Category and description exist only on the book's own page."""
        response = self.fetch(url)
        if response is None:
            return {}  # keep the book, just without these two fields
        soup = BeautifulSoup(response.text, "lxml")

        crumbs = soup.select("ul.breadcrumb li a")  # Home > Books > Category
        category = crumbs[2].get_text() if len(crumbs) >= 3 else None

        desc_tag = soup.select_one("#product_description + p")
        description = desc_tag.get_text() if desc_tag else None

        return {"category_raw": category, "description_raw": description}