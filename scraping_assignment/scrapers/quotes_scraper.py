import logging
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

START_URL = "https://quotes.toscrape.com/"


class QuotesScraper(BaseScraper):
    source_name = "Quotes to Scrape"

    def scrape(self, max_pages=None):
        return self.scrape_all_pages(START_URL, self.parse_page, max_pages)

    def parse_page(self, soup, page_url):
        records = []
        for div in soup.select("div.quote"):
            try:
                records.append(self.parse_quote(div, page_url))
            except Exception as exc:
                logger.warning("Skipping a quote on %s: %s", page_url, exc)
        return records

    def parse_quote(self, div, page_url):
        text = div.select_one("span.text")
        author = div.select_one("small.author")
        author_link = div.select_one('a[href^="/author/"]')
        tags = [t.get_text() for t in div.select("a.tag")]  # may be empty

        return {
            "text": text.get_text() if text else None,
            "author": author.get_text() if author else None,
            "author_url": urljoin(page_url, author_link["href"]) if author_link else None,
            "tags_raw": tags,
            "page_url": page_url,  # this becomes source_url in the final data model
        }