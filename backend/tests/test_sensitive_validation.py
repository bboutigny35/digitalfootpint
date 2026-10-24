import pytest

from app.sensitive_monitor.privacy import mask_value
from app.sensitive_monitor.types import SensitiveCategory
from app.sensitive_monitor.validation import (
    SensitiveValueError,
    validate_address,
    validate_iban,
    validate_nir,
    validate_pan,
    validate_phone,
)


def synthetic_nir(body: str) -> str:
    adjusted = int(body.replace("A", "0").replace("B", "0"))
    if "A" in body:
        adjusted -= 1_000_000
    if "B" in body:
        adjusted -= 2_000_000
    return f"{body}{97 - adjusted % 97:02d}"


def test_nir_format_and_control_key() -> None:
    value = synthetic_nir("1000199999999")
    assert validate_nir(value) == value
    with pytest.raises(SensitiveValueError, match="Clé NIR"):
        validate_nir(value[:-2] + "00")
    with pytest.raises(SensitiveValueError, match="Format NIR"):
        validate_nir("123")


def test_nir_corsica_control_key() -> None:
    value = synthetic_nir("200012A001001")
    assert validate_nir(value) == value


def test_luhn_is_local_validation_only() -> None:
    assert validate_pan("4242 4242 4242 4242") == "4242424242424242"
    with pytest.raises(SensitiveValueError):
        validate_pan("4242 4242 4242 4241")


def test_iban_phone_and_address_validation() -> None:
    assert validate_iban("GB82 WEST 1234 5698 7654 32") == "GB82WEST12345698765432"
    assert validate_phone("+33 6 12 34 56 78") == "+33612345678"
    assert validate_address("  10 rue Exemple  75000 Paris ") == "10 rue Exemple 75000 Paris"
    with pytest.raises(SensitiveValueError):
        validate_iban("FR00INVALID")


def test_masking_never_returns_complete_value() -> None:
    values = {
        SensitiveCategory.NIR: synthetic_nir("1000199999999"),
        SensitiveCategory.PAYMENT_CARD: "4242424242424242",
        SensitiveCategory.IBAN: "GB82WEST12345698765432",
        SensitiveCategory.PHONE: "+33612345678",
        SensitiveCategory.POSTAL_ADDRESS: "10 rue Exemple 75000 Paris",
        SensitiveCategory.ID_DOCUMENT: "TESTDOCUMENT123",
    }
    for category, value in values.items():
        assert value not in mask_value(category, value)
