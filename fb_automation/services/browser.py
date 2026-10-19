"""WebDriver factory + manager. Context manager for clean shutdown."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from fb_automation import config

logger = logging.getLogger(__name__)


def create_driver(headless: bool = False) -> webdriver.Firefox:
    """
    Create a fresh Firefox instance.
    Selenium Manager (Selenium >= 4.6) resolves geckodriver automatically.
    """
    options = Options()
    if headless:
        options.add_argument("-headless")
    options.add_argument("--width=1280")
    options.add_argument("--height=1024")
    # Realistic UA to reduce headless detection
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0",
    )

    logger.info("Starting Firefox (headless=%s)", headless)
    driver = webdriver.Firefox(service=Service(), options=options)
    driver.implicitly_wait(config.IMPLICIT_WAIT)
    driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
    return driver


@contextmanager
def managed_driver(headless: bool = False) -> Iterator[webdriver.Firefox]:
    """Yield a driver and always quit it afterwards."""
    driver = create_driver(headless=headless)
    try:
        yield driver
    finally:
        try:
            driver.quit()
            logger.info("Firefox closed")
        except Exception:
            logger.exception("Error while closing the driver")