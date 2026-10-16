"""Cross-source deduplication, ported from the As-Is tool (buscar.deduplicar).

Two offers are the same posting when they share the normalised company name and region and
their titles have a Jaccard similarity >= 0.7 over content words. Duplicates are *linked*
(duplicate_of), never deleted, so the decision stays auditable (docs/data-model.md).
"""

import re

from matcher.models import DedupeItem, DedupeRequest, DedupeResponse, DuplicateLink
from matcher.text import normalize

THRESHOLD = 0.7
STOPWORDS = {
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "y",
    "e",
    "en",
    "con",
    "para",
    "a",
    "o",
    "al",
    "un",
    "una",
}


def title_words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", normalize(title)) if len(w) > 1 and w not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _company_key(company: str | None) -> str | None:
    key = normalize(company)[:40]
    if not key or "confidencial" in key:
        return None  # anonymous employers cannot be matched safely
    return key


def find_duplicates(request: DedupeRequest) -> DedupeResponse:
    index: dict[str, list[tuple[DedupeItem, set[str]]]] = {}
    for item in request.existing:
        key = _company_key(item.company)
        if key:
            index.setdefault(key, []).append((item, title_words(item.title)))

    links = []
    for candidate in request.candidates:
        key = _company_key(candidate.company)
        if not key:
            continue
        words = title_words(candidate.title)
        best: tuple[float, DedupeItem] | None = None
        for canonical, canonical_words in index.get(key, []):
            if canonical.offer_id == candidate.offer_id or canonical.region != candidate.region:
                continue
            score = jaccard(words, canonical_words)
            if score >= THRESHOLD and (best is None or score > best[0]):
                best = (score, canonical)
        if best:
            links.append(
                DuplicateLink(
                    offer_id=candidate.offer_id, duplicate_of=best[1].offer_id, similarity=round(best[0], 3)
                )
            )
        else:
            index.setdefault(key, []).append((candidate, words))
    return DedupeResponse(links=links)
