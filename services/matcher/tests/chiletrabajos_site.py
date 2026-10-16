"""A fictitious Chiletrabajos-like site served through httpx2.MockTransport (no network in tests)."""

import json

import httpx2

ROBOTS = "User-agent: *\nDisallow: /partners/\n"


def card(number: int, title: str, day: str) -> str:
    slug = title.lower().replace(" ", "-")
    return (
        f'<div class="job-item"><h2><a href="https://www.chiletrabajos.cl/trabajo/{slug}-{number}">'
        f'{title}</a></h2><h3 class="meta">Empresa Ficticia, Antofagasta</h3>'
        f'<h3 class="meta">{day} de octubre de 2026</h3></div>'
    )


LISTING = (
    "<html><body>"
    + "".join(
        [
            card(101, "Ingeniero Automatizacion", "15"),
            card(102, "Ingeniero Electronico", "14"),
            card(103, "Tecnico Antiguo", "1"),  # outside a 7-day window from 2026-10-16
            "<div class='job-item'><h2>sin enlace</h2></div>",
        ]
    )
    + "</body></html>"
)


def detail(number: int, title: str, salary: str = "1.800.000", location_type: str | None = None) -> str:
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "datePosted": "2026-10-15",
        "description": "<p>Programar PLC y SCADA. Postular a seleccion@example.com</p>",
        "hiringOrganization": {"@type": "Organization", "name": "Andes Procesos SpA"},
        "jobLocation": {
            "@type": "Place",
            "address": {"addressLocality": "Calama", "addressRegion": "Antofagasta"},
        },
        "baseSalary": {"@type": "MonetaryAmount", "value": {"@type": "QuantitativeValue", "value": salary}},
    }
    if location_type:
        posting["jobLocationType"] = location_type
    return (
        '<html><head><script type=\'application/ld+json\'>{"@type": "WebSite"}</script>'
        f"<script type='application/ld+json'>{json.dumps({'@graph': [posting]})}</script></head><body>"
        "<table class='table'><tr><td>Buscado</td><td>Andes Procesos SpA</td></tr>"
        "<tr><td>Duración</td><td>Indefinido</td></tr><tr><td>Tipo</td><td>Full-time</td></tr></table>"
        "</body></html>"
    )


def transport(robots_status: int = 200, robots_body: str = ROBOTS, detail_status: dict | None = None):
    detail_status = detail_status or {}
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        calls.append(url)
        if url.endswith("/robots.txt"):
            return httpx2.Response(robots_status, text=robots_body)
        if "/encuentra-un-empleo" in url:
            return httpx2.Response(200, text=LISTING)
        for number in (101, 102):
            if url.endswith(f"-{number}"):
                status = detail_status.get(number, 200)
                return httpx2.Response(
                    status, text=detail(number, f"Oferta {number}") if status == 200 else ""
                )
        return httpx2.Response(404)

    return httpx2.MockTransport(handler), calls
