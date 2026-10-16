"""Pydantic contracts between n8n and matcher-service. Published as JSON Schema at /openapi.json."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["getonbrd"]


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
