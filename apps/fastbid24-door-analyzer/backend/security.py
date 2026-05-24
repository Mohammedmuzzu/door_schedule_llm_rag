import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from werkzeug.security import check_password_hash, generate_password_hash

from config import settings


class SecretConfigurationError(RuntimeError):
    pass


class SecretDecryptionError(RuntimeError):
    pass


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def issue_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    return token, token_digest(token), expires_at


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _secret_cipher() -> Fernet:
    if not settings.secret_key:
        raise SecretConfigurationError("FASTBID24_SECRET_KEY is required to store account analysis keys.")
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise ValueError("Secret value cannot be empty.")
    return _secret_cipher().encrypt(clean.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _secret_cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise SecretDecryptionError("Stored account analysis key could not be decrypted with this server secret.") from exc


def secret_fingerprint(value: str) -> str:
    return hashlib.sha256((value or "").strip().encode("utf-8")).hexdigest()


def secret_hint(value: str) -> str:
    clean = (value or "").strip()
    return f"...{clean[-4:]}" if len(clean) >= 4 else ""
