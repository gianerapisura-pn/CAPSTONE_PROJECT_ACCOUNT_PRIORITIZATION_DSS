-- The initial view selects the legacy table shape. Migration 002 replaces it
-- with a reordered projection, which PostgreSQL cannot CREATE OR REPLACE.
drop view if exists reporting_latest_account_priorities;
