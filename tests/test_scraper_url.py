import pytest

from backend.scrap import ScraperThread, build_search_url


def test_search_term_builds_paginated_ebay_search_url():
    url = build_search_url("wireless headphones", 3)

    assert url.startswith("https://www.ebay.com/sch/i.html?")
    assert "_nkw=wireless+headphones" in url
    assert "_pgn=3" in url
    assert "_ipg=240" in url


def test_user_ebay_url_is_preserved_and_page_is_updated():
    url = build_search_url(
        "",
        4,
        "https://www.ebay.com/sch/i.html?_nkw=phone&_pgn=1&_ipg=60",
    )

    assert "_nkw=phone" in url
    assert "_pgn=4" in url
    assert "_ipg=240" in url


@pytest.mark.parametrize(
    "url",
    [
        "http://www.ebay.com/sch/i.html?_nkw=phone",
        "https://example.com/sch/i.html?_nkw=phone",
        "https://www.ebay.com/itm/123456789",
    ],
)
def test_only_https_ebay_search_urls_are_accepted(url):
    with pytest.raises(ValueError, match="HTTPS eBay search-results URL"):
        build_search_url("", 1, url)


def test_scraper_uses_search_term_from_the_supplied_url():
    scraper = ScraperThread(
        product_name="",
        search_url="https://www.ebay.com/sch/i.html?_nkw=phone",
    )

    assert scraper.product_name == "phone"
    assert scraper._output_path().name == "phone.csv"
