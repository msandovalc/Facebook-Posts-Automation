"""Group scrape page."""
from __future__ import annotations
import logging
from difflib import SequenceMatcher
from fb_automation import config
from fb_automation.locators.contract import GROUP_PAGE
from fb_automation.utils import url_parse
from .base_page import BasePage

logger = logging.getLogger(__name__)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio()


class GroupPage(BasePage):
    SELECTORS = GROUP_PAGE

    def scrape_members(self, url: str) -> str:
        if "groups" not in url:
            return ""
        parsed = url_parse(url)
        if parsed is None:
            return ""
        try:
            self.goto(parsed + "?")
            self.click("members_tab", timeout=config.SCRAPE_TIMEOUT)
            self.click("all_members", timeout=config.SCRAPE_TIMEOUT)

            data: list[str] = []
            home = None
            try:
                home = self.find("home_link", timeout=3)
            except Exception:
                pass

            while True:
                for link in self.find_all("links", timeout=config.SCRAPE_TIMEOUT):
                    if home is not None and link.id == home.id:
                        continue
                    try:
                        text = (link.text or "").strip()
                        href = link.get_attribute("href") or ""
                    except Exception:
                        continue
                    if not text or text == "See More":
                        continue
                    if _similarity(href, text) > 0.1:
                        data.append(f"{text} {href}")
                try:
                    self.click("see_more", timeout=3)
                except Exception:
                    break
            logger.info("Scrape OK: %d members", len(data))
            return "\n".join(data)
        except Exception:
            logger.exception("Failed to scrape %s", parsed)
            return ""