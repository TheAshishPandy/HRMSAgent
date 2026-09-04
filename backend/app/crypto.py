import hashlib
import hmac
from cryptography.fernet import Fernet
from app.config import get_settings

_fernet = None


def reset() -> None:
    global _fernet
    _fernet = None


def _f() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_settings().data_encryption_key.encode())
    return _fernet


def encrypt_str(plain: str) -> str:
    return _f().encrypt(plain.encode()).decode()


def decrypt_str(token: str) -> str:
    return _f().decrypt(token.encode()).decode()


def hmac_email(email: str) -> str:
    key = get_settings().data_encryption_key.encode()
    return hmac.new(key, email.strip().lower().encode(), hashlib.sha256).hexdigest()
