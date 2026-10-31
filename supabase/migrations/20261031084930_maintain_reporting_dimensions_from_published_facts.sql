set lock_timeout='5s';
insert into public.dim_invoice_date(date_key,year,month,quarter) select distinct si_date,extract(year from si_date)::int,extract(month from si_date)::int,extract(quarter from si_date)::int from public.invoice_groups where si_date is not null on conflict(date_key) do nothing;
insert into public.dim_collection_date(date_key,year,month,quarter) select distinct final_cr_date,extract(year from final_cr_date)::int,extract(month from final_cr_date)::int,extract(quarter from final_cr_date)::int from public.invoice_groups where final_cr_date is not null on conflict(date_key) do nothing;
insert into public.dim_record_status(status_key,description,analytically_eligible) select distinct payment_status,'Source payment status; invoice validity, reconciliation and account eligibility remain separate checks.',payment_status='Fully Paid' from public.invoice_groups on conflict(status_key) do nothing;
insert into public.dim_sensitivity_scenario(scenario_key,perturbation_level,iterations) select distinct on (s.weight_range) s.weight_range::text,s.weight_range,(s.payload->>'iterations')::int from public.sensitivity_results s join public.analytics_runs r using(analysis_run_id) where r.status='successful' order by s.weight_range,r.completed_at desc on conflict(scenario_key) do nothing;
create function public.maintain_invoice_reporting_dimensions() returns trigger language plpgsql security invoker set search_path=pg_catalog,public as $$ begin
if new.si_date is not null then insert into public.dim_invoice_date values(new.si_date,extract(year from new.si_date)::int,extract(month from new.si_date)::int,extract(quarter from new.si_date)::int) on conflict(date_key) do nothing; end if;
if new.final_cr_date is not null then insert into public.dim_collection_date values(new.final_cr_date,extract(year from new.final_cr_date)::int,extract(month from new.final_cr_date)::int,extract(quarter from new.final_cr_date)::int) on conflict(date_key) do nothing; end if;
insert into public.dim_record_status values(new.payment_status,'Source payment status; invoice validity, reconciliation and account eligibility remain separate checks.',new.payment_status='Fully Paid') on conflict(status_key) do nothing;
return new; end $$;
revoke all on function public.maintain_invoice_reporting_dimensions() from public,anon,authenticated;
create trigger maintain_invoice_reporting_dimensions before insert or update of si_date,final_cr_date,payment_status on public.invoice_groups for each row execute function public.maintain_invoice_reporting_dimensions();
create function public.maintain_sensitivity_reporting_dimension() returns trigger language plpgsql security invoker set search_path=pg_catalog,public as $$ begin
insert into public.dim_sensitivity_scenario(scenario_key,perturbation_level,iterations) values(new.weight_range::text,new.weight_range,(new.payload->>'iterations')::int) on conflict(scenario_key) do update set iterations=excluded.iterations;
return new; end $$;
revoke all on function public.maintain_sensitivity_reporting_dimension() from public,anon,authenticated;
create trigger maintain_sensitivity_reporting_dimension after insert or update of payload on public.sensitivity_results for each row execute function public.maintain_sensitivity_reporting_dimension();
comment on column public.dim_sensitivity_scenario.iterations is 'Most recently persisted configuration for this perturbation range; immutable historical iterations remain in each run-scoped sensitivity_results payload.';
alter table public.invoice_groups add constraint invoice_groups_invoice_date_dimension_fk foreign key(si_date) references public.dim_invoice_date(date_key);
alter table public.invoice_groups add constraint invoice_groups_collection_date_dimension_fk foreign key(final_cr_date) references public.dim_collection_date(date_key);
alter table public.invoice_groups add constraint invoice_groups_record_status_dimension_fk foreign key(payment_status) references public.dim_record_status(status_key);
