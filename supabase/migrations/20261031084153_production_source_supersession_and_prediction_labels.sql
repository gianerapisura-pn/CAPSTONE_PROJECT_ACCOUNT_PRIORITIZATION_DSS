set lock_timeout = '5s';
alter table public.import_batches drop constraint import_batches_status_check;
alter table public.import_batches add constraint import_batches_status_check check (status in ('previewed','committed','blocked_duplicate','failed','superseded'));
alter table public.future_transaction_predictions drop constraint future_transaction_predictions_predicted_class_check;
alter table public.future_transaction_predictions add constraint future_transaction_predictions_predicted_class_check check (predicted_class in ('Future Transaction','No Future Transaction','With Future Sales','With No Future Sales'));
alter table public.future_transaction_predictions drop constraint future_transaction_predictions_actual_class_check;
alter table public.future_transaction_predictions add constraint future_transaction_predictions_actual_class_check check (actual_class in ('Future Transaction','No Future Transaction','With Future Sales','With No Future Sales'));
comment on constraint import_batches_status_check on public.import_batches is 'Superseded source batches retain immutable raw rows and historical publications but are excluded from cumulative current-source reconstruction.';
