# db/

Versioned SQL migrations for the `jobs` schema in PostgreSQL
([ADR-0002](../docs/adr/0002-postgresql-as-system-of-record.md)). Logical model:
[`docs/data-model.md`](../docs/data-model.md).

- Tool: [dbmate](https://github.com/amacneil/dbmate) 2.36.0, run by the one-shot `migrate`
  service in `compose.yaml` on every `docker compose up` (idempotent). The applied versions
  are tracked in `jobs.schema_migrations`.
- Naming: `migrations/YYYYMMDDHHMMSS_description.sql`, each with `-- migrate:up` and
  `-- migrate:down` sections. Never edit a migration after it is merged; add a new one.

```bash
# Roll back the latest migration, then re-apply (both verified for 20261016000001):
docker compose run --rm migrate --migrations-dir /db/migrations --no-dump-schema rollback
docker compose run --rm migrate --migrations-dir /db/migrations --no-dump-schema up
```

| Migration | Content |
|---|---|
| `20261016000001_jobs_schema_v1` | `runs`, `run_sources`, `offers`; retention function `jobs.purge_offer_texts(days)` |
