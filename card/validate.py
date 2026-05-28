from __future__ import annotations

import re
from urllib.parse import urlparse


def validate_int(value: str | None, default: int, min_value: int, max_value: int) -> int:
    """Parse an int and clamp it to [min_value, max_value], falling back to default."""
    if value is None:
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(min(number, max_value), min_value)


def validate_color(value: str | None, default: str) -> str:
    """Sanitize a color to '#' + 3/4/6/8 hex digits, otherwise return the default."""
    if not value:
        return default
    hex_digits = re.sub(r"[^a-fA-F0-9]", "", value)
    if len(hex_digits) not in (3, 4, 6, 8):
        return default
    return f"#{hex_digits}"


def validate_linkedin_url(value: str) -> str:
    """Normalize and validate a LinkedIn article/post URL.

    Returns a safe https://www.linkedin.com URL, or "" if invalid.
    """
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return ""
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"linkedin.com", "www.linkedin.com"}:
        return ""
    if parsed.port not in (None, 443):
        return ""
    if not (parsed.path.startswith("/pulse/") or parsed.path.startswith("/posts/")):
        return ""
    safe_url = f"https://www.linkedin.com{parsed.path}"
    if parsed.query:
        safe_url += f"?{parsed.query}"
    return safe_url


def validate_float(value: str | None, default: float, min_value: float, max_value: float) -> float:
    """Parse a float and clamp it to [min_value, max_value], falling back to default."""
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(min(number, max_value), min_value)
