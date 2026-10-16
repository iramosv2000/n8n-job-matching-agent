-- migrate:up
-- Schema v1 (M2-01): ingestion runs and offers. See docs/data-model.md.

CREATE TABLE jobs.runs (
    run_id      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status      text        NOT NULL DEFAULT 'running'
                CHECK (status IN ('running', 'succeeded', 'partial', 'failed')),
    trigger     text        NOT NULL DEFAULT 'schedule'
                CHECK (trigger IN ('schedule', 'manual', 'test')),
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE jobs.run_sources (
    run_id       uuid NOT NULL REFERENCES jobs.runs (run_id) ON DELETE CASCADE,
    source       text NOT NULL,
    fetched      int  NOT NULL DEFAULT 0 CHECK (fetched >= 0),
    new          int  NOT NULL DEFAULT 0 CHECK (new >= 0),
    updated      int  NOT NULL DEFAULT 0 CHECK (updated >= 0),
    errors       int  NOT NULL DEFAULT 0 CHECK (errors >= 0),
    error_sample text,
    PRIMARY KEY (run_id, source)
);

CREATE TABLE jobs.offers (
    offer_id      text        PRIMARY KEY CHECK (offer_id ~ '^[a-z0-9_]+:.+$'),
    source        text        NOT NULL,
    url           text        NOT NULL,
    title         text        NOT NULL,
    company       text,
    location_raw  text,
    region        text,
    published_at  date,
    -- Plain text with contact data redacted by matcher-service (/normalize).
    description   text        NOT NULL DEFAULT '',
    -- Structured fields reported by the source (contract, modality, salary, ...).
    structured    jsonb       NOT NULL DEFAULT '{}'::jsonb,
    -- Unredacted source payload; purged after the retention period (data-governance.md).
    raw           jsonb,
    content_hash  text        NOT NULL,
    first_seen    timestamptz NOT NULL DEFAULT now(),
    last_seen     timestamptz NOT NULL DEFAULT now(),
    first_run_id  uuid        REFERENCES jobs.runs (run_id) ON DELETE SET NULL,
    duplicate_of  text        REFERENCES jobs.offers (offer_id) ON DELETE SET NULL,
    CHECK (duplicate_of IS NULL OR duplicate_of <> offer_id),
    CHECK (last_seen >= first_seen)
);

CREATE INDEX offers_first_seen_idx   ON jobs.offers (first_seen DESC);
CREATE INDEX offers_published_at_idx ON jobs.offers (published_at DESC);
CREATE INDEX offers_company_idx      ON jobs.offers (lower(company));

-- Retention: drop third-party text after N days, keep metadata (docs/data-governance.md §4).
CREATE FUNCTION jobs.purge_offer_texts(retention_days int DEFAULT 180) RETURNS int
LANGUAGE sql AS $$
    WITH purged AS (
        UPDATE jobs.offers
           SET description = '', raw = NULL
         WHERE last_seen < now() - make_interval(days => retention_days)
           AND (description <> '' OR raw IS NOT NULL)
        RETURNING 1
    )
    SELECT count(*)::int FROM purged;
$$;

-- migrate:down
DROP FUNCTION jobs.purge_offer_texts(int);
DROP TABLE jobs.offers;
DROP TABLE jobs.run_sources;
DROP TABLE jobs.runs;
