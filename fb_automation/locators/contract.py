"""Selector Contract — single source of truth for every XPath/CSS the app uses.

HOW TO UPDATE WHEN FACEBOOK CHANGES:
  1. Open this file.
  2. Find the entry (e.g. LOGIN_PAGE["submit"]).
  3. Add the new Selector at the TOP of the list.
  That is the ONLY file you edit. No Page Object needs to change.

ORDER MATTERS: the loader checks candidates in order and returns the FIRST
one that currently exists in the DOM. Put the most likely selector first.
"""
from __future__ import annotations
from dataclasses import dataclass
from selenium.webdriver.common.by import By


@dataclass(frozen=True)
class Selector:
    by: str
    value: str


def sel(by: str, value: str) -> Selector:
    return Selector(by, value)


# ---------------------------------------------------------------- LOGIN PAGE
LOGIN_PAGE: dict[str, list[Selector]] = {
    "email": [
        sel(By.NAME, "email"),                                         # works on mbasic AND modern UI
        sel(By.XPATH, '//input[@type="email" or @type="text"]'),       # generic fallback
        sel(By.CSS_SELECTOR, "input#email"),
    ],
    "password": [
        sel(By.NAME, "pass"),                                          # works on mbasic AND modern UI
        sel(By.XPATH, '//input[@type="password"]'),                    # generic fallback
    ],
    "submit": [
        # mbasic fast path
        sel(By.NAME, "login"),
        sel(By.XPATH, '//input[@type="submit"]'),
        # modern facebook.com (div/span UI)
        sel(By.XPATH,
            '//span[normalize-space()="Log in" or normalize-space()="Log In"]'),
        sel(By.XPATH,
            '//*[@role="button"][.//text()="Log in" or .//text()="Log In"]'),
        sel(By.XPATH,
            '//*[@aria-label="Log in" or @aria-label="Log In"]'),
        sel(By.XPATH,
            '//*[self::button or self::a][normalize-space()="Log in" or normalize-space()="Log In"]'),
    ],
    "logged_in": [
        sel(By.XPATH, '//div[@aria-label="Your profile"]'),
        sel(By.XPATH, '//*[@data-pagelet="ProfileCometHeader"]'),
        sel(By.XPATH, '//input[@name="xc_message"]'),
        sel(By.XPATH, '//a[contains(@href,"logout")]'),
    ],
}

# ------------------------------------------------------------- COMPOSER PAGE
COMPOSER_PAGE: dict[str, list[Selector]] = {
    # The "Write something..." element on the modern UI is a <div role="button">.
    # Clicking it opens the "Create post" modal.
    "open_editor": [
        sel(By.XPATH, '//div[@role="button"][.//span[contains(normalize-space(), "Escribe algo") or contains(normalize-space(), "Write something")]]'),
        sel(By.XPATH, '//div[@aria-label="Crear publicación" or @aria-label="Create post"]'),
        sel(By.XPATH, '//div[@role="button" and .//span[normalize-space()="Crear publicación" or normalize-space()="Create post"]]'),
        sel(By.XPATH, '//span[contains(normalize-space(), "Escribe algo") or contains(normalize-space(), "Write something")]/ancestor::div[@role="button"][1]'),
    ],

    # The real editor appears INSIDE the modal AFTER clicking open_editor.
    # We scope this specifically to the modal or the exact aria-label to
    # avoid accidentally typing into comment boxes in the background.
    "message": [
        # 1. Exact match for the main post modal based on the placeholder/label
        sel(By.XPATH, '//div[@data-lexical-editor="true" and (contains(@aria-label, "pública") or contains(@aria-label, "public") or contains(@aria-placeholder, "pública") or contains(@aria-placeholder, "public"))]'),
        # 2. Any Lexical editor strictly inside an open dialog
        sel(By.XPATH, '//div[@role="dialog"]//div[@data-lexical-editor="true"]'),
        # 3. Fallbacks
        sel(By.XPATH, '//div[@data-lexical-editor="true"]'),
        sel(By.XPATH, '//div[@contenteditable="true" and @role="textbox"]'),
        sel(By.XPATH, '//div[@contenteditable="true"]'),
        sel(By.XPATH, '//div[@role="textbox"]'),
        sel(By.NAME, "xc_message"),
        sel(By.XPATH, '//textarea[@name="xc_message"]'),
    ],

    # Photo/Video trigger: scoped to the dialog to avoid clicking background items.
    "attach": [
        sel(By.XPATH, '//div[@role="dialog"]//div[@aria-label="Foto/Video" or @aria-label="Photo/Video"]'),
        sel(By.XPATH, '//div[@aria-label="Foto/Video" or @aria-label="Photo/Video"]'),
        sel(By.NAME, "view_photo"),
        sel(By.XPATH, '//input[@name="view_photo"]'),
    ],

    # The hidden file input.
    "file": [
        sel(By.XPATH, '//input[@type="file"]'),
        sel(By.NAME, "file1"),
    ],

    # "Done" in the photo preview (mbasic only).
    "confirm": [
        sel(By.NAME, "add_photo_done"),
        sel(By.XPATH, '//input[@name="add_photo_done"]'),
    ],

    # Final publish button: scoped to the dialog first, then global fallbacks.
    "submit": [
        sel(By.XPATH, '//div[@role="dialog"]//div[@aria-label="Publicar" or @aria-label="Post"]'),
        sel(By.XPATH, '//div[@role="dialog"]//*[@role="button"][.//span[normalize-space()="Publicar" or normalize-space()="Post"]]'),
        sel(By.XPATH, '//div[@aria-label="Publicar" or @aria-label="Post"]'),
        sel(By.XPATH, '//*[@role="button"][.//span[normalize-space()="Publicar" or normalize-space()="Post"]]'),
        sel(By.XPATH, '//span[normalize-space()="Publicar" or normalize-space()="Post"]'),
        sel(By.NAME, "view_post"),
        sel(By.XPATH, '//input[@name="view_post"]'),
    ],
}

# ---------------------------------------------------------------- GROUP PAGE
GROUP_PAGE: dict[str, list[Selector]] = {
    "members_tab": [sel(By.XPATH, '//a[text()="Members"]'),
                    sel(By.XPATH, '//a[contains(@href,"/members")]')],
    "all_members": [sel(By.XPATH, '//a[contains(@href,"list_nonfriend_nonadmin")]')],
    "home_link":   [sel(By.XPATH, '//a[text()="Go to Home"]')],
    "see_more":    [sel(By.XPATH, '//span[text()="See More"]')],
    "links":       [sel(By.TAG_NAME, "a")],
}

# ---------------------------------------------------------- GLOBAL REGISTRY
REGISTRY: dict[str, list[Selector]] = {
    **{f"login.{k}": v for k, v in LOGIN_PAGE.items()},
    **{f"composer.{k}": v for k, v in COMPOSER_PAGE.items()},
    **{f"groups.{k}": v for k, v in GROUP_PAGE.items()},
}