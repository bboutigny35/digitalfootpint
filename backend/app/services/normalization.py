import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
PHONE_SEPARATORS = re.compile(r"[\s.()\-/]+")


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split())


def fold_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", normalize_text(value))
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).casefold()


def normalize_phone(value: str) -> str:
    normalized = normalize_text(value)
    international = normalized.startswith("+") or normalized.startswith("00")
    if normalized.startswith("+"):
        normalized = normalized[1:]
    elif normalized.startswith("00"):
        normalized = normalized[2:]
    digits = PHONE_SEPARATORS.sub("", normalized)
    if not digits.isdigit() or not 7 <= len(digits) <= 15:
        raise ValueError("Numéro de téléphone invalide")
    return f"+{digits}" if international else digits


def canonicalize_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL HTTP(S) absolue requise")
    host = parsed.hostname.lower().rstrip(".")
    port = parsed.port
    netloc = host
    if port and not (
        (parsed.scheme.lower() == "http" and port == 80)
        or (parsed.scheme.lower() == "https" and port == 443)
    ):
        netloc = f"{host}:{port}"
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS
        )
    )
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, query, ""))
