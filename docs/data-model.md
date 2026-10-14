# Data Model (logical)

Target: PostgreSQL 16, schema `jobs`. n8n stores its own state in a separate schema
(`n8n`) of the same instance. Physical DDL is delivered as versioned migrations in
[`../db/migrations/`](../db/migrations/) during M2.

```mermaid
erDiagram
    runs ||--o{ run_sources : has
    offers ||--o{ offer_features : "scored as"
    offers ||--o| applications : "tracked by"
    offers ||--o{ cv_adaptations : "tailored for"
    offers ||--o{ llm_calls : "costed by"

    runs {
        uuid run_id PK
        timestamptz started_at
        timestamptz finished_at
        text status
    }
    run_sources {
        uuid run_id FK
        text source
        int fetched
        int new
        int errors
        text error_sample
    }
    offers {
        text offer_id PK
        text source
        text url
        text title
        text company
        text region
        date published_at
        text description
        jsonb raw
        text content_hash
        timestamptz first_seen
        timestamptz last_seen
        text duplicate_of
    }
    offer_features {
        bigserial id PK
        text offer_id FK
        text extractor
        text extractor_version
        jsonb features
        numeric score
        jsonb score_breakdown
        bool discarded
        text_array discard_reasons
        timestamptz created_at
    }
    applications {
        text offer_id PK
        text status
        timestamptz status_at
        text notes
    }
    cv_adaptations {
        bigserial id PK
        text offer_id FK
        text cv_hash
        text model
        jsonb output
        jsonb validation
        bool flagged
        timestamptz created_at
    }
    confirmed_skills {
        text skill PK
        text evidence
        timestamptz confirmed_at
    }
    llm_calls {
        bigserial id PK
        text workflow
        text offer_id FK
        text task
        text provider
        text model
        int input_tokens
        int cached_input_tokens
        int output_tokens
        int latency_ms
        numeric cost_usd
        text request_id
        timestamptz created_at
    }
```

## Table notes

| Table | Notes |
|---|---|
| `offers` | `offer_id` = `{source}:{native_id}`. `content_hash` detects edits to an existing offer. `duplicate_of` links cross-source duplicates rather than deleting them, so the deduplication decision stays auditable. |
| `offer_features` | **Append-only.** One row per extractor run (`extractor` ∈ {`rules`, `llm`, `hybrid`}) and version, so extractors can be compared on the same offers (needed in M6). The current view picks the latest `hybrid` row. |
| `applications` | `status` ∈ {`new`, `shortlisted`, `cv_generated`, `applied`, `interview`, `offer`, `rejected`, `discarded`}. Transitions are written only by WF-04 or by MCP tools with confirmation. |
| `cv_adaptations` | `cv_hash` is a SHA-256 of the master CV, so outputs made from an older CV can be detected and regenerated. `validation` stores the guardrail report. |
| `confirmed_skills` | Skills absent from the master CV that the candidate confirmed holding, each with free-text evidence. These are the only additions the CV agent may use. |
| `llm_calls` | One row per LLM request: `provider` (`gemini_free`, `ollama`, `claude_api`), model, token usage, latency, and the provider's request ID when available. These rows drive quota tracking and fallback routing. `cost_usd` is 0 for free providers and is kept for the optional paid provider. |

## Canonical offer schema (contract between n8n and matcher-service)

```json
{
  "offer_id": "getonbrd:abc123",
  "source": "getonbrd",
  "url": "https://…",
  "title": "Ingeniero/a de Automatización",
  "company": "…",
  "location_raw": "Santiago",
  "region": "RM",
  "published_at": "2026-10-13",
  "description_text": "…",
  "structured": {
    "contract": null, "schedule": null, "modality": null,
    "seniority": null, "salary_min_clp": null, "salary_max_clp": null
  }
}
```

## Retention

Collected offer texts are kept locally only for as long as the evaluation needs them. The
default is 180 days, after which `description` and `raw` are purged and labels and
features are kept. See [`data-governance.md`](data-governance.md).
