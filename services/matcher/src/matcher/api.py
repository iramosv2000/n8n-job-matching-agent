"""HTTP API consumed by n8n (private Docker network; not published to the host)."""

from fastapi import FastAPI

from matcher import __version__
from matcher.dedupe import find_duplicates
from matcher.models import DedupeRequest, DedupeResponse, Health, NormalizeRequest, NormalizeResponse
from matcher.normalize import normalize_batch

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
