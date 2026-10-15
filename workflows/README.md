# workflows/

Exported n8n workflows, one pretty-printed JSON file per workflow, produced by
`scripts/export_workflows.sh` ([ADR-0006](../docs/adr/0006-workflow-versioning.md)).

- Never edit these files by hand: change the workflow in n8n, then export it.
- Files contain credential **references** only; CI rejects secret-looking values.
- Workflow catalogue (WF-01 … WF-09): [`docs/architecture.md`](../docs/architecture.md#3-workflow-catalogue-n8n).

`wf-00-smoke-test.json` is a minimal workflow that CI imports to prove the round trip works.
