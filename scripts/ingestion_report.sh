#!/usr/bin/env bash
# Arrival-rate report for M2-06: new offers per day and per source, from jobs.run_sources.
# Usage: scripts/ingestion_report.sh [days]   (default 14)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
days="${1:-14}"

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -v days="$days" <<'SQL'
\echo 'Runs per status (window)'
SELECT status, count(*) FROM jobs.runs
 WHERE started_at > now() - make_interval(days => :days) GROUP BY 1 ORDER BY 1;

\echo 'New offers per day and source (successful or partial runs)'
SELECT (r.started_at AT TIME ZONE 'America/Santiago')::date AS day, s.source,
       sum(s.new) AS new, sum(s.updated) AS updated, sum(s.fetched) AS fetched, sum(s.errors) AS errors
  FROM jobs.runs r JOIN jobs.run_sources s USING (run_id)
 WHERE r.started_at > now() - make_interval(days => :days) AND r.status IN ('succeeded', 'partial')
 GROUP BY 1, 2 ORDER BY 1, 2;

\echo 'Daily new offers per source: summary (the first day is excluded as a backfill)'
WITH daily AS (
  SELECT (r.started_at AT TIME ZONE 'America/Santiago')::date AS day, s.source, sum(s.new) AS new
    FROM jobs.runs r JOIN jobs.run_sources s USING (run_id)
   WHERE r.started_at > now() - make_interval(days => :days) AND r.status IN ('succeeded', 'partial')
   GROUP BY 1, 2
), ranked AS (
  SELECT *, row_number() OVER (PARTITION BY source ORDER BY day) AS n FROM daily
)
SELECT source, count(*) AS days, round(avg(new), 1) AS mean_new,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY new) AS median_new,
       min(new) AS min_new, max(new) AS max_new
  FROM ranked WHERE n > 1 GROUP BY source;
SQL
