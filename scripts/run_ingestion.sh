#!/usr/bin/env bash
# Run WF-01 (Get on Board ingestion) once from the CLI and print a short summary.
# The n8n CLI prints the full execution data; it is kept in a temporary log, not on screen.
# A second task-broker port is needed because the n8n server in the container already uses 5679.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

log="$(mktemp -t wf01-run)"
if docker compose exec -T -e N8N_RUNNERS_BROKER_PORT=5690 n8n n8n execute --id=wf01IngestGoB001 >"$log" 2>&1 \
   && grep -q "Execution was successful" "$log"; then
  echo "WF-01 finished successfully."
else
  echo "WF-01 failed; execution log: $log" >&2
  grep -m3 '"message"' "$log" >&2 || true
  exit 1
fi
rm -f "$log"

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -c "
  SELECT (r.started_at AT TIME ZONE 'America/Santiago')::timestamp(0) AS started_santiago, r.status,
         extract(epoch FROM r.finished_at - r.started_at)::int AS seconds,
         s.fetched, s.new, s.updated, s.errors
    FROM jobs.runs r LEFT JOIN jobs.run_sources s USING (run_id)
   ORDER BY r.started_at DESC LIMIT 1;"
