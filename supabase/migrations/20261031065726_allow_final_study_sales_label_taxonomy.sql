begin;
DO $guard$
DECLARE def text;
BEGIN
  select pg_get_constraintdef(oid) into def
  from pg_constraint
  where conrelid='public.predictive_study_predictions'::regclass
  and conname='predictive_study_predictions_predicted_class_check';
  IF def IS DISTINCT FROM 'CHECK ((predicted_class = ANY (ARRAY[''Future Transaction''::text, ''No Future Transaction''::text])))' THEN
     RAISE EXCEPTION 'Unexpected existing predictive label constraint; aborting: %',def;
  END IF;
END;
$guard$;
alter table public.predictive_study_predictions
 drop constraint predictive_study_predictions_predicted_class_check;
alter table public.predictive_study_predictions
 add constraint predictive_study_predictions_predicted_class_check
 check (predicted_class in (
 'Future Transaction','No Future Transaction','With Future Sales','With No Future Sales'
 ));
commit;
