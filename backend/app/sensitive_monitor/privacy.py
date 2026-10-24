import hashlib
import hmac

from app.core.config import get_settings
from app.sensitive_monitor.types import SensitiveCategory


def fingerprint(category: SensitiveCategory, normalized_value: str) -> str:
    message = f"sensitive-monitor:v1:{category.value}:{normalized_value}".encode()
    return hmac.new(get_settings().secret_key.encode(), message, hashlib.sha256).hexdigest()


def mask_value(category: SensitiveCategory, normalized_value: str) -> str:
    if category == SensitiveCategory.NIR:
        return f"{normalized_value[0]} ** ** ***** *** **"
    if category == SensitiveCategory.PAYMENT_CARD:
        return f"•••• •••• •••• {normalized_value[-4:]}"
    if category == SensitiveCategory.IBAN:
        return f"{normalized_value[:4]} •••• •••• •••• {normalized_value[-4:]}"
    if category == SensitiveCategory.PHONE:
        return f"••••••{normalized_value[-4:]}"
    if category == SensitiveCategory.POSTAL_ADDRESS:
        return "Adresse postale masquée"
    return f"••••••{normalized_value[-3:]}"
