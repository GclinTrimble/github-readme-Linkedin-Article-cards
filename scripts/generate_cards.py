"""Render the LinkedIn article grid to static SVG files.

Run by the update-linkedin-cards GitHub Action (and locally) so the README can
embed committed assets instead of a live service. Reuses the same rendering and
URL-resolution logic as the /cards.svg endpoint.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import URLError

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import MAX_CARDS, app, build_cards_svg  # noqa: E402
from card.utils import fetch_article_urls  # noqa: E402
from card.validate import validate_linkedin_profile_url, validate_url_list  # noqa: E402

CONFIG_PATH = REPO_ROOT / "cards.config.json"
ASSETS_DIR = REPO_ROOT / "assets"

STYLE_KEYS = (
    "width",
    "border_radius",
    "max_title_lines",
    "max_description_lines",
    "image_ratio",
    "background_color",
    "title_color",
    "description_color",
    "stats_color",
    "accent_color",
    "font_family",
)


def resolve_article_urls(config: dict) -> list[str]:
    max_cards = int(config.get("max", 4))
    max_cards = max(1, min(max_cards, MAX_CARDS))

    article_urls: list[str] = []
    profile_url = validate_linkedin_profile_url(config.get("profile_url", "") or "")
    if profile_url:
        try:
            article_urls = fetch_article_urls(profile_url)
        except (URLError, TimeoutError, ValueError):
            article_urls = []
    if not article_urls:
        article_urls = validate_url_list(",".join(config.get("urls", [])), max_items=MAX_CARDS)
    return article_urls[:max_cards]


def main() -> int:
    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}", file=sys.stderr)
        return 1
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    article_urls = resolve_article_urls(config)
    if not article_urls:
        print("No valid article URLs resolved from config.", file=sys.stderr)
        return 1

    variants = config.get("variants") or []
    if not variants:
        print("No 'variants' defined in config.", file=sys.stderr)
        return 1

    overrides = config.get("overrides") or {}
    columns = max(1, min(int(config.get("columns", 2)), 4))
    base_style = {key: config[key] for key in STYLE_KEYS if key in config}

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        for variant in variants:
            name = variant["name"]
            style = {**base_style}
            style.update({k: v for k, v in variant.items() if k in STYLE_KEYS})
            svg = build_cards_svg(
                article_urls,
                columns=columns,
                overrides=overrides,
                **style,
            )
            out_path = ASSETS_DIR / f"{name}.svg"
            out_path.write_text(svg.rstrip("\n") + "\n", encoding="utf-8")
            print(f"Wrote {out_path} ({len(article_urls)} tiles)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
