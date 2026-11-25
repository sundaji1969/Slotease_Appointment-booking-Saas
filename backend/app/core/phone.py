"""Indian mobile numbers normalised to E.164 (+91XXXXXXXXXX)."""

import re

_INDIAN_MOBILE = re.compile(r"^[6-9]\d{9}$")


def normalize_indian_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not _INDIAN_MOBILE.match(digits):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return "+91" + digits
