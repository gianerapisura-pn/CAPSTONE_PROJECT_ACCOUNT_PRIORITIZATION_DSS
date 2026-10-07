-- PostgreSQL freezes SELECT * columns when a view is created. Migration 004
-- adds these fields to analytics_runs, then reads them through the existing
-- summary view. Add them first and append them to that view's column list.
alter table analytics_runs add column if not exists mcs_status text;
alter table analytics_runs add column if not exists context_metrics jsonb not null default '{}'::jsonb;

create or replace view reporting_latest_run_summary with (security_invoker = true) as
select * from analytics_runs
where status = 'successful'
order by completed_at desc
limit 1;
