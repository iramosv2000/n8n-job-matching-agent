"""Chiletrabajos (optional source, disabled by default): HTML listing + JSON-LD JobPosting.

Ported from the As-Is adapter (fuentes.chiletrabajos). Policy (ADR-0008): terms reviewed on
2026-10-16; they restrict publishing or transmitting site material, so offers from this source are
for local, personal processing only. They are never redistributed and never sent to external LLM
APIs (the router uses the local model only). Requests go through PoliteClient (robots.txt,
spacing, backoff).
"""

import json
import re
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from matcher.http import DisallowedByRobots, PoliteClient
from matcher.models import CanonicalOffer, SourceFetchRequest, SourceFetchResponse, Structured
from matcher.regions import extract_region
from matcher.text import content_hash, normalize, redact_contacts, strip_html

BASE = "https://www.chiletrabajos.cl"
PAGE_SIZE = 30
MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}  # fmt: skip


def spanish_date(text: str | None) -> date | None:
    match = re.search(r"(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})", normalize(text))
    if match and match.group(2) in MONTHS:
        try:
            return date(int(match.group(3)), MONTHS[match.group(2)], int(match.group(1)))
        except ValueError:
            return None
    return None


def offer_number(url: str) -> str | None:
    match = re.search(r"-(\d+)/?$", url)
    return match.group(1) if match else None


def search_url(query: str, page: int) -> str:
    offset = f"/{PAGE_SIZE * page}" if page else ""
    return f"{BASE}/encuentra-un-empleo{offset}?2={quote_plus(query)}"


def parse_listing(html: str) -> list[dict[str, Any]]:
    entries = []
    for card in BeautifulSoup(html, "html.parser").select("div.job-item"):
        link = card.select_one("h2 a")
        if not link or not link.get("href"):
            continue
        metas = [m.get_text(" ", strip=True) for m in card.select("h3.meta")]
        entries.append(
            {
                "url": str(link["href"]),
                "title": link.get_text(" ", strip=True),
                "meta": metas[0] if metas else "",
                "date": (d.isoformat() if (d := spanish_date(metas[-1] if metas else None)) else None),
            }
        )
    return entries


def jobposting(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text(), strict=False)
        except ValueError:
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in nodes if isinstance(nodes, list) else []:
            if isinstance(node, dict) and node.get("@type") == "JobPosting":
                return node
    return {}


def parse_detail(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    table = {}
    for row in soup.select("table.table tr"):
        cells = [td.get_text(" ", strip=True) for td in row.select("td")]
        if len(cells) >= 2:
            table[normalize(cells[0])] = cells[1]
    return {"jobposting": jobposting(soup), "table": table}


def fetch(client: PoliteClient, request: SourceFetchRequest, today: date) -> SourceFetchResponse:
    """Collect listings for each query, then download details of offers not seen before."""
    cutoff = today - timedelta(days=request.days)
    known = set(request.known_ids)
    candidates: dict[str, dict[str, Any]] = {}
    listed, errors, sample, truncated = 0, 0, None, 0
    try:
        for query in request.queries:
            for page in range(request.pages):
                html = client.get_text(search_url(query, page))
                if html is None:
                    errors += 1
                    sample = sample or f"listing unavailable: {query!r} page {page + 1}"
                    break
                entries = parse_listing(html)
                listed += len(entries)
                for entry in entries:
                    number = offer_number(entry["url"])
                    posted = date.fromisoformat(entry["date"]) if entry["date"] else None
                    if number and (posted is None or posted >= cutoff):
                        candidates.setdefault(number, entry)
                if len(entries) < PAGE_SIZE:
                    break
            else:
                # Page limit reached with a full last page: if its oldest entry is still inside the
                # window, in-window offers may exist beyond the pages we read (coverage truncation).
                dates = [e["date"] for e in entries if e["date"]]
                if entries and (not dates or min(dates) >= cutoff.isoformat()):
                    truncated += 1

        new = [(n, e) for n, e in candidates.items() if f"chiletrabajos:{n}" not in known]
        new.sort(key=lambda item: item[1]["date"] or "", reverse=True)  # newest first under the cap
        items = []
        for number, entry in new[: request.max_details]:
            html = client.get_text(entry["url"])
            if html is None:
                errors += 1
                sample = sample or f"detail unavailable: {entry['url']}"
                continue
            items.append({"id": number, "url": entry["url"], "listing": entry, **parse_detail(html)})
    except DisallowedByRobots as exc:
        return SourceFetchResponse(
            source="chiletrabajos", items=[], listed=listed, candidates=len(candidates),
            skipped_known=0, downloaded=0, pending=0, detail_cap=request.max_details,
            truncated_queries=truncated, errors=errors + 1,
            error_sample=f"disallowed by robots.txt: {exc}", robots_checked_at=client.robots_checked_at,
        )  # fmt: skip
    return SourceFetchResponse(
        source="chiletrabajos",
        items=items,
        listed=listed,
        candidates=len(candidates),
        skipped_known=len(candidates) - len(new),
        downloaded=len(items),
        pending=max(0, len(new) - request.max_details),
        detail_cap=request.max_details,
        truncated_queries=truncated,
        errors=errors,
        error_sample=sample,
        robots_checked_at=client.robots_checked_at,
    )


def _salary(posting: dict[str, Any]) -> int | None:
    try:
        value = posting["baseSalary"]["value"]
        raw = value.get("value") or value.get("Value") or value.get("minValue")
        amount = int(float(str(raw).replace(".", "").replace(",", "."))) if raw else 0
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    return amount if amount >= 300_000 else None  # below this it is not a monthly CLP salary


def to_canonical(item: dict[str, Any], usd_clp: float | None) -> CanonicalOffer:
    """Map one fetched item (listing + detail). Salaries are already in CLP; usd_clp is unused."""
    number, url = item.get("id"), item.get("url")
    posting, table, listing = item.get("jobposting") or {}, item.get("table") or {}, item.get("listing") or {}
    title = (posting.get("title") or listing.get("title") or "").strip()
    if not number or not url or not title:
        raise ValueError("missing id, url or title")

    address = (posting.get("jobLocation") or {}).get("address") or {}
    location = ", ".join(p for p in (address.get("addressLocality"), address.get("addressRegion")) if p)
    location = location or listing.get("meta") or ""
    company = (posting.get("hiringOrganization") or {}).get("name") or table.get("buscado") or None
    posted = posting.get("datePosted") or listing.get("date")
    description, redactions = redact_contacts(strip_html(posting.get("description")))
    salary = _salary(posting)
    remote = posting.get("jobLocationType") == "TELECOMMUTE" and "remot" in normalize(description)

    return CanonicalOffer(
        offer_id=f"chiletrabajos:{number}",
        source="chiletrabajos",
        url=url,
        title=title,
        company=company,
        location_raw=location or None,
        region="Remoto" if remote and not location else extract_region(location),
        published_at=date.fromisoformat(str(posted)[:10]) if posted else None,
        description=description,
        redactions=redactions,
        structured=Structured(
            contract=table.get("duracion") or None,
            schedule=table.get("tipo") or None,
            remote_modality="remote" if remote else None,
            salary_min_clp=salary,
            countries=["Chile"],
            outside_chile=False,
        ),
        content_hash=content_hash(title, company, description),
        raw=item,
    )
