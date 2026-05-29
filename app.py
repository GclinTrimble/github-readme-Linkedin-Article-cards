from __future__ import annotations

from urllib.error import URLError

from flask import Flask, Response, render_template, request

from card.utils import (
    data_uri_from_url,
    fetch_article_metadata,
    fetch_article_urls,
    trim_lines,
)
from card.validate import (
    validate_color,
    validate_float,
    validate_int,
    validate_linkedin_profile_url,
    validate_linkedin_url,
    validate_url_list,
)

app = Flask(__name__, template_folder="card/templates")
# Escape all rendered values, including inside the SVG template.
app.jinja_env.autoescape = True

DEFAULT_FONT_FAMILY = "Segoe UI, Roboto, sans-serif"

TITLE_FONT_SIZE = 20
TITLE_LINE_HEIGHT = 24
DESCRIPTION_FONT_SIZE = 14
DESCRIPTION_LINE_HEIGHT = 18
STATS_FONT_SIZE = 13


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
    article_url = validate_linkedin_url(requested_url)
    if not article_url:
        return Response("The 'url' must be a valid LinkedIn URL", status=400)

    width = validate_int(request.args.get("width"), default=420, min_value=220, max_value=1200)
    border_radius = validate_int(
        request.args.get("border_radius"), default=10, min_value=0, max_value=40
    )
    max_title_lines = validate_int(
        request.args.get("max_title_lines"), default=2, min_value=1, max_value=4
    )
    max_description_lines = validate_int(
        request.args.get("max_description_lines"), default=2, min_value=0, max_value=5
    )
    image_ratio = validate_float(
        request.args.get("image_ratio"), default=0.52, min_value=0.0, max_value=1.0
    )

    background_color = validate_color(request.args.get("background_color"), "#0d1117")
    title_color = validate_color(request.args.get("title_color"), "#ffffff")
    description_color = validate_color(request.args.get("description_color"), "#c9d1d9")
    stats_color = validate_color(request.args.get("stats_color"), "#8b949e")
    accent_color = validate_color(request.args.get("accent_color"), "#2f81f7")
    font_family = request.args.get("font_family", "").strip() or DEFAULT_FONT_FAMILY

    title_override = request.args.get("title", "").strip()
    description_override = request.args.get("description", "").strip()
    image_override = request.args.get("image", "").strip()
    likes_override = request.args.get("likes", "").strip()

    metadata = {"title": "", "description": "", "image": "", "likes": ""}
    try:
        metadata = fetch_article_metadata(article_url)
    except (URLError, TimeoutError, ValueError):
        pass

    title = title_override or metadata["title"] or "LinkedIn Article"
    description = (
        description_override or metadata["description"] or "Read this article on LinkedIn."
    )
    image_source = image_override or metadata["image"]
    likes = likes_override or metadata["likes"]

    image_href = data_uri_from_url(image_source)

    svg = _render_card(
        title=title,
        description=description,
        image_href=image_href,
        likes=likes,
        width=width,
        border_radius=border_radius,
        background_color=background_color,
        title_color=title_color,
        description_color=description_color,
        stats_color=stats_color,
        accent_color=accent_color,
        font_family=font_family,
        image_ratio=image_ratio,
        max_title_lines=max_title_lines,
        max_description_lines=max_description_lines,
    )

    response = Response(svg, mimetype="image/svg+xml")
    response.headers["Content-Type"] = "image/svg+xml; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


GRID_GAP = 16
MAX_CARDS = 6


