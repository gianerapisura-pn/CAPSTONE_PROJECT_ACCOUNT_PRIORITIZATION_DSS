-- SI completeness is independent of the analysis reference and latest observed SI/CR.
-- Backend service credentials own writes; no browser role receives table access.
create table if not exists si_coverage_confirmations (
  confirmation_id uuid primary key,
  complete_through date not null,
  evidence_type text not null check (evidence_type in ('Client confirmation', 'Audited source reconciliation')),
  evidence_reference text not null check (length(btrim(evidence_reference)) > 0),
  evidence_basis text not null check (length(btrim(evidence_basis)) > 0),
  confirmed_on date check (confirmed_on >= complete_through),
  recorded_by uuid not null,
  recorded_at timestamptz not null default now(),
  source_batch_id uuid references import_batches(import_batch_id),
  source_package_hash varchar(64),
  constraint si_coverage_evidence_date check (confirmed_on is not null or source_package_hash is not null),
  supersedes_confirmation_id uuid references si_coverage_confirmations(confirmation_id),
  superseded_at timestamptz
);

create index if not exists si_coverage_active_through_idx
 on si_coverage_confirmations (complete_through desc) where superseded_at is null;

alter table si_coverage_confirmations enable row level security;
revoke all on si_coverage_confirmations from anon, authenticated;
