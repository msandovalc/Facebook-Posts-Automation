"""Resolves a list of Selector candidates to a WebElement (or list).

3-pass resolution strategy:
  1. Existence check (no wait) — instant for whichever candidate exists.
  2. If nothing exists yet, wait on the primary (first) with the full timeout.
  3. If that fails, wait on the remaining fallbacks with a shorter timeout.
"""
from __future__ import annotations

import logging
from typing import Sequence

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .contract import Selector

logger = logging.getLogger(__name__)


def resolve_one(
    driver: WebDriver,
    candidates: Sequence[Selector],
    name: str = "",
    timeout: float = 10,
    condition=EC.presence_of_element_located,
):
    if not candidates:
        raise ValueError(f"No Selector candidates for '{name}'")

    # --- Pass 1: existence check, no waiting ---
    for idx, sel in enumerate(candidates):
        try:
            els = driver.find_elements(sel.by, sel.value)
            if els:
                if idx > 0:
                    logger.debug(
                        "Selector '%s': matched #%d (%s=%s); primary absent",
                        name, idx, sel.by, sel.value,
                    )
                return els[0]
        except Exception:
            pass

    # --- Pass 2: nothing on the page yet — wait on the primary with full timeout ---
    primary = candidates[0]
    try:
        return WebDriverWait(driver, timeout).until(
            condition((primary.by, primary.value))
        )
    except TimeoutException:
        pass

    # --- Pass 3: short wait on each fallback ---
    per_timeout = max(2.0, timeout / max(1, len(candidates)))
    for idx, sel in enumerate(candidates[1:], start=1):
        try:
            el = WebDriverWait(driver, per_timeout).until(
                condition((sel.by, sel.value))
            )
            logger.warning(
                "Selector '%s' used fallback #%d (%s=%s). "
                "Update fb_automation/locators/contract.py.",
                name, idx, sel.by, sel.value,
            )
            return el
        except TimeoutException:
            continue

    raise TimeoutException(
        f"Selector '{name}' never appeared. Candidates tried: "
        f"{[f'{s.by}={s.value}' for s in candidates]}"
    )


def resolve_all(
    driver: WebDriver,
    candidates: Sequence[Selector],
    name: str = "",
    timeout: float = 10,
):
    if not candidates:
        raise ValueError(f"No Selector candidates for '{name}'")

    # Pass 1: existence check
    for idx, sel in enumerate(candidates):
        try:
            els = driver.find_elements(sel.by, sel.value)
            if els:
                if idx > 0:
                    logger.debug(
                        "Selector '%s' (all): matched #%d (%s=%s); primary absent",
                        name, idx, sel.by, sel.value,
                    )
                return els
        except Exception:
            pass

    # Pass 2: wait on primary
    primary = candidates[0]
    try:
        return WebDriverWait(driver, timeout).until(
            lambda d: d.find_elements(primary.by, primary.value) or False
        )
    except TimeoutException:
        pass

    # Pass 3: short wait on fallbacks
    per_timeout = max(2.0, timeout / max(1, len(candidates)))
    for idx, sel in enumerate(candidates[1:], start=1):
        try:
            els = WebDriverWait(driver, per_timeout).until(
                lambda d: d.find_elements(sel.by, sel.value) or False
            )
            logger.warning(
                "Selector '%s' (all) used fallback #%d (%s=%s). "
                "Update fb_automation/locators/contract.py.",
                name, idx, sel.by, sel.value,
            )
            return els
        except TimeoutException:
            continue

    raise TimeoutException(
        f"Selector '{name}' (all) never appeared. Candidates: "
        f"{[f'{s.by}={s.value}' for s in candidates]}"
    )