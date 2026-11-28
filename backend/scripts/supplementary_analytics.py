"""Reproduce supplementary research without modifying the locked input archive.

Usage: python supplementary_analytics.py --source SOURCE.zip --output RESULTS
Python standard library only. Does not train, publish, or connect to a database.
"""
import argparse
import calendar
import csv
from datetime import date
from decimal import Decimal
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import zipfile
from collections import defaultdict

SOURCE_HASH = "972f91f4bf96aa735688f1a35b702b68319fcb5602356961a1e209fd2190eb65"
D = Decimal


def reproduce(source: Path, output: Path):
    content = source.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != SOURCE_HASH:
        raise ValueError("This research reproduction requires the verified study archive.")
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if archive.testzip() is not None:
            raise ValueError("Invalid archive integrity.")
        def read(suffix):
            names = [n for n in archive.namelist() if n.endswith(suffix)]
            if len(names) != 1:
                raise ValueError(f"Expected one member: {suffix}")
            return list(csv.DictReader(io.StringIO(archive.read(names[0]).decode("utf-8-sig"))))
        invoices = read("/03_INVOICES/invoices.csv")
        baseline = read("/04_DESCRIPTIVE/annual_baseline.csv")
        priorities = {r["account_key"]: r for r in read("/06_PRIORITY/current_priority.csv")}
        statuses = {r["account_key"]: r["account_status"] for r in read("/01_ACCOUNTS/account_status.csv")}
        ranks = read("/08_BACKTEST/rankings.csv")
        selected = read("/08_BACKTEST/selected.csv")
        summary = read("/08_BACKTEST/summary.csv")
        outer = read("/05_BENCHMARK/outer_predictions.csv")
        recency_reference = read("/08_BACKTEST/recency_only_benchmark.csv")
        weighting_reference = read("/01_WEIGHTING/backtest.csv")
        aggregation_reference = read("/02_AGGREGATION/backtest.csv")
        inventory = [{"member": n, "bytes": archive.getinfo(n).file_size,
                      "sha256": hashlib.sha256(archive.read(n)).hexdigest()}
                     for n in archive.namelist() if not n.endswith("/")]
    def write(name, rows):
        if not rows:
            return
        with (output / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    if len({r["invoice_key"] for r in invoices}) != len(invoices):
        raise ValueError("Duplicate logical invoice identity.")
    annual = defaultdict(lambda: D(0))
    count = defaultdict(int)
    names = {}
    for row in invoices:
        key = int(row["si_date"][:4]), row["account_key"]
        annual[key] += D(row["si_amount"]); count[key] += 1
        names[row["account_key"]] = row["account_name"]
    annual_rows = [{"year": y, "account_key": a, "account_name": names[a],
                    "sales": str(amount.quantize(D(".01"))), "invoice_count": count[y, a]}
                   for (y, a), amount in sorted(annual.items())]
    for row in baseline:
        total = sum((v for (y, _), v in annual.items() if y == int(row["year"])), D(0))
        assert total.quantize(D(".01")) == D(row["all_recorded_sales"]).quantize(D(".01"))
    comparisons, account_rows = [], []
    years = sorted(int(r["year"]) for r in baseline if r["period_status"] == "Complete year")
    for year in years:
        if year - 1 not in years:
            continue
        prev = {a for (y, a) in annual if y == year - 1}
        curr = {a for (y, a) in annual if y == year}
        prev_total = sum((annual[year - 1, a] for a in prev), D(0))
        curr_total = sum((annual[year, a] for a in curr), D(0))
        groups = [("Purchased in both years", prev & curr), ("Previous year only", prev - curr),
                  ("Current year only", curr - prev)]
        net = D(0)
        for group, accounts in groups:
            before = sum((annual.get((year - 1, a), D(0)) for a in accounts), D(0))
            after = sum((annual.get((year, a), D(0)) for a in accounts), D(0))
            net += after - before
            comparisons.append({"previous_year": year - 1, "current_year": year, "group": group,
                "account_count": len(accounts), "previous_sales": str(before), "current_sales": str(after),
                "change": str(after - before), "previous_share_pct": float(before / prev_total * 100) if prev_total else None,
                "current_share_pct": float(after / curr_total * 100) if curr_total else None,
                "previous_total": str(prev_total), "current_total": str(curr_total)})
            for account in sorted(accounts):
                p, c = annual.get((year - 1, account), D(0)), annual.get((year, account), D(0))
                current = priorities.get(account, {})
                account_rows.append({"previous_year": year - 1, "current_year": year, "account_key": account,
                    "account_name": names[account], "group": group, "previous_sales": str(p),
                    "current_sales": str(c), "change": str(c - p),
                    "previous_share_pct": float(p / prev_total * 100) if prev_total else None,
                    "current_share_pct": float(c / curr_total * 100) if curr_total else None,
                    "current_priority_rank": current.get("priority_rank"),
                    "current_priority_group": current.get("priority_group"),
                    "current_final_priority_score": current.get("final_priority_score"),
                    "current_account_status": statuses.get(account),
                    "current_is_ranked": bool(current),
                    "current_predicted_target": current.get("predicted_target"),
                    "current_analysis_reference": current.get("analysis_reference")})
        assert net == curr_total - prev_total
        # Independent invoice-stream calculation, not the account-year aggregation.
        direct = sum((D(r["si_amount"]) * (1 if int(r["si_date"][:4]) == year else -1)
                      for r in invoices if int(r["si_date"][:4]) in (year - 1, year)), D(0))
        assert direct == net
    buyers_rows, breadth_rows, monetary_rows, comparator_reference = [], [], [], []
    for cutoff in sorted({r["cutoff"] for r in ranks}):
        ranked = [r for r in ranks if r["cutoff"] == cutoff]
        ranked.sort(key=lambda r: (int(r["historical_rank"]), r["account_key"]))
        eligible = {r["account_key"] for r in ranked}
        chosen = {r["account_key"] for r in selected if r["cutoff"] == cutoff}
        end = ranked[0]["evaluation_end"]
        buyers = {r["account_key"] for r in invoices if cutoff < r["si_date"] <= end} & eligible
        # Independently reconcile saved future-sales outcomes to invoice-date evidence.
        for r in ranked:
            future = sum((D(i["si_amount"]) for i in invoices
                          if i["account_key"] == r["account_key"] and cutoff < i["si_date"] <= end), D(0))
            assert future.quantize(D(".01")) == D(r["future_sales_12m"]).quantize(D(".01"))
        def metrics(keys):
            total = sum((D(r["future_sales_12m"]) for r in ranked), D(0))
            sales = sum((D(r["future_sales_12m"]) for r in ranked if r["account_key"] in keys), D(0))
            hit = len(keys & buyers); k = len(keys); n = len(eligible)
            return {"N": n, "K": k, "buyers": len(buyers), "captured_buyers": hit,
                "precision_at_K": hit / k if k else None, "recall_at_K": hit / len(buyers) if buyers else None,
                "buyer_prevalence": len(buyers) / n, "selected_share": k / n,
                "future_sales_total": str(total), "selected_future_sales": str(sales),
                "sales_capture": float(sales / total) if total else None,
                "sales_lift": float(sales / total) / (k / n) if total and k else None}
        official = metrics(chosen)
        saved = next(r for r in summary if r.get("cutoff", r.get("cutoff_date")) == cutoff)
        # Field names differ between evidence versions; compare only the exact locked contract.
        lift_field = next((k for k in saved if "lift" in k and "mean" not in k), None)
        if lift_field and saved[lift_field]:
            assert math.isclose(official["sales_lift"], float(saved[lift_field]), abs_tol=1e-10)
        buyers_rows.append({"cutoff": cutoff, "evaluation_end": end, **official})
        for fraction in (.05, .10, .20, .30):
            target = max(1, math.ceil(len(ranked) * fraction)); boundary = float(ranked[target - 1]["historical_fps"])
            keys = {r["account_key"] for r in ranked
                    if float(r["historical_fps"]) > boundary or abs(float(r["historical_fps"]) - boundary) <= 1e-12}
            breadth_rows.append({"cutoff": cutoff, "illustrative_fraction": fraction, **metrics(keys)})
        origin = date.fromisoformat(cutoff)
        lower = date(origin.year - 2, origin.month, min(origin.day, calendar.monthrange(origin.year - 2, origin.month)[1])).isoformat()
        monetary = {a: sum((D(r["si_amount"]) for r in invoices
                           if r["account_key"] == a and lower < r["si_date"] <= cutoff), D(0)) for a in eligible}
        # Match actual official K. Stable canonical ID resolves exact Monetary ties.
        ordered = sorted(eligible, key=lambda a: (-monetary[a], a))
        money_keys = set(ordered[:len(chosen)])
        monetary_rows.append({"cutoff": cutoff, "tie_rule": "Exact K; Monetary24m descending then canonical account ID",
                              **metrics(money_keys), "official_mcs_lift": official["sales_lift"],
                              "overlap_with_official_count": len(money_keys & chosen),
                              "overlap_with_official_share": len(money_keys & chosen) / len(chosen),
                              "random_expected_sales_capture": len(chosen) / len(eligible),
                              "random_expected_buyer_precision": len(buyers) / len(eligible),
                              "random_expected_buyer_recall": len(chosen) / len(eligible)})
        # Reference the existing comparisons without retuning or replacing their tie rules.
        def reference(method, n, k, capture, lift, scope):
            comparator_reference.append({"cutoff": cutoff, "method": method, "N": n, "K": k,
                "sales_capture": capture, "sales_lift": lift,
                "matched_to_official_N_and_K": n == len(eligible) and k == len(chosen), "scope": scope})
        reference("CRITIC-MCS", len(eligible), len(chosen), official["sales_capture"], official["sales_lift"], "Official saved selection")
        monetary_metrics = metrics(money_keys)
        reference("Monetary24m-only", len(eligible), len(money_keys), monetary_metrics["sales_capture"], monetary_metrics["sales_lift"], "Supplementary exact-K comparator")
        recent = next(r for r in recency_reference if int(r["year"]) == origin.year)
        reference("Recency-only", int(recent["eligible_accounts"]), int(recent["selected_accounts"]),
                  float(recent["recency_only_capture"]), float(recent["recency_only_lift"]), recent["comparison_scope"])
        for r in weighting_reference + aggregation_reference:
            if r["cutoff"] == cutoff and r["method"] not in {"CRITIC", "MCS", "Additive MCS"}:
                reference(r["method"], int(r["eligible_account_count"]), int(r["selected_count_after_ties"]),
                          float(r["capture_rate"]), float(r["lift_over_expected_random"]), "Preserved original comparison and original tie rules")
    write("annual_account_sales.csv", annual_rows)
    write("sales_group_decomposition.csv", comparisons)
    write("account_sales_changes.csv", account_rows)
    write("buyer_top_k.csv", buyers_rows)
    write("illustrative_selection_breadth.csv", breadth_rows)
    write("monetary_only_comparison.csv", monetary_rows)
    write("existing_comparator_reference.csv", comparator_reference)
    report = {"source_sha256": digest, "logical_invoices": len(invoices),
        "source_sales_total": str(sum((D(r["si_amount"]) for r in invoices), D(0))),
        "annual_comparisons": len(comparisons) // 3, "historical_cutoffs": len(buyers_rows),
        "mean_precision_at_K": statistics.mean(r["precision_at_K"] for r in buyers_rows),
        "mean_recall_at_K": statistics.mean(r["recall_at_K"] for r in buyers_rows),
        "pooled_precision_at_K": sum(r["captured_buyers"] for r in buyers_rows) / sum(r["K"] for r in buyers_rows),
        "pooled_recall_at_K": sum(r["captured_buyers"] for r in buyers_rows) / sum(r["buyers"] for r in buyers_rows),
        "mean_official_lift_reconciled_cents": statistics.mean(r["sales_lift"] for r in buyers_rows),
        "mean_official_lift_locked": statistics.mean(float(r["lift_over_expected_random"]) for r in summary),
        "mean_monetary_only_lift": statistics.mean(r["sales_lift"] for r in monetary_rows),
        "pr_ap_decision": "Excluded: locked outer predictions contain labels only, not out-of-sample continuous scores. No surrogate in-sample score or new model-selection run is introduced.",
        "outer_prediction_columns": list(outer[0]),
        "scope": "Research-only additions. No model training, method selection, operational contact-capacity claim, or forecast-outcome evaluation."}
    (output / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "source_inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.source, args.output), indent=2))
