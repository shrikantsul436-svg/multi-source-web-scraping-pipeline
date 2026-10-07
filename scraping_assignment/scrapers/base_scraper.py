from urllib.parse import urljoin
from bs4 import BeautifulSoup

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "ScrapingAssignment/1.0 (learning project)"}
    )
    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class BaseScraper:
    """Shared networking: one session, timeout, polite delay."""

    def __init__(self, delay: float = 0.5, timeout: int = 10):
        self.session = create_session()
        self.delay = delay
        self.timeout = timeout

    def fetch(self, url: str):
        """Return the response, or None if the request failed after retries."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = "utf-8"  # keeps £ from turning into Â£
            logger.info("Fetched %s", url)
            return response
        except requests.RequestException as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            return None
        finally:
            time.sleep(self.delay)

    def scrape_all_pages(self, start_url, parse_page, max_pages=None):
        """Follow 'li.next > a' until there is no next page.

        parse_page(soup, page_url) must return a list of raw record dicts.
        max_pages is only for quick testing; leave it None for a full run.
        """
        url, page, records = start_url, 1, []
        while url and (max_pages is None or page <= max_pages):
            logger.info("Page %d: %s", page, url)
            response = self.fetch(url)
            if response is None:
                logger.error("Stopping pagination at page %d", page)
                break  # stop this source only; the other source still runs
            soup = BeautifulSoup(response.text, "lxml")
            records.extend(parse_page(soup, url))

            next_link = soup.select_one("li.next > a")
            if next_link and next_link.get("href"):
                url = urljoin(url, next_link["href"])
            else:
                url = None
            page += 1
        return records