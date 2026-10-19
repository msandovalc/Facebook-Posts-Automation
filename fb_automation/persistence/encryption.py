"""Password encryption with Fernet. Key stored in the OS keyring."""
from __future__ import annotations

import getpass
import logging

import keyring
from cryptography.fernet import Fernet

from fb_automation import config

logger = logging.getLogger(__name__)


class DatabaseEncrypt:
    def __init__(self, service: str = config.KEYRING_SERVICE):
        user = getpass.getuser()
        stored = keyring.get_password(service, user)
        if not stored:
            stored = Fernet.generate_key().decode()
            keyring.set_password(service, user, stored)
            logger.info("Fernet key generated and stored in keyring (%s/%s)", service, user)
        self._fernet = Fernet(stored.encode())

    def encrypt(self, password: str) -> bytes:
        return self._fernet.encrypt(password.encode())

    def decrypt(self, blob: bytes) -> str:
        return self._fernet.decrypt(blob).decode()