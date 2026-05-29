# GitHub Readme LinkedIn Article Cards

Generate live SVG cards for LinkedIn articles (title, description, cover image, and
likes) for use in your GitHub README. Cover images are fetched server-side and
embedded as base64 data URIs so they actually render inside GitHub (GitHub's image
proxy strips external image references from SVGs).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

## Usage

Endpoint:

`GET /card.svg?url=<linkedin-article-url>`

Example:

```text
http://127.0.0.1:5000/card.svg?url=https://www.linkedin.com/pulse/example-article
```

Only `https://www.linkedin.com/pulse/...` and `https://www.linkedin.com/posts/...`
URLs are accepted.

### Query parameters

| Parameter               | Default                     | Description                                            |
| ----------------------- | --------------------------- | ------------------------------------------------------ |
| `url`                   | _(required)_                | LinkedIn article/post URL                              |
| `title`                 | _(from metadata)_           | Manual title override                                  |
| `description`           | _(from metadata)_           | Manual description override                            |
| `image`                 | _(from metadata)_           | Manual cover image URL override (https only)           |
| `likes`                 | _(from metadata)_           | Manual likes/stats override                            |
| `width`                 | `420`                       | Card width in px (220–1200)                            |
| `border_radius`         | `10`                        | Corner radius in px (0–40)                             |
| `background_color`      | `#0d1117`                   | Card background (hex; 3/4/6/8 digits)                  |
| `title_color`           | `#ffffff`                   | Title text color (hex)                                 |
| `description_color`     | `#c9d1d9`                   | Description text color (hex)                           |
| `stats_color`           | `#8b949e`                   | Likes/stats text color (hex)                           |
| `accent_color`          | `#2f81f7`                   | Placeholder block color when no image is available     |
| `font_family`           | `Segoe UI, Roboto, sans-serif` | Font family for all text                            |
| `image_ratio`           | `0.52`                      | Cover image height as a fraction of width (0.0–1.0)    |
| `max_title_lines`       | `2`                         | Max title lines before truncation (1–4)                |
| `max_description_lines` | `2`                         | Max description lines before truncation (0–5)          |

Color values are sanitized to hex; invalid values fall back to the default.
Integer and ratio values are clamped to their valid ranges. If LinkedIn metadata
cannot be fetched (for example due to anti-bot blocks), the manual overrides above
can still be used to render a card.

## Live Examples (multiple article tiles)

<a href="https://www.linkedin.com/in/guillaume-clin/recent-activity/articles/">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/linkedin-cards-dark.svg" />
    <img alt="LinkedIn articles" src="./assets/linkedin-cards-light.svg" />
  </picture>
</a>

The grid above is rendered to static SVG files committed under [`assets/`](./assets)
and refreshed automatically — see [How the cards stay updated](#how-the-cards-stay-updated).
No server hosting is required for the README to render.

### How the cards stay updated

A scheduled GitHub Action ([`.github/workflows/update-linkedin-cards.yml`](.github/workflows/update-linkedin-cards.yml))
regenerates `assets/linkedin-cards-*.svg` daily, on manual **Run workflow**
(`workflow_dispatch`), and whenever [`cards.config.json`](./cards.config.json) changes.
It runs [`scripts/generate_cards.py`](./scripts/generate_cards.py) and commits any changes.

To change which articles appear (or their colors/layout), edit `cards.config.json`:

- `urls` — the reliable list of article URLs to render (LinkedIn authwalls anonymous
  discovery via `profile_url`, so this list is what actually gets used).
- `max` / `columns` — tile count and grid columns.
- `overrides` — optional per-URL `title`/`description`/`image`/`likes` used when the
  Action runner can't fetch LinkedIn (its IP may also be authwalled), keeping the render correct.
- `variants` — one committed SVG per entry (e.g. dark and light).

### Self-hosting the live endpoint (optional)

If you prefer per-view live rendering instead of committed assets, run the `/cards.svg`
endpoint yourself:

`GET /cards.svg?url=<recent-activity-articles-url>&urls=<fallback-list>`

```text
http://127.0.0.1:5000/cards.svg?url=https://www.linkedin.com/in/guillaume-clin/recent-activity/articles/&urls=https://www.linkedin.com/pulse/system-aoteroa-infrastructure-guillaume-clin-mqlsc,https://www.linkedin.com/pulse/connected-data-civil-construction-examination-cde-ecosystems-clin-xthyc,https://www.linkedin.com/pulse/civil-construction-terrain-aggregation-surface-data-connected-clin-oebtc&max=3&columns=3
```

The endpoint first makes a **best-effort** attempt to scrape article links from the
`recent-activity/articles/` page. LinkedIn usually serves that page behind an
anti-bot wall (HTTP 999) when fetched anonymously, so the **`urls=` list is the
reliable source** — provide a comma-separated list of `/pulse/` (or `/posts/`) URLs
and the grid will render from those whenever the scrape returns nothing.

### Additional query parameters

| Parameter | Default      | Description                                                                 |
| --------- | ------------ | --------------------------------------------------------------------------- |
| `url`     | _(optional)_ | A `…/in/<vanity>/recent-activity/articles/` URL to scrape (best-effort)     |
| `urls`    | _(optional)_ | Comma-separated list of article/post URLs used as the reliable fallback     |
| `max`     | `4`          | Maximum number of tiles to render (1–6)                                     |
| `columns` | `2`          | Number of grid columns (1–4)                                                |

At least one of `url` or `urls` is required. All of the styling parameters from the
single-card endpoint (`width` is the per-tile width, plus `border_radius`,
`image_ratio`, colors, `font_family`, `max_title_lines`, `max_description_lines`)
apply to every tile.

When self-hosting, dark / light variants work the same way as the single card —
point each themed embed at your running endpoint:

```md
[![LinkedIn articles](https://<your-host>/cards.svg?urls=<pulse-1>,<pulse-2>,<pulse-3>&max=3&columns=3&background_color=0d1117&title_color=ffffff#gh-dark-mode-only)](https://www.linkedin.com/in/guillaume-clin/recent-activity/articles/)
[![LinkedIn articles](https://<your-host>/cards.svg?urls=<pulse-1>,<pulse-2>,<pulse-3>&max=3&columns=3&background_color=ffffff&title_color=24292f&description_color=57606a#gh-light-mode-only)](https://www.linkedin.com/in/guillaume-clin/recent-activity/articles/)
```

## Light / dark mode

The card has no built-in theme switching, but GitHub renders different images per
theme via the `#gh-dark-mode-only` / `#gh-light-mode-only` URL fragments. Provide
two color variants and GitHub will show the one matching the viewer's theme:

```md
[![LinkedIn article](https://<your-host>/card.svg?url=https://www.linkedin.com/pulse/example&background_color=0d1117&title_color=ffffff#gh-dark-mode-only)](https://www.linkedin.com/pulse/example)
[![LinkedIn article](https://<your-host>/card.svg?url=https://www.linkedin.com/pulse/example&background_color=ffffff&title_color=24292f&description_color=57606a#gh-light-mode-only)](https://www.linkedin.com/pulse/example)
```

## Tests

```bash
pip install -r requirements.txt
python -m pytest
```
