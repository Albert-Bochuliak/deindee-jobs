"""Text-cleanup tests for normalize.py — entity-escaped markup must not
survive into stored descriptions (arbeitnow encodes its HTML)."""
from app.parsing.normalize import strip_html


def test_plain_markup_stripped():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_entity_escaped_markup_stripped():
    raw = (
        "&lt;p&gt;&lt;span data-contrast=&quot;auto&quot;&gt;"
        "Advise. Invest. Build.&lt;/span&gt;&lt;/p&gt;"
    )
    assert strip_html(raw) == "Advise. Invest. Build."


def test_double_escaped_markup_stripped():
    assert strip_html("&amp;lt;p&amp;gt;Hi&amp;lt;/p&amp;gt;") == "Hi"


def test_real_entities_still_decoded():
    assert strip_html("AT&amp;T jobs &amp; more") == "AT&T jobs & more"
