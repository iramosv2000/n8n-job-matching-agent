-- migrate:up
-- Fetch statistics for sources fetched through listings with a per-run detail cap (M2-06).
-- They tell whether a run's sample was limited by the cap (pending > 0) or by listing depth
-- (truncated_queries > 0), so the arrival rate is not inferred from capped "new" counts.
-- NULL = not applicable (API sources) or not recorded (runs before this migration).

ALTER TABLE jobs.run_sources
    ADD COLUMN listed            int CHECK (listed >= 0),
    ADD COLUMN candidates        int CHECK (candidates >= 0),
    ADD COLUMN skipped_known     int CHECK (skipped_known >= 0),
    ADD COLUMN downloaded        int CHECK (downloaded >= 0),
    ADD COLUMN pending           int CHECK (pending >= 0),
    ADD COLUMN detail_cap        int CHECK (detail_cap >= 0),
    ADD COLUMN truncated_queries int CHECK (truncated_queries >= 0);

COMMENT ON COLUMN jobs.run_sources.candidates IS 'Distinct offers within the day window seen in the listings';
COMMENT ON COLUMN jobs.run_sources.pending IS 'New candidates not downloaded because of detail_cap (backlog after the run)';
COMMENT ON COLUMN jobs.run_sources.truncated_queries IS 'Queries whose last listing page was full: more results exist beyond the page limit';

-- migrate:down
ALTER TABLE jobs.run_sources
    DROP COLUMN listed,
    DROP COLUMN candidates,
    DROP COLUMN skipped_known,
    DROP COLUMN downloaded,
    DROP COLUMN pending,
    DROP COLUMN detail_cap,
    DROP COLUMN truncated_queries;
