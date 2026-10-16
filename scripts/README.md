# scripts/

| Script | Purpose |
|---|---|
| `init_env.sh` | Create `.env` from `.env.example` with random secrets (refuses to overwrite) |
| `export_workflows.sh` | Export all n8n workflows into `workflows/` (normalised and checked) |
| `import_workflows.sh` | Import `workflows/*.json` into the running n8n (inactive) |
| `normalize_workflows.py` | Strip volatile and data-bearing fields; name files after workflows |
| `check_workflows.py` | Reject invalid structure, execution data, embedded credentials and secret-like strings |
| `guard_personal_data.py` | Pre-commit guard against personal and collected data (optional local deny-list) |
| `smoke_test.sh` | End-to-end check of the running stack (used by CI) |
| `bootstrap_credentials.sh` | Create the n8n credentials that workflows reference by id, from `.env` (secrets never touch the repo) |
| `run_ingestion.sh` | Run WF-01 once from the CLI and print a one-line summary of the run |
| `ingestion_report.sh [days]` | Arrival-rate report (new offers per day and source) for M2-06 |
| `bench_local_llm.py` | M1-07 local LLM benchmark (see `docs/spikes/`) |

Tests for the Python tools live in [`../tests/`](../tests/): `python3 -m unittest discover -s tests`.