@app.get("/cards.svg")
def cards() -> Response:
    profile_arg = request.args.get("url", "").strip()
    profile_url = validate_linkedin_profile_url(profile_arg) if profile_arg else ""

    max_cards = validate_int(request.args.get("max"), default=4, min_value=1, max_value=MAX_CARDS)
    columns = validate_int(request.args.get("columns"), default=2, min_value=1, max_value=4)
    fallback_urls = validate_url_list(request.args.get("urls"), max_items=MAX_CARDS)

    if not profile_url and not fallback_urls:
        return Response("Provide a 'url' (recent-activity) or 'urls' list", status=400)

    article_urls: list[str] = []
    if profile_url:
        try:
            article_urls = fetch_article_urls(profile_url)
        except (URLError, TimeoutError, ValueError):
            article_urls = []
    if not article_urls:
        article_urls = fallback_urls
    article_urls = article_urls[:max_cards]

    if not article_urls:
        return Response("No LinkedIn articles could be resolved", status=400)

    width = validate_int(request.args.get("width"), default=420, min_value=220, max_value=1200)
    border_radius = validate_int(
        request.args.get("border_radius"), default=10, min_value=0, max_value=40
    )
    max_title_lines = validate_int(
        request.args.get("max_title_lines"), default=2, min_value=1, max_value=4
    )
    max_description_lines = validate_int(
        request.args.get("max_description_lines"), default=2, min_value=0, max_value=5
    )
    image_ratio = validate_float(
        request.args.get("image_ratio"), default=0.52, min_value=0.0, max_value=1.0
    )
    background_color = validate_color(request.args.get("background_color"), "#0d1117")
    title_color = validate_color(request.args.get("title_color"), "#ffffff")
    description_color = validate_color(request.args.get("description_color"), "#c9d1d9")
    stats_color = validate_color(request.args.get("stats_color"), "#8b949e")
    accent_color = validate_color(request.args.get("accent_color"), "#2f81f7")
    font_family = request.args.get("font_family", "").strip() or DEFAULT_FONT_FAMILY

    svg = build_cards_svg(
        article_urls,
        width=width,
        border_radius=border_radius,
        max_title_lines=max_title_lines,
        max_description_lines=max_description_lines,
        image_ratio=image_ratio,
        background_color=background_color,
        title_color=title_color,
        description_color=description_color,
        stats_color=stats_color,
        accent_color=accent_color,
        font_family=font_family,
        columns=columns,
    )
    response = Response(svg, mimetype="image/svg+xml")
    response.headers["Content-Type"] = "image/svg+xml; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


