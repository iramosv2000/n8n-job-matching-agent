#!/usr/bin/env bash
# Export every n8n workflow into workflows/ (one normalised JSON file per workflow, ADR-0006).
set -euo pipefail
cd "$(dirname "$0")/.."

container_dir=/tmp/wf-export
staging=.wf-export

docker compose exec -T n8n sh -c "rm -rf $container_dir && n8n export:workflow --backup --output=$container_dir"
rm -rf "$staging" && mkdir -p "$staging"
docker compose cp "n8n:$container_dir/." "$staging/"
python3 scripts/normalize_workflows.py "$staging" workflows
rm -rf "$staging"
python3 scripts/check_workflows.py workflows
git status --short workflows
