import re
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlencode, urlsplit, urlunsplit

import pandas as pd
from bs4 import BeautifulSoup
from PyQt5.QtCore import QObject, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


DATA_DIRECTORY = Path(__file__).resolve().parent / "data"
TARGET_ENTITY_COUNT = 15_000
MAX_PAGE_SIZE = 240
MAX_PAGES = 100


def build_search_url(product_name: str, page_number: int, search_url: str = "") -> str:
    if page_number < 1:
        raise ValueError("page_number must be at least 1.")

    if search_url.strip():
        parsed = urlsplit(search_url.strip())
        hostname = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or not re.fullmatch(
                r"(?:[a-z0-9-]+\.)*ebay\.[a-z]{2,3}(?:\.[a-z]{2})?",
                hostname,
            )
            or not (parsed.path.startswith("/sch/") or parsed.path.startswith("/s/"))
        ):
            raise ValueError(
                "Enter an HTTPS eBay search-results URL, such as "
                "https://www.ebay.com/sch/i.html?_nkw=phone."
            )
        query = parse_qs(parsed.query, keep_blank_values=True)
        if not query.get("_nkw", [""])[0].strip() and not product_name.strip():
            raise ValueError("Enter a product name or an eBay URL containing a search term.")
        query["_ipg"] = [str(MAX_PAGE_SIZE)]
        query["_pgn"] = [str(page_number)]
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query, doseq=True), "")
        )

    if not product_name.strip():
        raise ValueError("Enter a product name or an eBay search-results URL.")
    return (
        "https://www.ebay.com/sch/i.html?_from=R40&_nkw="
        f"{quote_plus(product_name)}&_sacat=0&_ipg={MAX_PAGE_SIZE}"
        f"&_pgn={page_number}&rt=nc"
    )


