"""Pydantic contracts between n8n and matcher-service. Published as JSON Schema at /openapi.json."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["getonbrd", "chiletrabajos"]


class Structured(BaseModel):
    """Fields reported by the source itself, before any text extraction (M3)."""

    contract: str | None = None
    schedule: str | None = None
    remote_modality: str | None = None
    seniority: str | None = None
    salary_min_clp: int | None = None
    salary_max_clp: int | None = None
    salary_note: str | None = None
    countries: list[str] = Field(default_factory=list)
    outside_chile: bool = False


class CanonicalOffer(BaseModel):
    offer_id: str = Field(pattern=r"^[a-z0-9_]+:.+$", examples=["getonbrd:automation-engineer-acme"])
    source: Source
    url: str
    title: str
    company: str | None = None
    location_raw: str | None = None
    region: str
    published_at: date | None = None
    description: str = Field(description="Plain text with e-mail addresses and phone numbers redacted")
    redactions: int = Field(ge=0, description="Number of contact items redacted from the description")
    structured: Structured
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw: dict[str, Any] = Field(description="Unredacted source item, stored for the retention period only")


class NormalizeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"source": "getonbrd", "items": [], "usd_clp": 950.0}]}
    )

    source: Source
    items: list[dict[str, Any]]
    usd_clp: float | None = Field(
        default=None, gt=0, description="Exchange rate for USD salaries; null keeps them as a note"
    )


class Rejected(BaseModel):
    index: int
    reason: str


class NormalizeResponse(BaseModel):
    offers: list[CanonicalOffer]
    rejected: list[Rejected]


class DedupeItem(BaseModel):
    offer_id: str
    title: str
    company: str | None = None
    region: str | None = None
    first_seen: datetime | None = None


class DedupeRequest(BaseModel):
    candidates: list[DedupeItem] = Field(description="Offers from the current run")
    existing: list[DedupeItem] = Field(
        default_factory=list, description="Recent offers already stored, oldest first; they win ties"
    )


class DuplicateLink(BaseModel):
    offer_id: str
    duplicate_of: str
    similarity: float = Field(ge=0, le=1)


class DedupeResponse(BaseModel):
    links: list[DuplicateLink]


class Health(BaseModel):
    status: Literal["ok"]
    version: str


class SourceInfo(BaseModel):
    """Per-source policy (ADR-0008). The LLM router reads external_llm_allowed (M3)."""

    name: Source
    enabled: bool
    fetched_by: Literal["n8n", "matcher"]
    external_llm_allowed: bool = Field(
        description="Whether offer text may be sent to external (free-tier) LLM APIs"
    )
    terms_reviewed: str = Field(description="Date the source's terms of use were last reviewed")
    terms_url: str


class SourceFetchRequest(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=30)
    days: int = Field(default=21, ge=1, le=60)
    pages: int = Field(default=2, ge=1, le=5)
    max_details: int = Field(default=60, ge=0, le=200, description="Cap on detail pages downloaded per run")
    known_ids: list[str] = Field(
        default_factory=list, description="offer_ids already stored; their details are not re-downloaded"
    )


class SourceFetchResponse(BaseModel):
    source: Source
    items: list[dict[str, Any]]
    listed: int = Field(description="Listing entries seen")
    candidates: int = Field(description="Distinct recent offers in the listings")
    skipped_known: int
    downloaded: int = Field(default=0, description="Detail pages downloaded successfully")
    pending: int = Field(default=0, description="New candidates left for later runs because of max_details")
    detail_cap: int = Field(default=0, description="max_details applied in this run")
    truncated_queries: int = Field(
        default=0, description="Queries whose page limit cut off offers that are still inside the day window"
    )
    errors: int
    error_sample: str | None = None
    robots_checked_at: dict[str, str]


class FetchEnabledResponse(BaseModel):
    batches: list[SourceFetchResponse] = Field(description="One batch per enabled optional source")
