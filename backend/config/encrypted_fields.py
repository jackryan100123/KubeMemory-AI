"""Fernet-encrypted database fields compatible with Django 4.2+."""

from __future__ import annotations

from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet() -> Fernet:
    keys = getattr(settings, "FERNET_KEYS", None) or []
    if not keys or not keys[0]:
        raise ValueError(
            "FERNET_KEY environment variable is required for encrypted fields"
        )
    key = keys[0]
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


class EncryptedTextField(models.TextField):
    """TextField that transparently encrypts values at rest using Fernet."""

    description = "Fernet-encrypted text"

    def get_prep_value(self, value: Any) -> str | None:
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        if not isinstance(value, str):
            value = str(value)
        return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")

    def from_db_value(
        self, value: str | None, expression: Any, connection: Any
    ) -> str | None:
        if value is None or value == "":
            return value
        try:
            return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return value

    def to_python(self, value: Any) -> str | None:
        if value is None or value == "":
            return value
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return value
