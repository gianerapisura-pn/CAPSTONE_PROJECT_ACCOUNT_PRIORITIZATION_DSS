-- Keep source records and frozen model artifacts private in every project.
insert into storage.buckets (id, name, public)
values ('source-imports', 'source-imports', false),
       ('model-artifacts', 'model-artifacts', false)
on conflict (id) do nothing;

do $$
begin
  if exists (
    select 1 from storage.buckets
    where id in ('source-imports', 'model-artifacts') and public
  ) then
    raise exception 'PESLC storage buckets must remain private';
  end if;
end
$$;
