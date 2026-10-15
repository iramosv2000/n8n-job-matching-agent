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

Tests for the Python tools live in [`../tests/`](../tests/): `python3 -m unittest discover -s tests`.
