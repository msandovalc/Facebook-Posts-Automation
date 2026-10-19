"""Global configuration. Single source of truth for constants."""
from __future__ import annotations

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("FB_DB_PATH", BASE_DIR / "FB.db"))

# URLs
BASE_URL = "http://mbasic.facebook.com"
LOGIN_URL = f"{BASE_URL}/"

# Timeouts (seconds)
DEFAULT_TIMEOUT = 10
LOGIN_TIMEOUT = 15
POST_TIMEOUT = 20
SCRAPE_TIMEOUT = 10

# Driver
IMPLICIT_WAIT = 5
PAGE_LOAD_TIMEOUT = 30

# Worker
TASK_POLL_INTERVAL = 15  # max seconds to sleep between checks

# Keyring
KEYRING_SERVICE = "fbdb"

# Facebook markers
LOGIN_SUCCESS_TITLE = "Facebook"