# ADR-0002: PostgreSQL as system of record

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
The As-Is uses SQLite with a single writer. In the To-Be, several workflows write
concurrently: ingestion, Telegram actions and evaluation. n8n itself also needs a
production-grade database, and its default SQLite is not recommended for concurrent use.

## Decision
Use one **PostgreSQL 16** instance with two schemas: `n8n` for n8n's own state and `jobs`
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
