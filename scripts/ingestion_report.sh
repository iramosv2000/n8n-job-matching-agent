#!/usr/bin/env bash
# Ingestion report for M2-06 (arrival rate). Usage: scripts/ingestion_report.sh [days]  (default 14)
#
# Arrival is measured by PUBLICATION date, not by "new" rows per run: while a source has a
# backlog (pending > 0), "new" is censored by the per-run detail cap and mixes old offers with
# arrivals. A publication day counts as complete only if it is on or after the day the source's
# backlog first reached 0 and before the date of the latest successful run (offers published late
# in the day are picked up by the next day's run).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
days="${1:-14}"

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -v days="$days" <<'SQL'
\echo 'Runs per status (window)'
SELECT status, count(*) FROM jobs.runs
 WHERE started_at > now() - make_interval(days => :days) GROUP BY 1 ORDER BY 1;

\echo 'Per-run fetch statistics (sources with a detail cap); "capped" = backlog left after the run'
SELECT (r.started_at AT TIME ZONE 'America/Santiago')::timestamp(0) AS started_santiago, s.source,
       s.listed, s.candidates, s.skipped_known AS known, s.downloaded, s.new, s.pending, s.detail_cap AS cap,
       s.truncated_queries AS truncated, CASE WHEN s.pending > 0 THEN 'capped' ELSE '' END AS flag
  FROM jobs.runs r JOIN jobs.run_sources s USING (run_id)
 WHERE r.started_at > now() - make_interval(days => :days) AND s.candidates IS NOT NULL
 ORDER BY 1, 2;

\echo 'Offers published per day, complete days only (see header for the rule)'
WITH ok_runs AS (
    SELECT r.started_at, s.source, s.pending
      FROM jobs.runs r JOIN jobs.run_sources s USING (run_id)
     WHERE r.status IN ('succeeded', 'partial')
       AND s.source <> 'optional-sources'  -- pseudo-source that only records failed calls
), cleared AS (
    -- First run with no backlog. API sources (pending IS NULL) have no cap: their first run counts.
    SELECT source, (min(started_at) AT TIME ZONE 'America/Santiago')::date AS since
      FROM ok_runs WHERE coalesce(pending, 0) = 0 GROUP BY source
), latest AS (
    SELECT (max(started_at) AT TIME ZONE 'America/Santiago')::date AS day FROM ok_runs
)
SELECT o.source, o.published_at AS day, to_char(o.published_at, 'Dy') AS dow, count(*) AS published
  FROM jobs.offers o JOIN cleared c USING (source) CROSS JOIN latest l
 WHERE o.published_at >= c.since AND o.published_at < l.day AND o.duplicate_of IS NULL
 GROUP BY 1, 2, 3 ORDER BY 1, 2;

\echo 'Arrival rate summary over complete days (weekdays and weekends reported separately)'
WITH ok_runs AS (
    SELECT r.started_at, s.source, s.pending
      FROM jobs.runs r JOIN jobs.run_sources s USING (run_id)
     WHERE r.status IN ('succeeded', 'partial')
       AND s.source <> 'optional-sources'  -- pseudo-source that only records failed calls
), cleared AS (
    SELECT source, (min(started_at) AT TIME ZONE 'America/Santiago')::date AS since
      FROM ok_runs WHERE coalesce(pending, 0) = 0 GROUP BY source
), latest AS (
    SELECT (max(started_at) AT TIME ZONE 'America/Santiago')::date AS day FROM ok_runs
), calendar AS (
    SELECT c.source, d::date AS day
      FROM cleared c CROSS JOIN latest l, generate_series(c.since, l.day - 1, interval '1 day') AS d
), daily AS (
    SELECT k.source, k.day, count(o.offer_id) AS published,
           extract(isodow FROM k.day) BETWEEN 1 AND 5 AS weekday
      FROM calendar k
      LEFT JOIN jobs.offers o ON o.source = k.source AND o.published_at = k.day AND o.duplicate_of IS NULL
     GROUP BY 1, 2
)
SELECT source, CASE WHEN weekday THEN 'weekday' ELSE 'weekend' END AS kind, count(*) AS complete_days,
       round(avg(published), 1) AS mean, percentile_cont(0.5) WITHIN GROUP (ORDER BY published) AS median,
       min(published) AS min, max(published) AS max
  FROM daily GROUP BY 1, 2 ORDER BY 1, 2;
SQL
