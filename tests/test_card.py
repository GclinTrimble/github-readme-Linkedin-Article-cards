import xml.dom.minidom as minidom

import pytest

import app as app_module
from card.utils import data_uri_from_url, trim_lines


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def _patch_metadata(monkeypatch, **overrides):
    base = {"title": "", "description": "", "image": "", "likes": ""}
    base.update(overrides)
    monkeypatch.setattr(app_module, "fetch_article_metadata", lambda _url: base)


def test_missing_url_returns_400(client):
    assert client.get("/card.svg").status_code == 400


def test_invalid_url_returns_400(client):
    assert client.get("/card.svg?url=https://evil.com/pulse/x").status_code == 400


def test_card_renders_well_formed_svg(client, monkeypatch):
    _patch_metadata(monkeypatch, title="Hello", description="World", likes="12 likes")
    monkeypatch.setattr(app_module, "data_uri_from_url", lambda _url: "")
    resp = client.get("/card.svg?url=https://www.linkedin.com/pulse/test")
    assert resp.status_code == 200
    assert resp.mimetype == "image/svg+xml"
    # Parses as XML -> well-formed.
    doc = minidom.parseString(resp.data)
    assert doc.documentElement.tagName == "svg"


def test_image_embedded_as_data_uri(client, monkeypatch):
    _patch_metadata(monkeypatch, image="https://example.com/cover.jpg")
    monkeypatch.setattr(
        app_module, "data_uri_from_url", lambda _url: "data:image/jpeg;base64,AAAA"
    )
    resp = client.get("/card.svg?url=https://www.linkedin.com/pulse/test")
    body = resp.data.decode("utf-8")
    assert "data:image/jpeg;base64,AAAA" in body
    assert "https://example.com/cover.jpg" not in body


def test_invalid_color_falls_back_to_default(client, monkeypatch):
    _patch_metadata(monkeypatch)
    monkeypatch.setattr(app_module, "data_uri_from_url", lambda _url: "")
    resp = client.get(
        "/card.svg?url=https://www.linkedin.com/pulse/test&background_color=zzz"
    )
    body = resp.data.decode("utf-8")
    assert "#0d1117" in body


def test_color_injection_cannot_emit_markup(client, monkeypatch):
    _patch_metadata(monkeypatch)
    monkeypatch.setattr(app_module, "data_uri_from_url", lambda _url: "")
    resp = client.get(
        "/card.svg?url=https://www.linkedin.com/pulse/test&background_color=red'/><script>alert(1)</script>"
    )
    body = resp.data.decode("utf-8")
    assert "<script>" not in body
    assert "alert(1)" not in body


def test_max_title_lines_changes_height(client, monkeypatch):
    long_title = "word " * 60
    _patch_metadata(monkeypatch, title=long_title)
    monkeypatch.setattr(app_module, "data_uri_from_url", lambda _url: "")
    one = client.get(
        "/card.svg?url=https://www.linkedin.com/pulse/test&max_title_lines=1"
    ).data.decode()
    four = client.get(
        "/card.svg?url=https://www.linkedin.com/pulse/test&max_title_lines=4"
    ).data.decode()

    def height(svg):
        doc = minidom.parseString(svg)
        return int(doc.documentElement.getAttribute("height"))

    assert height(four) > height(one)


def test_cards_requires_a_source(client):
    assert client.get("/cards.svg").status_code == 400


def test_cards_renders_grid_from_urls_list(client, monkeypatch):
    _patch_metadata(monkeypatch, title="Hello", description="World")
    monkeypatch.setattr(app_module, "data_uri_from_url", lambda _url: "")
    urls = (
        "https://www.linkedin.com/pulse/a,"
        "https://www.linkedin.com/pulse/b,"
        "https://www.linkedin.com/pulse/c"
    )
    resp = client.get(f"/cards.svg?urls={urls}&max=2&columns=2")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    doc = minidom.parseString(body)
    assert doc.documentElement.tagName == "svg"
    # One nested <svg> per tile, capped at max=2.
    assert len(doc.documentElement.getElementsByTagName("svg")) == 2


def test_cards_falls_back_when_scrape_yields_nothing(client, monkeypatch):
    _patch_metadata(monkeypatch, title="Hello")
    monkeypatch.setattr(app_module, "data_uri_from_url", lambda _url: "")
    monkeypatch.setattr(app_module, "fetch_article_urls", lambda _url: [])
    profile = "https://www.linkedin.com/in/guillaume-clin/recent-activity/articles/"
    resp = client.get(
        f"/cards.svg?url={profile}&urls=https://www.linkedin.com/pulse/a&max=4"
    )
    assert resp.status_code == 200
    doc = minidom.parseString(resp.data)
    assert len(doc.documentElement.getElementsByTagName("svg")) == 1


def test_trim_lines_adds_ellipsis():
    lines = trim_lines("one two three four five six seven", width=10, max_lines=1)
    assert len(lines) == 1
    assert lines[0].endswith("…")


def test_data_uri_rejects_non_https():
    assert data_uri_from_url("http://example.com/x.jpg") == ""
    assert data_uri_from_url("") == ""
