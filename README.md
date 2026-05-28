# GitHub Readme LinkedIn Article Cards

Generate live SVG cards for LinkedIn articles (title, description, cover image, and likes) for use in your GitHub README.

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

Optional query parameters:

- `title` (manual override)
- `description` (manual override)
- `image` (manual override)
- `likes` (manual override)
- `width` (default: `420`)
- `background_color` (default: `#0d1117`)
- `title_color` (default: `#ffffff`)
- `description_color` (default: `#c9d1d9`)
- `stats_color` (default: `#8b949e`)
- `border_radius` (default: `10`)

If metadata cannot be fetched from LinkedIn (for example due anti-bot blocks), manual overrides can still be used to render a card.
