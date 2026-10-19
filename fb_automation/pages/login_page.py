"""Login page."""
from __future__ import annotations
import logging
from fb_automation import config
from fb_automation.locators.contract import LOGIN_PAGE
from .base_page import BasePage

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    SELECTORS = LOGIN_PAGE

    def open(self) -> "LoginPage":
        self.goto(config.LOGIN_URL)
        return self

    def is_logged_in(self) -> bool:
        return self.exists("logged_in", timeout=2)

    def login(self, username: str, password: str) -> bool:
        logger.info("Login attempt for %s", username)
        try:
            self.type_text("email", username, timeout=config.LOGIN_TIMEOUT)
            self.type_text("password", password, timeout=config.LOGIN_TIMEOUT)
            self.click("submit", timeout=config.LOGIN_TIMEOUT)
            if self.is_logged_in() or self.driver.title.strip() == config.LOGIN_SUCCESS_TITLE:
                logger.info("Login OK for %s", username)
                return True
            logger.warning("Login FAILED for %s (title=%r)", username, self.driver.title)
            return False
        except Exception:
            logger.exception("Exception during login for %s", username)
            return False