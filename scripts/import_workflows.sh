#!/usr/bin/env bash
# Import workflows/*.json into the running n8n. Imported workflows are inactive by default.
set -euo pipefail
cd "$(dirname "$0")/.."

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
docker compose exec -T n8n n8n import:workflow --separate --input="$container_dir"
