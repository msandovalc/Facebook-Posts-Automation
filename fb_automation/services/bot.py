"""
Bot: thin facade over Page Objects.

Keeps the original public API (doLogin, postToUrl, groupScraper, logout,
check_browser_state, logged_in) so the UI doesn't need to change.
"""
from __future__ import annotations

import logging

from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from fb_automation.pages.composer_page import ComposerPage
from fb_automation.pages.group_page import GroupPage
from fb_automation.pages.login_page import LoginPage
from fb_automation.services.browser import create_driver

logger = logging.getLogger(__name__)


class Bot:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = create_driver(headless=headless)
        self.logged_in = False

        self.login_page = LoginPage(self.driver)
        self.composer_page = ComposerPage(self.driver)
        self.group_page = GroupPage(self.driver)
        logger.info("Bot initialized (headless=%s)", headless)

    # ---------- lifecycle ----------

    def close(self) -> None:
        """Shut down the browser cleanly."""
        try:
            self.driver.quit()
            logger.info("Bot closed")
        except Exception:
            logger.exception("Error while closing Bot")
        finally:
            self.driver = None  # type: ignore

    def __enter__(self) -> "Bot":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ---------- public API (backwards compatible) ----------

    def check_browser_state(self) -> None:
        """Restart the driver if the session was lost."""
        try:
            _ = self.driver.current_url
        except (InvalidSessionIdException, WebDriverException):
            logger.warning("Browser session lost — restarting")
            self._restart()

    def _restart(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass
        self.driver = create_driver(headless=self.headless)
        self.login_page = LoginPage(self.driver)
        self.composer_page = ComposerPage(self.driver)
        self.group_page = GroupPage(self.driver)
        self.logged_in = False

    def doLogin(self, username: str, password: str) -> str:
        if self.logged_in:
            return "Already logged in"
        try:
            self.login_page.open()
            if self.login_page.login(username, password):
                self.logged_in = True
                return "Login Successful"
            return "Failed to login"
        except Exception:
            logger.exception("Error in doLogin(%s)", username)
            return "Failed to login"

    def postToUrl(
        self,
        message: str = "",
        media_path: str = "",
        url: str = "http://mbasic.facebook.com",
    ) -> str:
        try:
            ok = self.composer_page.post(url, message=message, media_path=media_path)
            return f"Posted to :{url}" if ok else f"Failed to post to :{url}"
        except Exception:
            logger.exception("postToUrl failed")
            return f"Failed to post to :{url}"

    def groupScraper(self, url: str) -> str:
        try:
            return self.group_page.scrape_members(url)
        except Exception:
            logger.exception("groupScraper failed")
            return ""

    def logout(self) -> str:
        try:
            self.logged_in = False
            self.driver.delete_all_cookies()
            self.driver.get("https://mobile.facebook.com/")
            logger.info("Logout OK")
            return "Logged out successfully"
        except WebDriverException:
            logger.exception("Logout failed")
            return "Failed to logout"