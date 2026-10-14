# db/

Versioned SQL migrations for the `jobs` schema in PostgreSQL
([ADR-0002](../docs/adr/0002-postgresql-as-system-of-record.md)). Logical model:
[`docs/data-model.md`](../docs/data-model.md).

Naming: `migrations/NNNN_description.sql`, applied in order, never edited after merge.

*Populated from M2.*
