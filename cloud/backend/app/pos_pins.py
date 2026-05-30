"""POS waiter / cash-register PIN hashing (stored in `pin` columns as bcrypt)."""

from .security import get_password_hash, verify_password

_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def is_pin_hash(value: str | None) -> bool:
    if not value:
        return False
    return value.startswith(_BCRYPT_PREFIXES) and len(value) > 20


def hash_pos_pin(plain: str) -> str:
    return get_password_hash(plain)


def verify_pos_pin(plain: str, stored: str | None) -> bool:
    if not stored:
        return False
    if is_pin_hash(stored):
        try:
            return verify_password(plain, stored)
        except Exception:
            return False
    return plain == stored


def apply_pos_pin_value(entity, pin_input: str | None, *, default_plain: str = "0000") -> None:
    """Set entity.pin from admin plaintext, existing hash, or keep unchanged when empty."""
    raw = (pin_input or "").strip()
    if raw:
        entity.pin = hash_pos_pin(raw) if not is_pin_hash(raw) else raw
        return
    current = (getattr(entity, "pin", None) or "").strip()
    if current:
        return
    entity.pin = hash_pos_pin(default_plain)
