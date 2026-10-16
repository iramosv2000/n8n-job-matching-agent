"""Text utilities shared by every source: normalisation, HTML stripping, word matching and
redaction of third-party contact data (docs/data-governance.md §4)."""

import hashlib
import re
import unicodedata

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# International numbers written with "+", and Chilean mobiles written without it ("9 1234 5678").
# Amounts such as "$1.800.000" are not matched: they start with "$" and use dot separators.
_PHONE_INTL = re.compile(r"\+\d{1,3}[\s.-]?(?:\(?\d{1,4}\)?[\s.-]?){2,4}\d{2,4}")
_PHONE_CL_MOBILE = re.compile(r"(?<![\d$.,])9[\s-]?\d{4}[\s-]?\d{4}(?![\d.,])")


def normalize(text: str | None) -> str:
    """Lower case, no accents, collapsed whitespace."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def strip_html(html: str | None) -> str:
    """Plain text from the small HTML subset used by job boards, keeping line breaks."""
    if not html:
        return ""
    text = re.sub(r"<(br|/p|/li|/div|/h\d)\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    for entity, char in (("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    text = text.replace("&amp;", "&")
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def contains(normalized_text: str, term: str) -> bool:
    """Word-prefix match on normalised text. Terms of up to 3 characters (acronyms such as
    'plc', 'pid', 'rm') must match a whole word, optionally plural, so 'pid' does not match 'pide'."""
    pattern = r"(?<![a-z0-9])" + re.escape(term)
    if len(term) <= 3:
        pattern += r"s?(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def redact_contacts(text: str) -> tuple[str, int]:
    """Replace e-mail addresses and phone numbers with placeholders; return text and count."""
    count = 0
    for pattern, placeholder in (
        (_EMAIL, "[email]"),
        (_PHONE_INTL, "[phone]"),
        (_PHONE_CL_MOBILE, "[phone]"),
    ):
        text, n = pattern.subn(placeholder, text)
        count += n
    return text, count


def content_hash(*parts: str | None) -> str:
    """Stable fingerprint of the normalised content, used to detect edits to an offer."""
    joined = "\x1f".join(normalize(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
