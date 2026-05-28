from __future__ import annotations

import base64
import html
import re
import textwrap
from urllib.parse import urlparse
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)

# Cap embedded images to keep the SVG payload reasonable.
MAX_IMAGE_BYTES = 3 * 1024 * 1024


def _build_request(url: str) -> Request:
    req = Request(url)
    req.add_header("User-Agent", USER_AGENT)
    return req


def extract_meta_tags(content: str) -> dict[str, str]:
    meta_pattern = re.compile(
        r"<meta[^>]+(?:property|name)=[\"']([^\"']+)[\"'][^>]+content=[\"']([^\"']*)[\"'][^>]*>",
        re.IGNORECASE,
    )
    tags: dict[str, str] = {}
    for key, value in meta_pattern.findall(content):
        tags[key.lower()] = html.unescape(value.strip())
    return tags


def extract_likes(content: str) -> str:
    match = re.search(
        r'"(?:numLikes|likesCount|reactionCount|socialDetailCount)"\s*:\s*([0-9]+)',
        content,
        re.IGNORECASE,
    )
    if match:
        return f"{int(match.group(1)):,} likes"

    text_match = re.search(
        r"([0-9][0-9,\.]*)\s+(?:likes|reactions)",
        content,
        re.IGNORECASE,
    )
    if text_match:
        return f"{text_match.group(1)} likes"
    return ""


def trim_lines(value: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(value, width=max(width, 1)) if value else []
    if len(lines) > max_lines and max_lines > 0:
        lines[max_lines - 1] = lines[max_lines - 1].rstrip(" .") + "…"
    return lines[:max_lines]


def fetch_article_metadata(article_path_query: str) -> dict[str, str]:
    req = _build_request(f"https://www.linkedin.com{article_path_query}")
    with urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8", errors="replace")

    tags = extract_meta_tags(body)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    title = tags.get("og:title") or (
        html.unescape(title_match.group(1)).strip() if title_match else ""
    )
    description = tags.get("og:description") or tags.get("description") or ""
    image = tags.get("og:image") or ""
    likes = extract_likes(body)
    return {
        "title": title,
        "description": description,
        "image": image,
        "likes": likes,
    }


def data_uri_from_url(url: str) -> str:
    """Fetch an image over https and return a base64 data URI.

    Returns "" on any failure (invalid scheme, timeout, oversized payload, etc.)
    so the caller can fall back to a placeholder. Embedding the image inline is
    required because GitHub's image proxy strips external <image href> targets.
    """
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return ""
    try:
        with urlopen(_build_request(url), timeout=10) as response:
            data = response.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                return ""
            mime_type = response.headers.get("Content-Type", "image/jpeg")
    except Exception:
        return ""
    mime_type = mime_type.split(";", 1)[0].strip().lower()
    if not mime_type.startswith("image/"):
        return ""
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
