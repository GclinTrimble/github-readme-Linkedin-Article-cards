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


def _parse_linkedin(value: str):
    """Parse a URL and confirm it is a well-formed linkedin.com https URL.

    Returns the parsed result, or None if the scheme/host/port/credentials are invalid.
    """
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return None
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"linkedin.com", "www.linkedin.com"}:
        return None
    if parsed.port not in (None, 443):
        return None
    return parsed


def validate_linkedin_url(value: str) -> str:
    """Normalize and validate a LinkedIn article/post URL.

    Returns a safe https://www.linkedin.com URL, or "" if invalid.
    """
    parsed = _parse_linkedin(value)
    if parsed is None:
        return ""
    if not (parsed.path.startswith("/pulse/") or parsed.path.startswith("/posts/")):
        return ""
    safe_url = f"https://www.linkedin.com{parsed.path}"
    if parsed.query:
        safe_url += f"?{parsed.query}"
    return safe_url


_PROFILE_ARTICLES_PATH = re.compile(r"^/in/[^/]+/recent-activity/articles/?$")


def validate_linkedin_profile_url(value: str) -> str:
    """Normalize and validate a LinkedIn recent-activity/articles profile URL.

    Returns a safe https://www.linkedin.com/in/<vanity>/recent-activity/articles/ URL,
    or "" if invalid.
    """
    parsed = _parse_linkedin(value)
    if parsed is None:
        return ""
    if not _PROFILE_ARTICLES_PATH.match(parsed.path):
        return ""
    path = parsed.path if parsed.path.endswith("/") else f"{parsed.path}/"
    return f"https://www.linkedin.com{path}"


def validate_url_list(value: str | None, max_items: int) -> list[str]:
    """Parse a comma-separated list of LinkedIn article/post URLs.

    Each item is normalized via validate_linkedin_url; invalid items are dropped,
    duplicates removed (order preserved), and the result capped to max_items.
    """
    if not value:
        return []
    result: list[str] = []
    for item in value.split(","):
        normalized = validate_linkedin_url(item.strip())
        if normalized and normalized not in result:
            result.append(normalized)
        if len(result) >= max_items:
            break
    return result


def validate_float(value: str | None, default: float, min_value: float, max_value: float) -> float:
    """Parse a float and clamp it to [min_value, max_value], falling back to default."""
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(min(number, max_value), min_value)
