"""Structural accessibility checks; do not claim browser/screen-reader validation."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"

class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.elements = []
        self.feed(path.read_text(encoding="utf-8"))
    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_dialogs_have_explicit_names_resolving_to_page_content():
    count = 0
    for path in WEB.glob("*.html"):
        page = Page(path)
        ids = {attrs["id"] for _, attrs in page.elements if "id" in attrs}
        for tag, attrs in page.elements:
            if tag != "dialog":
                continue
            count += 1
            assert attrs.get("aria-label") or attrs.get("aria-labelledby"), (path.name, attrs.get("id"))
            for ref in attrs.get("aria-labelledby", "").split():
                assert ref in ids, (path.name, ref)
    assert count >= 5
    for filename, cancel_ids in [("exam.html", ["cancel-start", "cancel-finish"]), ("wallet.html", ["pack-cancel"])]:
        attrs_by_id = {a.get("id"): a for _, a in Page(WEB / filename).elements}
        assert all("autofocus" in attrs_by_id[key] for key in cancel_ids)


def test_skip_links_resolve_to_programmatically_focusable_main():
    for path in WEB.glob("*.html"):
        page = Page(path)
        for tag, attrs in page.elements:
            if tag == "a" and "skip" in attrs.get("class", "").split():
                target = attrs["href"].removeprefix("#")
                assert any(t == "main" and a.get("id") == target and a.get("tabindex") == "-1" for t, a in page.elements), path.name


def test_unique_ids_and_no_positive_tabindex():
    for path in WEB.glob("*.html"):
        page = Page(path)
        ids = [attrs["id"] for _, attrs in page.elements if "id" in attrs]
        assert not [key for key, count in Counter(ids).items() if count > 1], path.name
        assert all(int(attrs.get("tabindex", "0")) <= 0 for _, attrs in page.elements), path.name
