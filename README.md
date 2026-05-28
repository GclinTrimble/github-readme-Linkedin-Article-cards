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
