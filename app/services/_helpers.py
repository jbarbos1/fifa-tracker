"""Small shared helpers for finance services."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def decimal_or_none(value) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def quantize_or_none(value, places: str = "0.0001") -> Decimal | None:
    number = decimal_or_none(value)
    if number is None:
        return None
    return number.quantize(Decimal(places))


def ratio_or_none(numerator, denominator) -> Decimal | None:
    num = decimal_or_none(numerator)
    den = decimal_or_none(denominator)
    if num is None or den in (None, 0):
        return None
    return num / den


def set_known_attrs(model, values: dict) -> None:
    columns = model.__table__.columns.keys()
    for key, value in values.items():
        if key in columns:
            setattr(model, key, value)
