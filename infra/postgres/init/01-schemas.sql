-- Runs once, on the first start of an empty data volume.
-- n8n keeps its own tables in schema "n8n"; application data lives in "jobs" (ADR-0002).
CREATE SCHEMA IF NOT EXISTS n8n;
CREATE SCHEMA IF NOT EXISTS jobs;
