"""HTTP API consumed by n8n (private Docker network; not published to the host)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException

from matcher import __version__
from matcher.dedupe import find_duplicates
from matcher.http import PoliteClient
from matcher.models import (
    DedupeRequest,
    DedupeResponse,
    FetchEnabledResponse,
    Health,
    NormalizeRequest,
    NormalizeResponse,
    SourceFetchRequest,
    SourceFetchResponse,
    SourceInfo,
)
from matcher.normalize import normalize_batch
from matcher.sources import POLICIES, chiletrabajos, enabled_sources, source_info

FETCHERS = {"chiletrabajos": chiletrabajos.fetch}
SANTIAGO = ZoneInfo("America/Santiago")


def make_client() -> PoliteClient:
    """Factory, replaced in tests with a client backed by a mock transport."""
    return PoliteClient()


app = FastAPI(
    title="matcher-service",
    version=__version__,
    description="Deterministic domain logic for the n8n job-matching agent (ADR-0001).",
)


@app.get("/health", response_model=Health, tags=["ops"])
def health() -> Health:
    return Health(status="ok", version=__version__)


@app.post("/normalize", response_model=NormalizeResponse, tags=["ingestion"])
def normalize(request: NormalizeRequest) -> NormalizeResponse:
    """Map raw source items to canonical offers; contact data in descriptions is redacted."""
    return normalize_batch(request)


@app.post("/dedupe", response_model=DedupeResponse, tags=["ingestion"])
def dedupe(request: DedupeRequest) -> DedupeResponse:
    """Link candidates that duplicate an existing or earlier candidate offer."""
    return find_duplicates(request)


@app.get("/sources", response_model=list[SourceInfo], tags=["sources"])
def sources() -> list[SourceInfo]:
    """Known sources, whether each is enabled, and its data policy."""
    return source_info()


@app.post("/sources/{name}/fetch", response_model=SourceFetchResponse, tags=["sources"])
def fetch_source(name: str, request: SourceFetchRequest) -> SourceFetchResponse:
    """Fetch raw items from an optional source (polite client: robots.txt, spacing, backoff)."""
    if name not in POLICIES:
        raise HTTPException(status_code=404, detail=f"unknown source: {name}")
    if name not in FETCHERS:
        raise HTTPException(status_code=400, detail=f"{name} is fetched by n8n, not by matcher-service")
    if name not in enabled_sources():
        raise HTTPException(status_code=403, detail=f"{name} is disabled (set MATCHER_ENABLED_SOURCES)")
    client = make_client()
    try:
        return FETCHERS[name](client, request, datetime.now(SANTIAGO).date())
    finally:
        client.close()


@app.post("/sources/fetch-enabled", response_model=FetchEnabledResponse, tags=["sources"])
def fetch_enabled(request: SourceFetchRequest) -> FetchEnabledResponse:
    """Fetch every enabled optional source in turn (used by WF-01). Empty when none is enabled."""
    names = [n for n in FETCHERS if n in enabled_sources()]
    client = make_client()
    try:
        today = datetime.now(SANTIAGO).date()
        return FetchEnabledResponse(batches=[FETCHERS[n](client, request, today) for n in names])
    finally:
        client.close()