def build_cards_svg(
    article_urls: list[str],
    *,
    width: int = 420,
    border_radius: int = 10,
    max_title_lines: int = 2,
    max_description_lines: int = 2,
    image_ratio: float = 0.52,
    background_color: str = "#0d1117",
    title_color: str = "#ffffff",
    description_color: str = "#c9d1d9",
    stats_color: str = "#8b949e",
    accent_color: str = "#2f81f7",
    font_family: str = DEFAULT_FONT_FAMILY,
    columns: int = 2,
    overrides: dict[str, dict[str, str]] | None = None,
) -> str:
    """Render a grid SVG for the given article URLs.

    ``overrides`` maps an article URL to manual metadata (title/description/image/likes)
    that replaces the live fetch for that tile — used when LinkedIn blocks the caller's
    network (e.g. CI runners) so the static render stays correct.
    """
    overrides = overrides or {}
    image_height = int(width * image_ratio)

    contents = []
    for article_url in article_urls:
        override = overrides.get(article_url, {})
        metadata = {"title": "", "description": "", "image": "", "likes": ""}
        # An override entry is authoritative: skip the live fetch entirely so the
        # render stays correct (and fast) even when LinkedIn blocks the caller.
        if not override:
            try:
                metadata = fetch_article_metadata(article_url)
            except (URLError, TimeoutError, ValueError):
                pass
        title = override.get("title") or metadata["title"] or "LinkedIn Article"
        description = (
            override.get("description") or metadata["description"] or "Read this article on LinkedIn."
        )
        image_source = override.get("image") or metadata["image"]
        likes = override.get("likes") or metadata["likes"]
        contents.append(
            {
                "title_lines": trim_lines(title, max(20, width // 10), max_title_lines),
                "description_lines": trim_lines(
                    description, max(30, width // 12), max_description_lines
                ),
                "image_href": data_uri_from_url(image_source),
                "likes": likes,
            }
        )

    has_likes = any(c["likes"] for c in contents)
    footer_height = 34 if has_likes else 8
    title_block = max_title_lines * TITLE_LINE_HEIGHT
    description_block = max_description_lines * DESCRIPTION_LINE_HEIGHT
    tile_height = image_height + title_block + description_block + footer_height + 26

    tiles = []
    for index, content in enumerate(contents):
        row, col = divmod(index, columns)
        actual_title_block = len(content["title_lines"]) * TITLE_LINE_HEIGHT
        actual_description_block = len(content["description_lines"]) * DESCRIPTION_LINE_HEIGHT
        tiles.append(
            {
                "x": col * (width + GRID_GAP),
                "y": row * (tile_height + GRID_GAP),
                "clip_id": f"card-clip-{index}",
                "width": width,
                "height": tile_height,
                "border_radius": border_radius,
                "background_color": background_color,
                "image_href": content["image_href"],
                "image_height": image_height,
                "accent_color": accent_color,
                "font_family": font_family,
                "placeholder_text": "LinkedIn Article",
                "title_lines": content["title_lines"],
                "title_color": title_color,
                "title_base_y": image_height + 30,
                "title_line_height": TITLE_LINE_HEIGHT,
                "title_font_size": TITLE_FONT_SIZE,
                "description_lines": content["description_lines"],
                "description_color": description_color,
                "description_base_y": image_height + 34 + actual_title_block,
                "description_line_height": DESCRIPTION_LINE_HEIGHT,
                "description_font_size": DESCRIPTION_FONT_SIZE,
                "stats_text": content["likes"],
                "stats_color": stats_color,
                "stats_y": image_height + actual_title_block + actual_description_block + 26,
                "stats_font_size": STATS_FONT_SIZE,
            }
        )

    used_columns = min(columns, len(tiles))
    rows = -(-len(tiles) // columns)
    canvas_width = used_columns * width + (used_columns - 1) * GRID_GAP
    canvas_height = rows * tile_height + (rows - 1) * GRID_GAP

    return render_template(
        "cards.svg",
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        tiles=tiles,
    )


def _render_card(
    *,
    title: str,
    description: str,
    image_href: str,
    likes: str,
    width: int,
    border_radius: int,
    background_color: str,
    title_color: str,
    description_color: str,
    stats_color: str,
    accent_color: str,
    font_family: str,
    image_ratio: float,
    max_title_lines: int,
    max_description_lines: int,
) -> str:
    image_height = int(width * image_ratio)
    title_lines = trim_lines(title, max(20, width // 10), max_title_lines)
    description_lines = trim_lines(description, max(30, width // 12), max_description_lines)

    title_block = len(title_lines) * TITLE_LINE_HEIGHT
    description_block = len(description_lines) * DESCRIPTION_LINE_HEIGHT
    footer_height = 34 if likes else 8
    height = image_height + title_block + description_block + footer_height + 26

    title_base_y = image_height + 30
    description_base_y = image_height + 34 + title_block
    stats_y = image_height + title_block + description_block + 26

    return render_template(
        "card.svg",
        width=width,
        height=height,
        border_radius=border_radius,
        background_color=background_color,
        font_family=font_family,
        image_href=image_href,
        image_height=image_height,
        accent_color=accent_color,
        placeholder_text="LinkedIn Article",
        title_color=title_color,
        title_lines=title_lines,
        title_base_y=title_base_y,
        title_line_height=TITLE_LINE_HEIGHT,
        title_font_size=TITLE_FONT_SIZE,
        description_color=description_color,
        description_lines=description_lines,
        description_base_y=description_base_y,
        description_line_height=DESCRIPTION_LINE_HEIGHT,
        description_font_size=DESCRIPTION_FONT_SIZE,
        stats_color=stats_color,
        stats_text=likes,
        stats_y=stats_y,
        stats_font_size=STATS_FONT_SIZE,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
