"""Entry point for the reusable GitHub Action.

Reads inputs from ``INPUT_*`` environment variables (set by ``action.yml``),
renders the LinkedIn card SVG variants into the consumer repo's output dir, and
rewrites the consumer README between ``<!-- {TAG}-START -->`` / ``<!-- {TAG}-END -->``
markers with a ``<picture>`` embed linking to the profile in a new tab.

When ``INPUT_CONFIG_FILE`` points at a committed JSON config, that file is
authoritative (it can carry ``overrides`` and ``variants``) and the inline style
inputs are ignored — this is the path that stays correct when the runner is
authwalled by LinkedIn.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ACTION_ROOT))

from app import app, build_cards_svg  # noqa: E402
from scripts.generate_cards import STYLE_KEYS, resolve_article_urls  # noqa: E402

# Consumer files (README, config, output dir) live in the workspace, not the
# action checkout.
WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE") or os.getcwd())

DEFAULT_VARIANT_NAME = "linkedin-cards"


def _input(name: str, default: str = "") -> str:
    return os.environ.get(f"INPUT_{name.upper()}", "").strip() or default


def config_from_inputs() -> dict:
    """Build a config dict from INPUT_* env vars, or load the authoritative config_file."""
    config_file = _input("config_file")
    if config_file:
        path = (WORKSPACE / config_file).resolve()
        return json.loads(path.read_text(encoding="utf-8"))

    config: dict = {
        "profile_url": _input("profile_url"),
        "urls": [u.strip() for u in _input("urls").split(",") if u.strip()],
        "max": int(_input("max", "4")),
        "columns": int(_input("columns", "2")),
    }
    style = {key: _input(key) for key in STYLE_KEYS if _input(key)}
    config.update(style)
    # Single default variant from the inline style inputs; consumers wanting
    # dark/light themes provide a config_file with explicit `variants`.
    config["variants"] = [{"name": DEFAULT_VARIANT_NAME, **style}]
    return config


def _coerce_style(style: dict) -> dict:
    """Cast string style inputs to the numeric types build_cards_svg expects."""
    int_keys = ("width", "border_radius", "max_title_lines", "max_description_lines")
    out = dict(style)
    for key in int_keys:
        if key in out:
            out[key] = int(out[key])
    if "image_ratio" in out:
        out["image_ratio"] = float(out["image_ratio"])
    return out


def render_variants(config: dict, output_dir: Path) -> list[str]:
    """Render each variant SVG into output_dir; return the variant names written."""
    article_urls = resolve_article_urls(config)
    if not article_urls:
        raise SystemExit("No valid article URLs resolved from inputs/config.")

    variants = config.get("variants") or [{"name": DEFAULT_VARIANT_NAME}]
    overrides = config.get("overrides") or {}
    columns = max(1, min(int(config.get("columns", 2)), 4))
    base_style = {key: config[key] for key in STYLE_KEYS if key in config}

    output_dir.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    with app.app_context():
        for variant in variants:
            name = variant["name"]
            style = _coerce_style({**base_style, **{k: v for k, v in variant.items() if k in STYLE_KEYS}})
            svg = build_cards_svg(article_urls, columns=columns, overrides=overrides, **style)
            (output_dir / f"{name}.svg").write_text(svg.rstrip("\n") + "\n", encoding="utf-8")
            names.append(name)
            print(f"Wrote {output_dir / f'{name}.svg'} ({len(article_urls)} tiles)")
    return names


def build_embed(variant_names: list[str], output_dir: str, profile_url: str) -> str:
    """Build the README embed: a profile link (new tab) wrapping a themed <picture>."""
    href = f' href="{profile_url}"' if profile_url else ""
    dark = next((n for n in variant_names if "dark" in n), variant_names[0])
    light = next((n for n in variant_names if "light" in n), variant_names[-1])
    if dark != light:
        media = (
            f'  <picture>\n'
            f'    <source media="(prefers-color-scheme: dark)" srcset="./{output_dir}/{dark}.svg" />\n'
            f'    <img alt="LinkedIn articles" src="./{output_dir}/{light}.svg" />\n'
            f'  </picture>'
        )
    else:
        media = f'  <img alt="LinkedIn articles" src="./{output_dir}/{light}.svg" />'
    return f'<a{href} target="_blank" rel="noopener noreferrer">\n{media}\n</a>'


def replace_between_markers(text: str, tag: str, block: str) -> str | None:
    """Replace content between the first ``<!-- {tag}-START -->`` / ``<!-- {tag}-END -->`` pair.

    Only the first pair is rewritten (``count=1``) so a documentation example of
    the markers elsewhere in the file — e.g. inside a fenced code block — is left
    untouched. Returns the new text, or ``None`` if the markers are not present.
    """
    start = f"<!-- {tag}-START -->"
    end = f"<!-- {tag}-END -->"
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.DOTALL
    )
    if not pattern.search(text):
        return None
    return pattern.sub(f"{start}\n{block}\n{end}", text, count=1)


def main() -> int:
    config = config_from_inputs()
    output_dir_name = _input("output_dir", "assets")
    tag = _input("comment_tag_name", "LINKEDIN-CARDS")
    readme_name = _input("readme", "README.md")
    profile_url = config.get("profile_url", "") or _input("profile_url")

    variant_names = render_variants(config, WORKSPACE / output_dir_name)

    readme_path = WORKSPACE / readme_name
    if readme_path.exists():
        block = build_embed(variant_names, output_dir_name, profile_url)
        updated = replace_between_markers(readme_path.read_text(encoding="utf-8"), tag, block)
        if updated is None:
            print(
                f"README markers <!-- {tag}-START --> / <!-- {tag}-END --> not found; "
                f"skipped README update."
            )
        else:
            readme_path.write_text(updated, encoding="utf-8")
            print(f"Updated {readme_path} between {tag} markers.")
    else:
        print(f"No README at {readme_path}; skipped README update.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
