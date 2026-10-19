"""BasePage: pages declare SELECTORS = a dict from contract.py."""
from __future__ import annotations

import logging
from typing import Sequence

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from fb_automation.locators.contract import Selector
from fb_automation.locators.loader import resolve_all, resolve_one

logger = logging.getLogger(__name__)


class BasePage:
    # Each subclass overrides this with its page dict from contract.py.
    SELECTORS: dict[str, list[Selector]] = {}

    def __init__(self, driver: WebDriver, default_timeout: float = 10):
        self.driver = driver
        self.default_timeout = default_timeout

    def _candidates(self, name: str) -> list[Selector]:
        if name not in self.SELECTORS:
            raise KeyError(
                f"'{name}' is not declared in {type(self).__name__}.SELECTORS. "
                f"Available: {sorted(self.SELECTORS)}"
            )
        return self.SELECTORS[name]

    def find(self, name: str, timeout: float | None = None,
             condition=EC.presence_of_element_located) -> WebElement:
        return resolve_one(
            self.driver, self._candidates(name), name=name,
            timeout=timeout or self.default_timeout, condition=condition,
        )

    def find_all(self, name: str, timeout: float | None = None) -> list[WebElement]:
        return resolve_all(
            self.driver, self._candidates(name), name=name,
            timeout=timeout or self.default_timeout,
        )

    def click(self, name: str, timeout: float | None = None) -> WebElement:
        el = self.find(name, timeout, condition=EC.element_to_be_clickable)
        try:
            el.click()
        except Exception:
            logger.debug("native click failed on '%s' — JS click", name)
            self.driver.execute_script("arguments[0].click();", el)
        return el

    def type_text(self, name: str, text: str, timeout: float | None = None) -> WebElement:
        import platform as _platform
        import time
        import pyperclip
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        el = self.find(name, timeout)
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
        except Exception:
            pass

        is_editable = el.get_attribute("contenteditable") == "true"

        if not is_editable:
            el.clear()
            el.send_keys(text)
            return el

        # --- Lexical path ---
        try:
            pyperclip.copy(text)
            self.driver.execute_script("arguments[0].focus();", el)
            el.click()
            modifier = Keys.COMMAND if _platform.system() == "Darwin" else Keys.CONTROL

            logger.info("Pegando texto (Ctrl+V)...")
            ActionChains(self.driver).key_down(modifier).send_keys("v").key_up(modifier).perform()
            time.sleep(1)  # Dar tiempo a React de procesar el paste

            # VERIFICACIÓN: ¿El texto realmente se escribió?
            landed = self.driver.execute_script("return arguments[0].innerText;", el)
            if text[:20] not in landed:
                logger.warning("Ctrl+V falló. Intentando send_keys de respaldo...")
                el.send_keys(text)
                time.sleep(1)
                landed = self.driver.execute_script("return arguments[0].innerText;", el)

                if text[:20] not in landed:
                    raise Exception("No se pudo escribir el texto en el editor (Lexical ignoró el input).")

            logger.info("Texto verificado en el editor exitosamente.")
            return el
        except Exception as e:
            logger.error("Error al escribir texto: %s", e)
            raise e

    def exists(self, name: str, timeout: float = 2) -> bool:
        try:
            self.find(name, timeout=timeout)
            return True
        except Exception:
            return False

    def goto(self, url: str) -> None:
        logger.info("goto %s", url)
        self.driver.get(url)