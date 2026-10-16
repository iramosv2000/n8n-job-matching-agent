#!/usr/bin/env bash
# Smoke test for the running stack (used locally and by CI after `docker compose up --wait`).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }

echo "1/6 n8n readiness endpoint"
curl -fsS http://127.0.0.1:5678/healthz/readiness >/dev/null || fail "n8n is not ready"

echo "2/6 n8n stores its tables in schema 'n8n' (not public)"
psql() { docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "$1"; }
[[ "$(psql "select count(*) from information_schema.tables where table_schema='n8n'")" -gt 0 ]] \
  || fail "no n8n tables in schema n8n"
[[ "$(psql "select count(*) from information_schema.schemata where schema_name='jobs'")" -eq 1 ]] \
  || fail "schema jobs missing"

echo "3/6 migrations applied (jobs.runs, jobs.run_sources, jobs.offers)"
[[ "$(psql "select count(*) from information_schema.tables where table_schema='jobs'
             and table_name in ('runs','run_sources','offers')")" -eq 3 ]] || fail "jobs tables missing"

echo "4/6 matcher-service healthy and reachable from n8n"
docker compose exec -T n8n wget -qO- http://matcher:8000/health | grep -q '"status":"ok"' \
  || fail "matcher not reachable from n8n"

echo "5/6 workflows in Git import cleanly"
scripts/import_workflows.sh
expected=$(find workflows -maxdepth 1 -name '*.json' | wc -l | tr -d ' ')
actual=$(docker compose exec -T n8n n8n list:workflow 2>/dev/null | grep -c '|' || true)
[[ "$actual" -ge "$expected" ]] || fail "imported $actual workflow(s), expected $expected"

echo "6/6 exported JSON passes the secret and structure checks"
python3 scripts/check_workflows.py workflows

echo "SMOKE OK"
