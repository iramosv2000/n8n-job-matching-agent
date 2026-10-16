#!/usr/bin/env bash
# Import workflows/*.json into the running n8n.
# n8n deactivates workflows on import, so workflows that were active before are re-published
# afterwards and n8n is restarted to register their triggers again.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

container_dir=/tmp/wf-import
shopt -s nullglob
files=(workflows/*.json)
if (( ${#files[@]} == 0 )); then
  echo "No workflows to import."
  exit 0
fi

docker compose exec -T n8n sh -c "rm -rf $container_dir && mkdir -p $container_dir"
for f in "${files[@]}"; do
  docker compose cp "$f" "n8n:$container_dir/"
done
active_ids=$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT id FROM n8n.workflow_entity WHERE active" 2>/dev/null || true)

docker compose exec -T n8n n8n import:workflow --separate --input="$container_dir"

if [[ -n "${active_ids// /}" ]]; then
  for id in $active_ids; do
    docker compose exec -T -e N8N_RUNNERS_BROKER_PORT=5690 n8n n8n publish:workflow --id="$id" >/dev/null
    echo "Re-published previously active workflow $id"
  done
  docker compose restart n8n >/dev/null && docker compose up -d --wait >/dev/null
fi
