# workflows/

Exported n8n workflows, one pretty-printed JSON file per workflow, produced by
`scripts/export_workflows.sh` ([ADR-0006](../docs/adr/0006-workflow-versioning.md)).

- Never edit these files by hand: change the workflow in n8n, then export it.
- Files contain credential **references** only; CI rejects secret-looking values.
- Workflow catalogue (WF-01 … WF-09): [`docs/architecture.md`](../docs/architecture.md#3-workflow-catalogue-n8n).

| File | Workflow | Trigger | Status |
|---|---|---|---|
| `wf-00-smoke-test.json` | Minimal workflow that CI imports to prove the round trip | Manual | ✔ |
| `wf-01-ingest-sources.json` | **WF-01 ingest-sources**: Get on Board → matcher `/normalize` → `/dedupe` → upsert `jobs.offers` → run counts | Weekdays 08:00 (America/Santiago) + manual | ✔ M2 |

### WF-01 in brief

```
Config ─▶ Start run ─▶ USD rate ─▶ USD rate (fallback) ─▶ Build requests ─▶ Get on Board API ─▶ Collect
   ─▶ Normalize (matcher) ─▶ Recent offers ─▶ Dedupe (matcher) ─▶ Upsert offers ─▶ Finish run
```

- **Search configuration** (categories, queries, pages, 21-day window) lives in the `Config`
  node, so changes to it are versioned with the workflow.
- **Politeness:** one request every 0.8 s, identifiable User-Agent, 3 retries. Errors are
  counted per run instead of aborting it.
- **USD → CLP:** mindicador.cl, then open.er-api.com. If both fail, salaries are kept as
  a USD note, never converted with a stale constant.
- **Idempotent:** a re-run on the same day inserts 0 new offers. `updated` counts content
  changes (`content_hash`).
- **Self-healing:** a run left in `running` for more than 2 h is marked `failed` by the
  next run.
- **CLI runs** (`scripts/run_ingestion.sh`) are recorded with trigger `schedule`, because
  n8n reports CLI executions as production executions.

Setup on a new machine: `scripts/bootstrap_credentials.sh` (Postgres credential), then
`scripts/import_workflows.sh`. To schedule WF-01, activate it in the editor or with
`docker compose exec n8n n8n publish:workflow --id=wf01IngestGoB001`.
