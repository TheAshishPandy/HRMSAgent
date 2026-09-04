import os
import pytest
from cryptography.fernet import Fernet


def test_get_settings_requires_jwt_and_encryption_key(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        get_settings()


def test_encrypt_roundtrip(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", key)
    monkeypatch.setenv("JWT_SECRET", "test-secret-at-least-32-chars-long")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import crypto
    crypto.reset()
    token = crypto.encrypt_str("ada@example.com")
    assert token != "ada@example.com"
    assert crypto.decrypt_str(token) == "ada@example.com"
    assert crypto.hmac_email("Ada@example.com") == crypto.hmac_email("ada@example.com")
