from __future__ import annotations

import html
import re
import textwrap
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Flask, Response, request

app = Flask(__name__)


def _get_int_arg(name: str, default: int, min_value: int, max_value: int) -> int:
    value = request.args.get(name, str(default))
    try:
        number = int(value)
    except ValueError:
        return default
    return max(min(number, max_value), min_value)


def _normalize_and_validate_linkedin_article_url(value: str) -> str:
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


def _extract_meta_tags(content: str) -> dict[str, str]:
    meta_pattern = re.compile(
        r"<meta[^>]+(?:property|name)=[\"']([^\"']+)[\"'][^>]+content=[\"']([^\"']*)[\"'][^>]*>",
        re.IGNORECASE,
    )
    tags: dict[str, str] = {}
    for key, value in meta_pattern.findall(content):
        tags[key.lower()] = html.unescape(value.strip())
    return tags


def _extract_likes(content: str) -> str:
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


def _trim_lines(value: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(value, width=max(width, 1)) if value else []
    if len(lines) > max_lines and max_lines > 0:
        lines[max_lines - 1] = lines[max_lines - 1].rstrip(" .") + "…"
    return lines[:max_lines]


def _fetch_article_metadata(article_path_query: str) -> dict[str, str]:
    req = Request(f"https://www.linkedin.com{article_path_query}")
    req.add_header(
        "User-Agent",
        (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        ),
    )
    with urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8", errors="replace")

    tags = _extract_meta_tags(body)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    title = tags.get("og:title") or (html.unescape(title_match.group(1)).strip() if title_match else "")
    description = tags.get("og:description") or tags.get("description") or ""
    image = tags.get("og:image") or ""
    likes = _extract_likes(body)
    return {
        "title": title,
        "description": description,
        "image": image,
        "likes": likes,
    }


def _build_svg(
    *,
    title: str,
    description: str,
    image_url: str,
    likes: str,
    width: int,
    border_radius: int,
    background_color: str,
    title_color: str,
    description_color: str,
    stats_color: str,
) -> str:
    image_height = int(width * 0.52)
    title_lines = _trim_lines(title, max(20, width // 10), 2)
    description_lines = _trim_lines(description, max(30, width // 12), 2)
    title_height = len(title_lines) * 24
    description_height = len(description_lines) * 18
    footer_height = 34 if likes else 8
    height = image_height + title_height + description_height + footer_height + 26

    title_text = "".join(
        f'<text x="16" y="{image_height + 30 + (i * 24)}" fill="{html.escape(title_color)}" '
        f'font-family="Segoe UI, Roboto, sans-serif" font-size="20" font-weight="600">{html.escape(line)}</text>'
        for i, line in enumerate(title_lines)
    )

    description_start_y = image_height + 34 + title_height
    description_text = "".join(
        f'<text x="16" y="{description_start_y + (i * 18)}" fill="{html.escape(description_color)}" '
        f'font-family="Segoe UI, Roboto, sans-serif" font-size="14">{html.escape(line)}</text>'
        for i, line in enumerate(description_lines)
    )

    likes_y = image_height + title_height + description_height + 26
    likes_text = (
        f'<text x="16" y="{likes_y}" fill="{html.escape(stats_color)}" '
        f'font-family="Segoe UI, Roboto, sans-serif" font-size="13">{html.escape(likes)}</text>'
        if likes
        else ""
    )

    image_tag = (
        f'<image href="{html.escape(image_url)}" x="0" y="0" width="{width}" height="{image_height}" '
        f'preserveAspectRatio="xMidYMid slice" />'
        if image_url
        else (
            f'<rect x="0" y="0" width="{width}" height="{image_height}" fill="#2f81f7" />'
            f'<text x="{width / 2}" y="{image_height / 2}" text-anchor="middle" fill="#ffffff" '
            'font-family="Segoe UI, Roboto, sans-serif" font-size="18" font-weight="600">LinkedIn Article</text>'
        )
    )

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LinkedIn article card">'
        f'<defs><clipPath id="clip"><rect x="0" y="0" width="{width}" height="{height}" '
        f'rx="{border_radius}" ry="{border_radius}" /></clipPath></defs>'
        f'<g clip-path="url(#clip)"><rect width="{width}" height="{height}" fill="{html.escape(background_color)}" />'
        f"{image_tag}{title_text}{description_text}{likes_text}</g></svg>"
    )


@app.get("/")
def home() -> str:
    return (
        "GitHub Readme LinkedIn Article Cards. "
        "Use /card.svg?url=<linkedin-article-url> to generate a card."
    )


@app.get("/card.svg")
def card() -> Response:
    requested_url = request.args.get("url", "").strip()
    if not requested_url:
        return Response("Missing required 'url' query parameter", status=400)
    article_url = _normalize_and_validate_linkedin_article_url(requested_url)
    if not article_url:
        return Response("The 'url' must be a valid LinkedIn URL", status=400)

    width = _get_int_arg("width", default=420, min_value=220, max_value=1200)
    border_radius = _get_int_arg("border_radius", default=10, min_value=0, max_value=40)
    background_color = request.args.get("background_color", "#0d1117")
    title_color = request.args.get("title_color", "#ffffff")
    description_color = request.args.get("description_color", "#c9d1d9")
    stats_color = request.args.get("stats_color", "#8b949e")

    title_override = request.args.get("title", "").strip()
    description_override = request.args.get("description", "").strip()
    image_override = request.args.get("image", "").strip()
    likes_override = request.args.get("likes", "").strip()

    metadata = {"title": "", "description": "", "image": "", "likes": ""}
    try:
        metadata = _fetch_article_metadata(article_url)
    except (URLError, TimeoutError, ValueError):
        pass

    title = title_override or metadata["title"] or "LinkedIn Article"
    description = description_override or metadata["description"] or "Read this article on LinkedIn."
    image_url = image_override or metadata["image"]
    likes = likes_override or metadata["likes"]

    svg = _build_svg(
        title=title,
        description=description,
        image_url=image_url,
        likes=likes,
        width=width,
        border_radius=border_radius,
        background_color=background_color,
        title_color=title_color,
        description_color=description_color,
        stats_color=stats_color,
    )

    response = Response(svg, mimetype="image/svg+xml")
    response.headers["Content-Type"] = "image/svg+xml; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
