import re
import unicodedata


class SensitiveValueError(ValueError):
    pass


def digits_only(value: str) -> str:
    return re.sub(r"[\s.-]", "", value)


def validate_nir(value: str) -> str:
    normalized = digits_only(value).upper()
    if not re.fullmatch(r"[12]\d{4}(?:\d{2}|2[AB])\d{6}\d{2}", normalized):
        raise SensitiveValueError("Format NIR invalide")
    body, supplied_key = normalized[:13], int(normalized[13:])
    adjusted = body
    if "A" in body:
        number = int(body.replace("A", "0")) - 1_000_000
    elif "B" in body:
        number = int(body.replace("B", "0")) - 2_000_000
    else:
        number = int(adjusted)
    expected_key = 97 - (number % 97)
    if supplied_key != expected_key:
        raise SensitiveValueError("Clé NIR invalide")
    return normalized


def validate_pan(value: str) -> str:
    normalized = re.sub(r"[ -]", "", value)
    if not normalized.isdigit() or not 12 <= len(normalized) <= 19:
        raise SensitiveValueError("Format de carte invalide")
    checksum = 0
    parity = len(normalized) % 2
    for index, character in enumerate(normalized):
        digit = int(character)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    if checksum % 10:
        raise SensitiveValueError("Clé de Luhn invalide")
    return normalized


def validate_iban(value: str) -> str:
    normalized = re.sub(r"\s", "", value).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", normalized):
        raise SensitiveValueError("Format IBAN invalide")
    rearranged = normalized[4:] + normalized[:4]
    numeric = "".join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
    if int(numeric) % 97 != 1:
        raise SensitiveValueError("Clé IBAN invalide")
    return normalized


def validate_phone(value: str) -> str:
    normalized = re.sub(r"[\s().-]", "", value)
    if normalized.startswith("00"):
        normalized = "+" + normalized[2:]
    if not re.fullmatch(r"\+?[1-9]\d{7,14}", normalized):
        raise SensitiveValueError("Numéro de téléphone invalide")
    return normalized


def validate_address(value: str) -> str:
    normalized = " ".join(value.split())
    if not 8 <= len(normalized) <= 300 or "\n" in normalized or "\r" in normalized:
        raise SensitiveValueError("Adresse postale invalide")
    return normalized


def validate_id_document(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    if not re.fullmatch(r"[A-Z0-9 -]{5,40}", normalized):
        raise SensitiveValueError("Numéro de pièce invalide")
    return normalized
