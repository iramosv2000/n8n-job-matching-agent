# services/matcher/

`matcher-service`: a Python 3.12 FastAPI service holding the project's deterministic
domain logic ([ADR-0001](../../docs/adr/0001-n8n-orchestrates-python-computes.md)). n8n
calls it at `http://matcher:8000` on the private Docker network; it is not published to
the host.

## Endpoints

| Method & path | Status | Purpose |
|---|---|---|
| `GET /health` | M2 ✔ | Liveness (used by the Docker health check) |
| `POST /normalize` | M2 ✔ | Raw source items → canonical offers; HTML stripped; e-mails and phones redacted; malformed items rejected individually |
| `POST /dedupe` | M2 ✔ | Links cross-source duplicates (same company and region, title Jaccard ≥ 0.7) |
| `GET /sources` | M2 ✔ | Known sources, whether each is enabled, and its data policy (`external_llm_allowed`, terms-review date) |
| `POST /sources/fetch-enabled` | M2 ✔ | Fetch every enabled optional source (WF-01). Empty when none is enabled |
| `POST /sources/{name}/fetch` | M2 ✔ | Fetch one optional source: 404 if unknown, 400 if fetched by n8n, 403 if disabled |
| `POST /extract/rules`, `POST /score` | M3 | Rule extraction and scoring, ported with parity tests |
| `POST /validate/cv` | M5 | Fabrication and gap-leak guardrail |

Interactive docs: `docker compose exec n8n wget -qO- http://matcher:8000/openapi.json`, or
run the service locally (below) and open `http://127.0.0.1:8000/docs`.

## Layout

```
src/matcher/
├── api.py           FastAPI app and routes
├── models.py        Pydantic contracts (canonical offer, dedupe, health)
├── normalize.py     Batch dispatch to source adapters
├── http.py          PoliteClient: robots.txt per request, 0.8 s spacing, backoff, no retry on 401/403
├── sources/__init__.py   Source registry and per-source policy (ADR-0008)
├── sources/getonbrd.py   Get on Board API item → canonical offer
├── sources/chiletrabajos.py   Listing + JSON-LD JobPosting → canonical offer (optional source)
├── regions.py       Chilean region detection (ported; parity-tested on 124 real locations)
├── dedupe.py        Cross-source deduplication (ported)
└── text.py          Normalisation, HTML stripping, contact redaction, content hash
tests/               pytest; fictitious fixtures plus the region parity oracle
```

## Development

```bash
cd services/matcher
uv sync                      # Python 3.12 + locked dependencies (uv.lock)
uv run pytest                # tests with coverage gate (>= 90 %)
uv run uvicorn matcher.api:app --reload
```

**Note:** on macOS, uv marks `.venv` as hidden, and Python skips hidden `.pth` files, which
breaks the editable install. pytest therefore imports from `src/` (`pythonpath` in
`pyproject.toml`). The Docker image installs the package non-editable and is unaffected.

## Image

`Dockerfile` is a multi-stage build. Dependencies come from `uv.lock` in a cached layer,
the runtime image has no build tools, and the process runs as an unprivileged user (uid
10001) with a Python health check. In `compose.yaml` the container also runs with a
read-only filesystem, all capabilities dropped and `no-new-privileges`.
