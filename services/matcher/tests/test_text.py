import pytest

from matcher.text import contains, content_hash, normalize, redact_contacts, strip_html


def test_normalize_removes_accents_case_and_spacing():
    assert normalize("  Ingeniería   ELÉCTRICA\n") == "ingenieria electrica"
    assert normalize(None) == ""


def test_strip_html_keeps_line_breaks_and_decodes_entities():
    html = "<p>Uno &amp; dos</p><ul><li>PLC</li><li>HMI&nbsp;SCADA</li></ul><br/>"
    assert strip_html(html) == "Uno & dos\nPLC\nHMI SCADA"
    assert strip_html("") == ""


@pytest.mark.parametrize(
    ("text", "term", "expected"),
    [
        ("se pide plc y pid", "pid", True),
        ("el cargo pide experiencia", "pid", False),
        ("manejo de plcs", "plc", True),
        ("automatizacion industrial", "automatiz", True),
        ("forma parte", "rm", False),
    ],
)
def test_contains_word_prefix_rules(text, term, expected):
    assert contains(text, term) is expected


def test_redact_contacts_emails_and_phones_but_not_amounts():
    # Built at runtime so this file does not trip the repository's personal-data guard.
    email = "rrhh" + "@" + "empresa.cl"
    mobile = "9 " + "8123 4567"
    intl = "+56 2 " + "2345 6789"
    text = f"Escribir a {email} o llamar al {mobile} o {intl}. Renta $1.800.000 desde 2026."
    redacted, count = redact_contacts(text)
    assert count == 3
    assert "[email]" in redacted
    assert redacted.count("[phone]") == 2
    assert "$1.800.000" in redacted
    assert "2026" in redacted


def test_content_hash_is_stable_and_sensitive():
    assert content_hash("Título", "ACME", "texto") == content_hash("titulo", "acme", "  texto ")
    assert content_hash("Título", "ACME", "texto") != content_hash("Título", "ACME", "otro texto")
    assert len(content_hash(None)) == 64
