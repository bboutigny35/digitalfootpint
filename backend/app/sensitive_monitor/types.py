import enum


class SensitiveCategory(str, enum.Enum):
    NIR = "nir"
    PAYMENT_CARD = "payment_card"
    IBAN = "iban"
    PHONE = "phone"
    POSTAL_ADDRESS = "postal_address"
    ID_DOCUMENT = "id_document"


class CheckStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    NEEDS_REVIEW = "needs_review"
    FALSE_POSITIVE = "false_positive"
