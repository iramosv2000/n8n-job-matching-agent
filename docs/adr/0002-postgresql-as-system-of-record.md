# ADR-0002: PostgreSQL as system of record

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
The As-Is uses SQLite with a single writer. In the To-Be, several workflows write
concurrently: ingestion, Telegram actions and evaluation. n8n itself also needs a
production-grade database, and its default SQLite is not recommended for concurrent use.

## Decision
Use one **PostgreSQL** instance (major version 18, see amendment) with two schemas: `n8n` for n8n's own state and `jobs`
for the application data. Schema changes are versioned SQL migrations.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Keep SQLite | Zero setup; existing data | Single writer; weak fit for n8n in production |
| n8n Data Tables / Google Sheets | No database to run | No relational integrity; poor for evaluation queries; external dependency |
| **PostgreSQL** | Native n8n node; concurrency; JSONB for features; `pgvector` available if semantic search is added later | One more container |

## Consequences
- The As-Is SQLite history can be imported once with a migration script (optional).
- JSONB stores extractor outputs, so the schema does not have to change with each new field.

## Amendment (2026-10-16, M2-01): PostgreSQL 18

The original record named PostgreSQL 16. When the stack ran with n8n 2.42.7, n8n logged
"Postgres 16 is outside the supported range and receives compatibility support only.
Upgrade to Postgres 17 or newer." The stack was moved to **`postgres:18.6-alpine`** before
any real data existed. PostgreSQL 18 is the newest major, already has six patch releases,
and has the longest support window. Images from 18 onwards keep data under a versioned
subdirectory, so the volume is mounted at `/var/lib/postgresql`. Schema migrations are
applied by a one-shot `migrate` service (dbmate 2.36.0) on every `docker compose up`.
