from datetime import date

import httpx2
import pytest
from chiletrabajos_site import LISTING, detail, transport

from matcher.http import PoliteClient
from matcher.models import SourceFetchRequest
from matcher.sources.chiletrabajos import (
    fetch,
    offer_number,
    parse_detail,
    parse_listing,
    search_url,
    spanish_date,
    to_canonical,
)

TODAY = date(2026, 10, 16)


def polite(transport_):
    return PoliteClient(transport=transport_, sleep=lambda s: None, min_interval=0)


def test_helpers():
    assert spanish_date("Publicado el 15 de Octubre de 2026") == date(2026, 10, 15)
    assert spanish_date("31 de febrero de 2026") is None
    assert spanish_date("ayer") is None
    assert offer_number("https://www.chiletrabajos.cl/trabajo/x-123/") == "123"
    assert offer_number("https://www.chiletrabajos.cl/trabajo/x") is None
    assert search_url("plc scada", 0).endswith("/encuentra-un-empleo?2=plc+scada")
    assert "/encuentra-un-empleo/30?" in search_url("plc", 1)


def test_parse_listing_and_detail():
    entries = parse_listing(LISTING)
    assert [e["title"] for e in entries] == [
        "Ingeniero Automatizacion",
        "Ingeniero Electronico",
        "Tecnico Antiguo",
    ]
    assert entries[0]["date"] == "2026-10-15"
    parsed = parse_detail(detail(101, "Oferta 101"))
    assert parsed["jobposting"]["title"] == "Oferta 101"
    assert parsed["table"] == {"buscado": "Andes Procesos SpA", "duracion": "Indefinido", "tipo": "Full-time"}
    assert parse_detail("<script type='application/ld+json'>{bad</script>")["jobposting"] == {}


def test_fetch_skips_old_and_known_offers_and_respects_cap():
    mock, calls = transport()
    request = SourceFetchRequest(queries=["automatizacion"], days=7, known_ids=["chiletrabajos:102"])
    result = fetch(polite(mock), request, TODAY)
    assert (result.listed, result.candidates, result.skipped_known, result.errors) == (3, 2, 1, 0)
    assert [i["id"] for i in result.items] == ["101"]
    assert not any(c.endswith("-102") for c in calls)  # known offer: detail not downloaded
    assert "www.chiletrabajos.cl" in result.robots_checked_at

    capped = fetch(polite(transport()[0]), SourceFetchRequest(queries=["x"], days=7, max_details=0), TODAY)
    assert (capped.candidates, len(capped.items)) == (2, 0)


def test_fetch_counts_unavailable_pages():
    mock, _ = transport(detail_status={101: 404})
    result = fetch(polite(mock), SourceFetchRequest(queries=["x"], days=7), TODAY)
    assert result.errors == 1
    assert "detail unavailable" in result.error_sample
    assert [i["id"] for i in result.items] == ["102"]


def test_fetch_stops_when_robots_disallow():
    mock, calls = transport(robots_body="User-agent: *\nDisallow: /\n")
    result = fetch(polite(mock), SourceFetchRequest(queries=["x"]), TODAY)
    assert result.items == []
    assert result.errors == 1
    assert "disallowed by robots.txt" in result.error_sample
    assert calls == ["https://www.chiletrabajos.cl/robots.txt"]


def test_fetch_when_listing_refused():
    refused = httpx2.MockTransport(lambda r: httpx2.Response(404 if r.url.path == "/robots.txt" else 403))
    result = fetch(polite(refused), SourceFetchRequest(queries=["x"], pages=2), TODAY)
    assert result.errors == 1
    assert "listing unavailable" in result.error_sample


def item(**overrides):
    base = {"id": "101", "url": "https://www.chiletrabajos.cl/trabajo/oferta-101",
            "listing": {"title": "Oferta 101", "meta": "Empresa, Calama", "date": "2026-10-15"},
            **parse_detail(detail(101, "Oferta 101"))}  # fmt: skip
    base.update(overrides)
    return base


def test_to_canonical_maps_jsonld_and_table():
    offer = to_canonical(item(), usd_clp=None)
    assert offer.offer_id == "chiletrabajos:101"
    assert (offer.company, offer.location_raw, offer.region) == (
        "Andes Procesos SpA",
        "Calama, Antofagasta",
        "Antofagasta",
    )
    assert offer.published_at == date(2026, 10, 15)
    assert offer.structured.salary_min_clp == 1_800_000
    assert (offer.structured.contract, offer.structured.schedule) == ("Indefinido", "Full-time")
    assert "[email]" in offer.description
    assert offer.redactions == 1


@pytest.mark.parametrize(("salary", "expected"), [("250000", None), ("abc", None), ("2.000.000", 2_000_000)])
def test_salary_parsing(salary, expected):
    assert (
        to_canonical(item(**parse_detail(detail(101, "x", salary=salary))), None).structured.salary_min_clp
        == expected
    )


def test_remote_without_location_and_listing_fallbacks():
    parsed = parse_detail(detail(101, "", location_type="TELECOMMUTE"))
    parsed["jobposting"].pop("jobLocation")
    parsed["jobposting"]["description"] = "Trabajo remoto desde cualquier ciudad"
    parsed["jobposting"].pop("hiringOrganization")
    offer = to_canonical(item(listing={"title": "Oferta 101", "meta": "", "date": None}, **parsed), None)
    assert offer.title == "Oferta 101"
    assert offer.region == "Remoto"
    assert offer.structured.remote_modality == "remote"
    assert offer.company == "Andes Procesos SpA"  # from the detail table


def test_missing_fields_raise():
    with pytest.raises(ValueError, match="missing"):
        to_canonical(item(id=None), None)


def test_fetch_reports_cap_backlog_and_truncation():
    full_page = (
        "<html><body>"
        + "".join(
            f'<div class="job-item"><h2><a href="https://www.chiletrabajos.cl/trabajo/o-{n}">O {n}</a></h2>'
            f'<h3 class="meta">Empresa, Calama</h3><h3 class="meta">16 de octubre de 2026</h3></div>'
            for n in range(1000, 1030)
        )
        + "</body></html>"
    )

    def handler(request):
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx2.Response(404)
        if "/encuentra-un-empleo" in url:
            return httpx2.Response(200, text=full_page)  # every page full and in-window
        return httpx2.Response(200, text=detail(1, "x"))

    request = SourceFetchRequest(queries=["a", "b"], pages=1, max_details=5, days=7)
    result = fetch(polite(httpx2.MockTransport(handler)), request, TODAY)
    assert (result.candidates, result.downloaded, result.pending) == (30, 5, 25)
    assert (result.detail_cap, result.truncated_queries) == (5, 2)


def test_no_truncation_when_last_page_is_short_or_old():
    mock, _ = transport()
    result = fetch(polite(mock), SourceFetchRequest(queries=["x"], pages=1, days=7), TODAY)
    assert result.truncated_queries == 0  # 4 entries < page size
    assert result.pending == 0
