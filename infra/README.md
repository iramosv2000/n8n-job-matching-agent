# infra/

Local platform for the project: n8n (Community Edition), PostgreSQL 18, schema migrations
(dbmate) and matcher-service on a private Docker network, defined in
[`../compose.yaml`](../compose.yaml). The local LLM runtime (Ollama) runs **natively on the host**, not in Docker, because
containers on macOS cannot use the Apple GPU
([ADR-0007](../docs/adr/0007-zero-cost-provider-agnostic-llm.md)).

## Prerequisites

| Tool | Purpose | No-cost option |
|---|---|---|
| A Docker engine with Compose v2 | Runs n8n and PostgreSQL | [Colima](https://github.com/abiosoft/colima) (MIT) or Docker Desktop (free for personal use) |
| Ollama (official build) | Local LLM runtime (from M1-07) | `brew install --cask ollama-binary` (**not** the `ollama` formula, see below) |
| Python ≥ 3.9, `pre-commit` | Repository tooling and hooks | `brew install pre-commit` |

**Memory budget on a 16 GB machine:** give the Docker VM about 4 GB (n8n and PostgreSQL
use well under 2 GB) and leave the rest to Ollama and macOS. With Colima:
`colima start --cpu 4 --memory 4`.

## Quick start

```bash
scripts/init_env.sh             # creates .env with random secrets (git-ignored)
docker compose up -d --wait     # starts PostgreSQL, then n8n, and waits for health checks
scripts/smoke_test.sh           # readiness, schemas, workflow import, export checks
open http://localhost:5678      # first visit: create the local n8n owner account
```

n8n is published on `127.0.0.1:5678` only, so it is not reachable from the LAN.

## Layout

| Path | Content |
|---|---|
| `../compose.yaml` | Services, health checks, pinned images (`postgres:18.6-alpine`, `dbmate:2.36.0`, `n8n:2.42.7`); `matcher` built from `services/matcher` |
| `../db/migrations/` | SQL migrations, applied by the one-shot `migrate` service before n8n and matcher start |
| `postgres/init/01-schemas.sql` | Creates schemas `n8n` (n8n's own tables) and `jobs` (application data) on first start |
| `../.env.example` | Variables; `scripts/init_env.sh` turns it into `.env` |

**Version policy:** images are pinned to exact versions. n8n is pinned to the latest
patch of the previous minor line (2.42.x), because the current minor (2.43) was released
on 2026-10-14. Upgrades are deliberate pull requests, so CI runs the smoke test against
the new version before it is merged.

## Secrets and the encryption key

- `.env` holds only infrastructure secrets (database password, `N8N_ENCRYPTION_KEY`).
  API keys and bot tokens are stored as **n8n credentials**, encrypted with that key.
- **Back up `N8N_ENCRYPTION_KEY` now** in a password manager. Without it, the credentials
  stored in n8n cannot be decrypted after a reinstall or on another machine.
- Restore procedure: put the same key in the new `.env` **before** the first
  `docker compose up`, then import the workflows and re-enter or restore the credentials.
- `scripts/init_env.sh` refuses to overwrite an existing `.env`. Using `--force`
  generates new secrets and makes existing credentials unreadable.

## Workflows ↔ Git

```bash
scripts/export_workflows.sh     # n8n → workflows/*.json (normalised, checked)
scripts/import_workflows.sh     # workflows/*.json → n8n (imported inactive)
```

The export uses `n8n export:workflow --backup`. `normalize_workflows.py` then removes
timestamps, version counters, pinned data and static data, and names each file after its
workflow. `check_workflows.py` rejects data, embedded credentials or secret-looking
strings ([ADR-0006](../docs/adr/0006-workflow-versioning.md)).

## Ollama: use the official build

Install the official binary (`brew install --cask ollama-binary`) or the app from
ollama.com. The Homebrew **formula** `ollama` 0.40.4 lacks `libollama_xgrammar.dylib`.
Without that library, models served by Ollama's MLX engine (for example `qwen3.5`,
`gemma4`) reject schema-constrained requests with HTTP 501, and the log shows
"Structured output is unavailable". This was found in M1-07; see
[`docs/spikes/M1-07-local-llm-benchmark.md`](../docs/spikes/M1-07-local-llm-benchmark.md).

```bash
ollama serve                    # keep running while the stack uses local models
ollama pull <model>             # model chosen in ADR-0007
```

## Reaching Ollama from n8n

In n8n's Ollama credential, set the base URL to `http://host.docker.internal:11434`.

| Engine | `host.docker.internal` |
|---|---|
| Docker Desktop (macOS) | Provided automatically |
| Colima (macOS) | Works with Colima 0.10.3, with Ollama bound to `127.0.0.1` (verified in M1-06) |
| Docker Engine (Linux) | Add `extra_hosts: ["host.docker.internal:host-gateway"]` to the n8n service in a `compose.override.yaml` |

## Common operations

| Task | Command |
|---|---|
| Logs | `docker compose logs -f n8n` |
| Stop (keep data) | `docker compose down` |
| Reset everything (deletes data) | `docker compose down -v` |
| SQL shell | `docker compose exec postgres psql -U jobmatcher -d jobmatcher` |