class ScraperThread(QObject):
    progress_signal = pyqtSignal(int)
    entity_progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(str)

    def __init__(
        self,
        product_name: str = "",
        total_pages: int = MAX_PAGES,
        search_url: str = "",
        target_entities: int = TARGET_ENTITY_COUNT,
    ) -> None:
        super().__init__()
        if total_pages < 1:
            raise ValueError("total_pages must be at least 1.")
        if target_entities < 1:
            raise ValueError("target_entities must be at least 1.")
        self.search_url = search_url.strip()
        query_term = parse_qs(urlsplit(self.search_url).query).get("_nkw", [""])[0]
        self.product_name = (query_term or product_name).strip()
        build_search_url(self.product_name, 1, self.search_url)
        self.total_pages = total_pages
        self.target_entities = target_entities
        self.driver = None
        self.thread = None
        self.stop_flag = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()

    def setup_driver(self) -> None:
        chrome_options = Options()
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--user-agent=Mozilla/5.0")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)

    def _output_path(self) -> Path:
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", self.product_name)
        filename = filename.strip(" .")[:120] or "scraped_products"
        return DATA_DIRECTORY / f"{filename}.csv"

    def _wait_until_resumed(self) -> bool:
        while not self.pause_event.wait(timeout=0.2):
            if self.stop_flag.is_set():
                return False
        return not self.stop_flag.is_set()

    def scrape_products(self) -> None:
        records = []
        listing_ids = set()
        failure = None
        saved = False
        output_path = self._output_path()
        pages_without_new_listings = 0

        try:
            self.setup_driver()
            for page_number in range(1, self.total_pages + 1):
                if not self._wait_until_resumed():
                    break

                url = build_search_url(
                    self.product_name, page_number, self.search_url
                )
                self.driver.get(url)
                page_source = self.driver.page_source
                if not isinstance(page_source, str) or not page_source.strip():
                    raise RuntimeError(
                        f"The browser returned an empty page for {url}"
                    )
                soup = BeautifulSoup(page_source, "html.parser")
                new_records = 0

                for item in soup.select("li.s-item"):
                    name = item.find("div", attrs={"class": "s-item__title"})
                    price = item.find("span", attrs={"class": "s-item__price"})
                    if not name or not price:
                        continue

                    rating = item.find("span", attrs={"class": "s-item__reviews-count"})
                    rating_value = rating.find("span") if rating else None
                    country = item.find(
                        "span", attrs={"class": "s-item__location s-item__itemLocation"}
                    )
                    shipping = item.find(
                        "span", attrs={"class": "s-item__shipping s-item__logisticsCost"}
                    )
                    condition = item.find("span", attrs={"class": "SECONDARY_INFO"})
                    watch = item.find(
                        "span", attrs={"class": "s-item__dynamic s-item__watchCountTotal"}
                    )
                    watcher = watch.find("span", attrs={"class": "BOLD"}) if watch else None
                    discount_tag = item.find(
                        "span", attrs={"class": "s-item__discount s-item__discount"}
                    )
                    discount = (
                        discount_tag.find("span", attrs={"class": "BOLD"})
                        if discount_tag
                        else None
                    )
                    seller_info = item.find(
                        "span", attrs={"class": "s-item__seller-info-text"}
                    )
                    match = (
                        re.match(r"(.+?)\s\(([\d,]+)\)\s([\d.]+%)", seller_info.text.strip())
                        if seller_info
                        else None
                    )
                    seller_name = match.group(1).strip() if match else "Not available"
                    seller_products = int(match.group(2).replace(",", "")) if match else 0
                    seller_rating = match.group(3) if match else "Not available"

                    price_numeric = re.sub(r"[^\d]", "", price.text)
                    shipping_numeric = (
                        re.sub(r"[^\d]", "", shipping.text) if shipping else ""
                    )
                    listing_link = item.select_one("a.s-item__link")
                    listing_url = listing_link.get("href", "") if listing_link else ""
                    listing_match = re.search(r"/itm/(?:[^/?]+/)?(\d+)", listing_url)
                    listing_id = (
                        listing_match.group(1)
                        if listing_match
                        else f"{name.text.strip().casefold()}|{price_numeric}"
                    )
                    if listing_id in listing_ids:
                        continue
                    listing_ids.add(listing_id)
                    records.append(
                        {
                            "Product Name": name.text.strip(),
                            "Price": int(price_numeric) if price_numeric else 0,
                            "Ratings": rating_value.text if rating_value else "Not available",
                            "Watchers": watcher.text if watcher else "Not available",
                            "Country": country.text if country else "Not available",
                            "Discount": discount.text if discount else "Not available",
                            "Shipping Price": int(shipping_numeric) if shipping_numeric else 0,
                            "Condition": condition.text if condition else "Not available",
                            "Seller Name": seller_name,
                            "Seller Sold Products": seller_products,
                            "Seller Ratings": seller_rating,
                        }
                    )
                    new_records += 1
                    if len(records) >= self.target_entities:
                        break

                percent = min(100, int(len(records) / self.target_entities * 100))
                self.progress_signal.emit(percent)
                self.entity_progress_signal.emit(
                    min(len(records), self.target_entities), self.target_entities
                )
                pages_without_new_listings = (
                    pages_without_new_listings + 1 if new_records == 0 else 0
                )
                if len(records) >= self.target_entities or pages_without_new_listings >= 2:
                    break
                if page_number < self.total_pages and not self.stop_flag.is_set():
                    time.sleep(1)
        except Exception as exc:
            failure = f"Scraping failed: {exc}"
        finally:
            if self.driver is not None:
                try:
                    self.driver.quit()
                except Exception as exc:
                    failure = f"{failure}; browser shutdown failed: {exc}" if failure else (
                        f"Browser shutdown failed: {exc}"
                    )
                self.driver = None

            if records:
                try:
                    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
                    columns = [
                        "Product Name",
                        "Price",
                        "Ratings",
                        "Watchers",
                        "Country",
                        "Discount",
                        "Shipping Price",
                        "Condition",
                        "Seller Name",
                        "Seller Sold Products",
                        "Seller Ratings",
                    ]
                    data = pd.DataFrame(records, columns=columns)
                    if output_path.exists():
                        data.to_csv(
                            output_path,
                            mode="a",
                            header=False,
                            index=False,
                            encoding="utf-8",
                        )
                    else:
                        data.to_csv(output_path, index=False, encoding="utf-8")
                    saved = True
                except (OSError, ValueError) as exc:
                    failure = f"{failure}; saving CSV failed: {exc}" if failure else (
                        f"Saving CSV failed: {exc}"
                    )

            if saved and self.stop_flag.is_set() and failure is None:
                status = f"Scraping stopped. {len(records)} rows saved to {output_path.name}."
            elif saved and failure:
                status = (
                    f"{failure}. Partial results ({len(records)} rows) saved to "
                    f"{output_path.name}."
                )
            elif failure:
                status = f"{failure}. No rows were saved."
            elif not records:
                status = (
                    "No products were parsed from eBay's response. The site may have "
                    "changed its page or restricted this request; no CSV was created."
                )
            else:
                status = (
                    f"Scraping completed with {len(records):,} listings "
                    f"({len(records):,}/{self.target_entities:,} target) saved to "
                    f"{output_path.name}."
                )
            self.finished_signal.emit(status)

    def start(self) -> None:
        if self.thread is not None and self.thread.is_alive():
            raise RuntimeError("Scraping is already running.")
        self.thread = threading.Thread(target=self.scrape_products, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_flag.set()
        self.pause_event.set()

    def pause(self) -> None:
        self.pause_event.clear()

    def resume(self) -> None:
        self.pause_event.set()
