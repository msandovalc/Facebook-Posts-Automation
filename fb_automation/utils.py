"""Cross-cutting utilities."""
from __future__ import annotations

import logging

from fb_automation import config

logger = logging.getLogger(__name__)


def url_parse(url: str | None) -> str | None:
    """
    Convert any facebook.com URL into its mbasic variant.

    Examples:
        https://www.facebook.com/groups/123 -> http://mbasic.facebook.com/groups/123
        m.facebook.com/groups/123           -> http://mbasic.facebook.com/groups/123
        facebook.com                        -> http://mbasic.facebook.com/
        garbage                             -> None
    """
    if not url or "facebook.com" not in url:
        return None

    marker = "facebook.com"
    idx = url.find(marker)
    if idx == -1:
        return None

    tail = url[idx + len(marker):]
    if not tail or tail == "/":
        return f"{config.BASE_URL}/"
    if tail.startswith("/"):
        tail = tail[1:]
    return f"{config.BASE_URL}/{tail}"