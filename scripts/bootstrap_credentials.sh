#!/usr/bin/env bash
# Create (or update) the n8n credentials that versioned workflows reference by id.
# Secrets are read from .env and passed straight into the container; nothing is written to the
# repository. Workflows reference credentials by {id, name} only (ADR-0006).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

container_file=/tmp/credentials.json
cleanup() { docker compose exec -T n8n rm -f "$container_file" >/dev/null 2>&1 || true; }
trap cleanup EXIT

python3 - <<PY | docker compose exec -T n8n sh -c "umask 077 && cat > $container_file"
import json, os
print(json.dumps([{
    "id": "jobsPostgres0001",
    "name": "jobs-postgres (local)",
    "type": "postgres",
    "data": {
        "host": "postgres",
        "port": 5432,
        "database": os.environ.get("POSTGRES_DB", "jobmatcher"),
        "user": os.environ.get("POSTGRES_USER", "jobmatcher"),
        "password": os.environ["POSTGRES_PASSWORD"],
        "ssl": "disable",
    },
}]))
PY
docker compose exec -T n8n n8n import:credentials --input="$container_file" 2>&1 | grep -v "outside the supported range" || true
echo "Credential 'jobs-postgres (local)' (id jobsPostgres0001) is ready."
