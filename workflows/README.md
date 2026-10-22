# workflows/

Exported n8n workflows, one pretty-printed JSON file per workflow, produced by
`scripts/export_workflows.sh` ([ADR-0006](../docs/adr/0006-workflow-versioning.md)).

- Never edit these files by hand: change the workflow in n8n, then export it.
- Files contain credential **references** only; CI rejects secret-looking values.
- Workflow catalogue (WF-01 … WF-09): [`docs/architecture.md`](../docs/architecture.md#3-workflow-catalogue-n8n).

| File | Workflow | Trigger | Status |
|---|---|---|---|
| `wf-00-smoke-test.json` | Minimal workflow that CI imports to prove the round trip | Manual | ✔ |
| `wf-01-ingest-sources.json` | **WF-01 ingest-sources**: Get on Board (API) + enabled optional sources (matcher) → `/normalize` → `/dedupe` → upsert `jobs.offers` → per-source run counts | Every 15 min, gated to once per weekday between 08:00 and 20:59 (America/Santiago) + manual | ✔ M2 |

### WF-01 in brief

```
Config ─▶ Gate ─▶ Should run? ─▶ Start run ─▶ USD rate ─▶ USD rate (fallback) ─▶ Build requests ─▶ Get on Board API
   ─▶ Collect Get on Board ─▶ Known ids ─▶ Optional sources (matcher /sources/fetch-enabled)
   ─▶ Batches (one per source) ─▶ Normalize ─▶ Combine ─▶ Recent offers ─▶ Dedupe ─▶ Upsert ─▶ Finish run
```

The pipeline is linear on purpose. It behaves the same with zero, one or several optional
sources enabled, and needs no Merge node waiting on a branch that may produce nothing.

- **Search configuration** (categories, queries, pages, 21-day window) lives in the `Config`
  node, so changes to it are versioned with the workflow.
- **Politeness:** one request every 0.8 s, identifiable User-Agent, 3 retries. Errors are
  counted per run instead of aborting it. Chiletrabajos detail downloads are capped at
  **150 per run** (ADR-0008 amendment), and each run records its backlog and truncation in
  `jobs.run_sources`.
- **USD → CLP:** mindicador.cl, then open.er-api.com. If both fail, salaries are kept as
  a USD note, never converted with a stale constant.
- **Idempotent:** a re-run on the same day inserts 0 new offers. `updated` counts content
  changes (`content_hash`).
- **Self-healing:** a run left in `running` for more than 2 h is marked `failed` by the
  next run.
- **Catch-up schedule that survives host sleep.** On macOS the Docker VM is suspended while
  the laptop sleeps, and **n8n's schedule timers are suspended with it**: a timer waiting for
  "next weekday 08:00" slips by the whole time the host slept. Observed on 2026-10-16/19:
  - Friday's hourly ticks fired late (14:50, 20:39);
  - the Monday 08:00 tick had not fired by 08:18, after a weekend asleep.

  The trigger therefore ticks **every 15 minutes, every day**. A short timer re-anchors to
  the wall clock at every tick, so after a wake-up the next tick comes within about 15
  minutes. `Gate` + `Should run?` let a scheduled tick work only if:
  - it is a weekday between 08:00 and 20:59 (Santiago time);
  - no run has succeeded today, and none is in progress;
  - fewer than 3 runs failed today. A failing day is retried at most three times.

  Skipped ticks end in milliseconds. They appear in n8n's *Executions* list (pruned after
  14 days by default) but write nothing to `jobs.runs`.
- **Run origin.** `Gate` reads the execution mode from n8n's `execution_entity` table
  (`trigger`, `cli` or `manual`; verified on 2.42.7). Runs are recorded as `schedule`
  (`trigger`) or `manual` (CLI and editor). Manual runs always proceed. An unknown mode is
  treated as scheduled, so a change in n8n internals cannot multiply the daily runs.
- **Verified on 2026-10-16:**
  - a CLI run proceeded on a day that already had runs, and was recorded as `manual`;
  - minute-by-minute scheduled ticks were skipped in 27–62 ms with no new rows;
  - a scheduled tick on a day without a successful run performed the full ingestion
    (126 s) and was recorded as `schedule`.

**Importing:** `import_workflows.sh` re-publishes workflows that were active before the
import, because n8n deactivates them on import, and `check_workflows.py` rejects two files
with the same workflow id, which would overwrite each other.

Setup on a new machine: `scripts/bootstrap_credentials.sh` (Postgres credential), then
`scripts/import_workflows.sh`. To schedule WF-01, activate it in the editor or with
`docker compose exec n8n n8n publish:workflow --id=wf01IngestGoB001`.
