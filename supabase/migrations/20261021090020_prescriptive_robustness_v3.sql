create or replace view reporting_prescriptive_validation_evidence with (security_invoker = true) as
select evidence_version,evidence_scope,comparator,payload,source_package_hash,registered_at
from prescriptive_validation_evidence
where evidence_version='prescriptive-robustness-final-v3';

drop policy if exists "reporting reader prescriptive validation evidence" on prescriptive_validation_evidence;
create policy "reporting reader prescriptive validation evidence" on prescriptive_validation_evidence
 for select to peslc_reporting_reader
 using (evidence_version='prescriptive-robustness-final-v3');
