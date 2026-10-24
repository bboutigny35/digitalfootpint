import hashlib
import hmac
import secrets

from app.core.config import get_settings


def new_token() -> str:
    return secrets.token_urlsafe(48)


def token_digest(token: str) -> str:
    return hmac.new(get_settings().secret_key.encode(), token.encode(), hashlib.sha256).hexdigest()


def tokens_match(token: str, digest: str) -> bool:
    return hmac.compare_digest(token_digest(token), digest)
