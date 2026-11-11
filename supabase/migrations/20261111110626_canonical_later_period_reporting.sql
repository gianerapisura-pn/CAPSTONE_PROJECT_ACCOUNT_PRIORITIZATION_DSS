-- Preserve historical evaluations while reporting the package-verified evidence set.
create or replace view public.reporting_predictive_later_period_checks
with (security_invoker = true) as
select o.predictive_model_version_id, v.model_version, o.oop_cutoff, o.payload
from public.predictive_oop_evaluations o
join public.predictive_model_versions v using (predictive_model_version_id)
where v.status = 'active'
  and (
    nullif(o.payload ->> 'source_package_sha256', '') is not null
    or not exists (
      select 1
      from public.predictive_oop_evaluations verified
      where verified.predictive_model_version_id = o.predictive_model_version_id
        and nullif(verified.payload ->> 'source_package_sha256', '') is not null
    )
  );
