"""Get on Board public API (api/v0) → canonical offer.

Ported from the As-Is adapter (fuentes.getonbrd). The HTTP calls themselves are made by n8n
(WF-01, ADR-0003); this module only maps one job item, as returned with
expand=["company","seniority","location_cities","modality"], to the canonical schema.
"""

from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from matcher.models import CanonicalOffer, Structured
from matcher.regions import extract_region
from matcher.text import content_hash, redact_contacts, strip_html

SANTIAGO = ZoneInfo("America/Santiago")
REMOTE_MODALITIES = ("fully_remote", "remote_local")


def _name(relation: Any) -> str:
    """Name of an expanded JSON:API relation ({"data": {"attributes": {"name": ...}}})."""
    if not isinstance(relation, dict):
        return ""
    data = relation.get("data")
    if not isinstance(data, dict):
        return ""
    return str((data.get("attributes") or {}).get("name") or "")


def _published(timestamp: Any) -> date | None:
    if not isinstance(timestamp, int | float):
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).astimezone(SANTIAGO).date()


def _description(attrs: dict[str, Any]) -> str:
    desirable = strip_html(attrs.get("desirable"))
    desirable = "\n".join(f"Deseable: {line}" for line in desirable.splitlines() if line.strip())
    parts = [
        strip_html(attrs.get("projects")),
        strip_html(attrs.get("description")),
        strip_html(attrs.get("functions")),
        desirable,
        strip_html(attrs.get("benefits")),
    ]
    return "\n".join(p for p in parts if p)


def to_canonical(item: dict[str, Any], usd_clp: float | None) -> CanonicalOffer:
    """Map one API item. Raises ValueError when mandatory fields are missing."""
    attrs = item.get("attributes")
    if not item.get("id") or not isinstance(attrs, dict) or not attrs.get("title"):
        raise ValueError("missing id, attributes or title")
    url = (item.get("links") or {}).get("public_url")
    if not url:
        raise ValueError("missing links.public_url")

    countries = [str(c) for c in attrs.get("countries") or []]
    remote = attrs.get("remote_modality") in REMOTE_MODALITIES
    cities_data = (attrs.get("location_cities") or {}).get("data") or []
    cities = [str((c.get("attributes") or {}).get("name", "")) for c in cities_data if isinstance(c, dict)]
    location = ", ".join([c for c in cities if c] + [c for c in countries if c != "Chile"])
    location = location or ("Remoto" if remote else "")

    smin, smax = attrs.get("min_salary"), attrs.get("max_salary")
    schedule = _name(attrs.get("modality"))
    lowered = schedule.lower()
    contract = "freelance" if "freelance" in lowered else ("practica" if "intern" in lowered else None)

    description, redactions = redact_contacts(_description(attrs))
    company = _name(attrs.get("company")) or None
    region = "Remoto" if (remote and "Chile" not in countries) else extract_region(location)

    return CanonicalOffer(
        offer_id=f"getonbrd:{item['id']}",
        source="getonbrd",
        url=url,
        title=str(attrs["title"]).strip(),
        company=company,
        location_raw=location or None,
        region=region,
        published_at=_published(attrs.get("published_at")),
        description=description,
        redactions=redactions,
        structured=Structured(
            contract=contract,
            schedule=schedule or None,
            remote_modality=attrs.get("remote_modality") or None,
            seniority=_name(attrs.get("seniority")) or None,
            salary_min_clp=round(smin * usd_clp) if (smin and usd_clp) else None,
            salary_max_clp=round(smax * usd_clp) if (smax and usd_clp) else None,
            salary_note=f"USD {smin or '?'}–{smax or '?'} /mes" if (smin or smax) else None,
            countries=countries,
            outside_chile=not ("Chile" in countries or (remote and ("Remote" in countries or not countries))),
        ),
        content_hash=content_hash(attrs.get("title"), company, description),
        raw=item,
    )
