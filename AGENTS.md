# PESLC Account Prioritization DSS

Read docs/ARCHITECTURE.md, docs/CAPSTONE_METHOD.md, docs/FUTURE_DATA_CONTINUITY.md, docs/POWER_BI_SETUP.md, and docs/IMPLEMENTATION_PLAN.md first.

Commands:
- Backend tests: cd backend; python -m pytest
- Frontend tests: cd frontend; npm test
- Backend dev: cd backend; uvicorn app.main:app --reload
- Frontend dev: cd frontend; npm run dev

Non-negotiable rules:
1. Never hardcode the system lifetime, account list, Priority Groups, current results, or fixed RFM/Settlement weights.
2. Inactivity Risk and Lower/Higher are not active constructs.
3. The predictive target is 12-month Future Transaction versus No Future Transaction.
4. Prediction never determines Final Priority Score, rank, or Priority Group.
5. RFM is descriptive and is not the predictive target.
6. Descriptive, predictive, and prescriptive branches remain separate.
7. Power BI is reporting only.
8. Future compatible data must work without redesign.
9. Never automatically fuzzy-merge accounts.
10. Never use post-cutoff evidence in predictive features or final OOP data for tuning.
11. Identify cancelled records before generic missing-data logic.
12. Multiple collection rows for one SI must not inflate Frequency or Monetary.
13. Production authentication cryptographically verifies Supabase sessions and database roles.
14. Preview and COMMITTED are distinct; successful analytical runs are immutable and atomically published.
15. Demo persistence/authentication remains visibly isolated.
16. Logical invoice identity excludes import batch, worksheet, and row lineage.
17. Routine imports score only with the active hash-verified extra_trees_stage8 artifact; retraining is separate and controlled.
18. Analysis reference date is explicit and must cover accepted SI and final CR evidence.
19. Only explicitly verified B2B accounts enter the analytical population.
20. B2B descriptive/predictive eligibility and current Client-Confirmed Active prescriptive actionability remain separate.
21. Published runs read immutable run-scoped account context, not mutable live account context.
