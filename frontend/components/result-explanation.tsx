"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { AccountDecisionRow } from "@/types/dss";

export type ResultExplanation = {
  title: string;
  basis: string;
  calculation?: string;
  inputs?: string[];
  note?: string;
  source?: string;
  interpretation?: string;
};

type Criterion = "recency" | "frequency" | "monetary" | "settlement";
const criteria: Criterion[] = ["recency", "frequency", "monetary", "settlement"];
const decimal = (value: number | null | undefined, places = 4) => value == null ? "Unavailable" : value.toFixed(places);

export function priorityExplanation(row?: Partial<AccountDecisionRow> | null): ResultExplanation {
  const contributions = row && criteria.map(key => row[`${key}_contribution`]);
  const hasContributions = contributions?.every(value => typeof value === "number");
  return {
    title: "Final Priority Score",
    basis: "Review order for active, verified business accounts. It uses four measures from saved invoice and payment records, not the Future Sales prediction.",
    calculation: "Add each 0-to-1 measure multiplied by its published weight: Recency + Frequency + Monetary + Settlement.",
    inputs: hasContributions ? criteria.map(key => `${key[0].toUpperCase() + key.slice(1)}: ${decimal(row?.[`normalized_${key}`])} x ${decimal(row?.[`baseline_${key}_weight`])} = ${decimal(row?.[`${key}_contribution`])}`) : undefined,
    note: hasContributions ? `Published score: ${decimal(row?.final_priority_score)}. Displayed inputs are rounded; the saved score uses full precision.` : "Weights come from how much each measure varies and differs from the others. Open account details for the four saved values and weights.",
  };
}

export function resultExplanation(key: string, row?: Partial<AccountDecisionRow> | null): ResultExplanation {
  if (key === "fps" || key === "score") return priorityExplanation(row);
  if (key.startsWith("normalized_")) {
    const criterion = key.slice(11) as Criterion;
    const cost = criterion === "recency" || criterion === "settlement";
    return {
      title: `Normalized ${criterion}`,
      basis: `The account's ${criterion} is converted to a 0-to-1 scale using the accounts eligible for this saved ranking. ${cost ? "Fewer days score higher." : "A larger original value scores higher."}`,
      calculation: cost ? "(largest eligible value - this account's value) / (largest - smallest eligible value)" : "(this account's value - smallest eligible value) / (largest - smallest eligible value)",
      note: "If all eligible accounts have the same value, each receives 0.5. The smallest and largest source values are not shown here.",
    };
  }
  if (key.startsWith("contribution_")) {
    const criterion = key.slice(13) as Criterion;
    return {
      title: `${criterion[0].toUpperCase() + criterion.slice(1)} contribution`,
      basis: `This is the part of this account's Final Priority Score contributed by ${criterion}.`,
      calculation: `0-to-1 ${criterion} value x saved ${criterion} weight`,
      inputs: row ? [`${decimal(row[`normalized_${criterion}`])} x ${decimal(row[`baseline_${criterion}_weight`])} = ${decimal(row[`${criterion}_contribution`])}`] : undefined,
      note: "The four full-precision contributions are added. The Future Sales prediction is not included.",
    };
  }
  const explanations: Record<string, ResultExplanation> = {
    reference: { title: "Analysis reference", basis: "This is the last date through which Sales Invoice data were confirmed complete for this published analysis.", note: "The system uses only evidence available by this date. A later payment receipt alone does not prove that later sales data are complete." },
    study_origin: { title: "Study forecast date", basis: "The study used Sales Invoices known by December 31, 2025 to predict whether each eligible account would buy in the following 12 months.", note: "This saved study forecast does not change when newer data are imported." },
    run: { title: "Published run", basis: "This identifies one saved analysis and when it finished.", note: "Changing a page filter changes what you see, not the saved analysis or its scores." },
    duration: { title: "Time taken to run", basis: "How long this saved analysis took to finish.", calculation: "Finish time - start time", note: "This is processing time, not an account score." },
    warnings: { title: "Run warnings", basis: "Number of data or calculation warnings saved with this analysis.", calculation: "Count the saved warning messages.", note: "Zero warnings alone does not prove that the source is complete or the forecast is accurate." },
    import_rows: { title: "Discovered source rows", basis: "Number of rows read from the uploaded file before the checks finished.", note: "Being read does not mean a row was accepted as a sale or payment." },
    import_accepted: { title: "Accepted source rows", basis: "Rows that passed the relevant file checks and can enter the saved source records.", note: "Several payment rows for one Sales Invoice still count as one purchase and one invoice amount." },
    import_flagged: { title: "Flagged source rows", basis: "Rows marked for review because a file check found a possible issue.", note: "The system does not quietly treat flagged rows as clean evidence." },
    import_excluded: { title: "Excluded source rows", basis: "Rows left out of analysis because they do not meet the import rules.", note: "The downloadable issue report gives the row-specific reason." },
    import_cancelled: { title: "Cancelled records", basis: "Rows marked cancelled before the system checks ordinary missing fields.", note: "A cancelled Sales Invoice is not counted as a sale or purchase." },
    import_quarantined: { title: "Quarantined rows", basis: "Rows set aside for an administrator to resolve before they can be published.", note: "The preview does not publish them or start a saved analysis." },
    import_blocked: { title: "Blocked rows", basis: "Rows the current file rules do not allow the system to publish.", note: "Open the issue report to see why each row was blocked." },
    quality_rate: { title: "File-check percentage", basis: "The percentage reported for this check on the uploaded file.", note: "Different checks may cover different rows. Preview results are not yet published analysis." },
    preview_si_date: { title: "Latest invoice date in this preview", basis: "The newest eligible Sales Invoice date found in the uploaded file so far.", note: "Seeing this date does not prove that all invoices through that date were supplied." },
    preview_cr_date: { title: "Latest payment evidence in this preview", basis: "The newest valid Collection Receipt date found in the uploaded file so far.", note: "A later payment receipt does not prove that later Sales Invoice records are complete." },
    historical: { title: "Historical identities", basis: "Count of different account identities found in the historical source records.", note: "Some may not be verified business customers or eligible for today's ranking." },
    b2b: { title: "Verified business customers", basis: "Count of accounts the client confirmed as business-to-business (B2B) customers in the saved records.", note: "An account without this confirmation is not included just because its name looks like a company." },
    sales: { title: "Valid historical sales", basis: "Add the amounts of accepted Sales Invoices. Each invoice is counted once.", note: "More than one payment row for an invoice does not repeat its sale amount. This total is background business context, not the Final Priority Score by itself." },
    actionable: { title: "Current actionable accounts", basis: "Count of verified business customers whose client-confirmed status is Active at this analysis date.", note: "Active status decides whether an account may be ranked; it does not add points to its score." },
    status: { title: "Recorded account status", basis: "The status the client confirmed for this account when the analysis was saved.", note: "It is not guessed by the model. Active status allows current prioritization but does not add score points." },
    provenance: { title: "Verified account details", basis: "The account name, business category, type, and verification details saved with this analysis.", note: "These are checked source details, not values computed from invoice amounts or guessed from a name." },
    ranked_count: { title: "Ranked accounts", basis: "Count of active, verified business accounts with all four measures needed for a saved priority rank.", note: "An unranked account can still appear in historical views. Page filters do not create new ranks." },
    group_count: { title: "Accounts in this priority group", basis: "How many ranked accounts are in this High, Medium, or Low management-review group.", calculation: "Sort eligible accounts by saved Final Priority Score; split the list into near thirds without separating exact score ties.", note: "Business type and Future Sales prediction do not set the group." },
    rank: { title: "Published rank", basis: "The account's place when eligible accounts are ordered from highest to lowest Final Priority Score.", calculation: "Accounts with exactly equal original scores share a rank. For example, if two share #2, the next is #4.", note: "The displayed scores are rounded, so two that look equal may have different original values." },
    model_rank: { title: "Model comparison place", basis: "Where this prediction model placed when candidate models were compared on past years.", note: "This is not an account rank or proof of how the pending forecast will perform." },
    group: { title: "Priority Group", basis: "High, Medium, or Low tells management which ranked accounts to review first, based on the saved score order.", calculation: "The ordered list is divided near thirds; accounts with exactly equal scores stay together at a boundary.", note: "This is a relative review group, not the chance that an account will buy again." },
    prediction: { title: "12-month sales prediction", basis: "The saved CatBoost model uses seven measures from past invoice and payment records to classify whether an eligible account may have a valid Sales Invoice in the next 12 months.", calculation: "Use records known by the stated analysis date; return With Future Sales or With No Future Sales for the next 12 months.", note: "This is not a confirmed sale or an account-closure label. It never changes the priority score, rank, or group." },
    prediction_count: { title: "Number of predicted cases", basis: "How many account-and-date cases the model placed in each future-sales class during the historical test.", calculation: "Count cases predicted in each class.", note: "A case is a prediction at one date, not necessarily a different company or a confirmed sale." },
    model: { title: "Selected predictive model", basis: "The approved CatBoost model chosen after testing candidate models on earlier time periods.", note: "Routine imports use this same verified model; they do not train a replacement. Its predictions do not decide the Final Priority Score." },
    horizon: { title: "Prediction window comparison", basis: "Earlier tests compared predictions for the next 3, 6, and 12 months using the same Extra Trees test model.", note: "The approved forecast covers 12 months and now uses CatBoost. These tests do not tell us what will actually happen in the coming year." },
    benchmark: { title: "Historical model comparison", basis: "Candidate prediction models were tested on later historical years, with each test year counted equally.", calculation: "Find each year's Macro F1 score (average performance across both classes), then average the yearly scores.", note: "CatBoost was selected. A small past advantage is not a guarantee for future data." },
    lookback: { title: "Historical lookback", basis: "How far into the past the test looked when preparing a candidate model's input measures.", note: "This is different from the 12 months into the future that the model tries to classify. It does not retrain the approved model." },
    recency: { title: "Recency", basis: "How many days have passed since this account's most recent valid Sales Invoice.", calculation: "Analysis reference date - latest valid Sales Invoice date", inputs: row?.latest_valid_si_date && row.analysis_reference_date ? [`${row.analysis_reference_date} - ${row.latest_valid_si_date}`] : undefined, note: "Fewer days means the account bought more recently. Only invoices available by the analysis date are used." },
    latest_si: { title: "Latest valid Sales Invoice", basis: "This account's newest accepted invoice date on or before the saved analysis date.", note: "The number of days since this date becomes Recency. The date itself is not a score." },
    invoice: { title: "Invoice or payment record", basis: "An accepted Sales Invoice or Collection Receipt in the current source records.", note: "These source records can change with later imports; a published analysis keeps its own saved snapshot. Several receipts may pay one invoice." },
    frequency: { title: "Purchases in the last 24 months", basis: "Number of different valid Sales Invoices dated within the 24 months ending on the analysis date.", calculation: "Count each eligible invoice once when it falls inside the 24-month window.", note: "Several payment records for one invoice do not create extra purchases. This is different from the all-history RFM count." },
    monetary: { title: "Sales value in the last 24 months", basis: "Total value of valid Sales Invoices in the 24 months ending on the analysis date.", calculation: "Add each eligible invoice amount once within the 24-month window.", note: "Payment records do not multiply an invoice's sale value. This differs from the all-history RFM amount." },
    rfm_frequency: { title: "All-history purchase count", basis: "How many different valid Sales Invoices this account has through the analysis date.", calculation: "Count each invoice once, even when it has several payment records." },
    rfm_monetary: { title: "All-history sales amount", basis: "Total amount of this account's valid Sales Invoices through the analysis date.", calculation: "Add each accepted invoice amount once." },
    rfm_score: { title: "Past-activity score (1 to 5)", basis: "Compares one account with other eligible business customers on Recency (how recently), Frequency (how often), or Monetary (how much).", calculation: "Sort each measure and use the 20%, 40%, 60%, and 80% boundaries. More recent, more frequent, or higher-value buying scores higher; ties stay together.", note: "If all values match, each account gets 3. These all-history scores are not the final priority formula." },
    rfm_mean: { title: "Average past-activity score", basis: "Average of the three all-history Recency, Frequency, and Monetary scores.", calculation: row ? `(${row.r_score ?? "R"} + ${row.f_score ?? "F"} + ${row.m_score ?? "M"}) / 3` : "(Recency score + Frequency score + Monetary score) / 3", note: "This describes past sales activity; it is neither the 12-month prediction nor the Final Priority Score." },
    settlement: { title: "Average Settlement Days", basis: "Average days from invoice date until the final valid payment receipt for invoices that can be matched and fully settled.", calculation: "Add the eligible invoice-to-final-payment durations, then divide by the number of eligible settled invoices.", note: "This measures past collection time, not whether payment broke a contract. Missing payment evidence is not treated as zero days." },
    settlement_count: { title: "Eligible settled invoices", basis: "Number of invoices that can be matched to their final valid payment date without a negative date gap.", note: "Several payment rows may belong to one invoice, which is still counted once." },
    settlement_max: { title: "Longest observed settlement", basis: "The longest invoice-to-final-payment time recorded for an eligible invoice from this account.", note: "This does not say whether the payment was late under its contract." },
    weight: { title: "Saved priority weight", basis: "The share assigned to one of four measures when the system builds the Final Priority Score for eligible accounts.", calculation: "CRITIC compares how much each measure varies across eligible accounts and how much new information it adds; divide its information by the total.", note: "Weights are saved with the run. Page filters do not change them, and they are not CatBoost prediction factors." },
    spearman: { title: "Spearman rank similarity", basis: "Shows how similar the account order is before and after a test change. A value near 1 means the order stayed similar.", calculation: "Compare the two lists of ranks; accounts tied in rank use their shared average position.", note: "This tests ranking stability. It does not predict future sales or prove the ranking will stay the same under every change." },
    movement: { title: "Priority Group movement rate", basis: "Percentage of eligible accounts that moved to a different High, Medium, or Low group in the test scenario.", calculation: "Accounts that changed group / all compared eligible accounts", note: "The test does not replace the published Priority Groups." },
    movement_count: { title: "Priority Group changes", basis: "Number of eligible accounts that moved to a different group when the named test changed the calculation.", calculation: "Count accounts whose test group differs from their saved group.", note: "The saved groups are not replaced by this test." },
    weight_change: { title: "Largest weight change in this test", basis: "Shows whether leaving out this one account would noticeably change any of the four priority weights.", calculation: "For each weight, find the gap between the test and saved value; show the biggest gap.", note: "This is a check only. It does not replace the saved weights." },
    recomputed_weights: { title: "Weights without one account", basis: "The four weights the method would produce if the named account were left out of this test.", note: "These are test-only values. Saved weights and priority scores remain unchanged." },
    agreement: { title: "Priority Group agreement", basis: "Percentage of eligible accounts put in the same group by the saved method and the named alternative method.", calculation: "Accounts with the same group in both methods / all compared accounts", note: "Alternative-method groups are used to check robustness, not to replace the saved groups." },
    rank_range: { title: "Rank range in tests", basis: "The lowest and highest place this account reached across the recorded weight-change tests.", note: "These are test results; the saved account rank is unchanged." },
    rank_movement: { title: "Largest rank movement", basis: "The biggest number of places this account moved from its saved rank in any recorded test.", calculation: "Find the largest absolute difference between a test rank and the saved rank.", note: "The saved rank does not change." },
    scenarios: { title: "Sensitivity scenarios", basis: "Tests that slightly change the four priority weights to see whether account ranks and groups stay stable.", calculation: "100 recorded tests at each weight-change range: +/-10%, +/-20%, +/-30%, and +/-40%. Add the recorded counts for the total.", note: "The page shows saved test results; moving the cursor does not run a new simulation." },
    perturbation: { title: "Weight-change test range", basis: "How much the test was allowed to vary the saved weights while checking whether rankings stayed stable.", note: "This is only a test setting; it is not a new saved weight." },
    capture: { title: "Future-sales value captured", basis: "Of the sales value recorded after a historical test date, this is the share from accounts selected at the top of the list.", calculation: "Next-12-month Sales Invoice value from selected accounts / next-12-month value from all eligible accounts", note: "This describes past test periods. It does not mean contacting those accounts caused the sales." },
    random: { title: "Random-selection baseline", basis: "The share of accounts selected, used as a simple comparison for historical sales capture.", calculation: "Selected accounts (k) / all eligible accounts (n)", note: "For example, choosing 10 of 100 accounts gives a 10% baseline. No random drawing is run here." },
    lift: { title: "Lift versus random", basis: "Shows how the selected accounts' historical future-sales share compares with the share expected from selecting the same number of accounts at random.", calculation: "Selected accounts' future-sales value share / (selected accounts / eligible accounts)", note: "Above 1 means higher historical capture than this baseline. It does not prove that contacting those accounts caused the sales." },
    macro_f1: { title: "Macro F1", basis: "A historical model-check score that gives equal importance to finding Future Sales and No Future Sales cases.", calculation: "(Future Sales F1 + No Future Sales F1) / 2. Each class F1 = 2 x precision x recall / (precision + recall).", note: "This comes from labelled past periods, not from already knowing the results of a pending future forecast." },
    f1: { title: "Future Sales F1", basis: "A historical model-check score balancing how many Future Sales alerts were right and how many actual Future Sales cases were found.", calculation: "2 x precision x recall / (precision + recall)", note: "This is historical validation, not realized accuracy of a pending forecast." },
    balanced_accuracy: { title: "Balanced accuracy", basis: "How often the model correctly finds each of the two historical classes, giving both classes equal importance.", calculation: "(Future Sales recall + No Future Sales recall) / 2", note: "This does not mean the source data contain equal numbers of both classes." },
    mcc: { title: "Matthews correlation coefficient", basis: "A score for a past model test that considers correct and incorrect predictions for both Future Sales and No Future Sales. Closer to 1 is better; 0 is roughly chance-level.", calculation: "(correct Future x correct No Future - false Future x missed Future) / square root of the four related row and column totals", note: "This is historical test performance, not proof that a new forecast is correct. When the formula cannot be divided, the saved evaluator's rule applies." },
    accuracy: { title: "Accuracy", basis: "Percentage of past cases for which the predicted class matched what later happened.", calculation: "Correct past predictions / all evaluated past cases", note: "This is for the shown historical test period, not confirmed accuracy for a forecast still in progress." },
    error: { title: "Classification error", basis: "Percentage of past cases where the model chose the wrong class.", calculation: "Incorrect past predictions / all evaluated past cases = 1 - accuracy" },
    recall: { title: "Future Sales recall", basis: "Of the past cases that really had a Future Sale, the percentage the model identified.", calculation: "Correct Future Sales predictions / all actual Future Sales cases" },
    share: { title: "Future Sales share", basis: "Percentage of historical account-and-date cases that had at least one valid future sale.", calculation: "Future Sales cases / all evaluated cases", note: "The same company may appear at several dates, so these cases are not a count of different companies." },
    count: { title: "Count", basis: "Number of records or accounts that meet the condition named beside this value.", note: "In historical tests, one account can appear at several dates. A count is not a sales amount." },
  };
  return explanations[key] ?? explanations.count;
}

export function ExplainedValue({ children, explanation, className = "", inline = true }: {
  children: ReactNode;
  explanation: ResultExplanation;
  className?: string;
  inline?: boolean;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pointerType = useRef("");
  const id = useId();
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);
  const [open, setOpen] = useState(false);
  function cancelClose() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = null;
  }
  function scheduleClose() {
    cancelClose();
    closeTimer.current = setTimeout(() => setOpen(false), 250);
  }
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    const closeOnOutsidePress = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!ref.current?.contains(target) && !cardRef.current?.contains(target)) setOpen(false);
    };
    const closeOnPageScroll = (event: Event) => {
      if (event.target instanceof Node && cardRef.current?.contains(event.target)) return;
      const anchor = ref.current?.getBoundingClientRect();
      if (!anchor) return;
      const width = cardRef.current?.getBoundingClientRect().width ?? 420;
      setPosition(current => current ? {
        left: Math.max(12, Math.min(anchor.left + anchor.width / 2 - width / 2, window.innerWidth - width - 12)),
        top: anchor.bottom + 8,
      } : current);
    };
    window.addEventListener("keydown", close);
    window.addEventListener("pointerdown", closeOnOutsidePress);
    window.addEventListener("scroll", closeOnPageScroll, true);
    const closeOnResize = () => setOpen(false);
    window.addEventListener("resize", closeOnResize);
    return () => { window.removeEventListener("keydown", close); window.removeEventListener("pointerdown", closeOnOutsidePress); window.removeEventListener("scroll", closeOnPageScroll, true); window.removeEventListener("resize", closeOnResize); };
  }, [open]);
  useEffect(() => () => cancelClose(), []);
  useLayoutEffect(() => {
    if (!open || !cardRef.current || !ref.current || !position) return;
    const anchor = ref.current.getBoundingClientRect();
    const card = cardRef.current.getBoundingClientRect();
    const height = card.height;
    const left = Math.max(12, Math.min(position.left, window.innerWidth - card.width - 12));
    const below = window.innerHeight - anchor.bottom - 8;
    const above = anchor.top - 8;
    const desiredTop = below >= height || below >= above ? anchor.bottom + 8 : anchor.top - height - 8;
    const top = Math.max(12, Math.min(desiredTop, window.innerHeight - height - 12));
    if (Math.abs(position.top - top) > 1 || Math.abs(position.left - left) > 1) {
      setPosition(current => current ? { left, top } : current);
    }
  }, [open, position]);
  function show() {
    cancelClose();
    const box = ref.current?.getBoundingClientRect();
    if (!box) return;
    const width = Math.min(420, window.innerWidth - 24);
    setPosition({ left: Math.max(12, Math.min(box.left + box.width / 2 - width / 2, window.innerWidth - width - 12)), top: box.bottom + 8 });
    setOpen(true);
  }
  return <>
    <span ref={ref} className={`explained-value ${inline ? "" : "explained-value-block"} ${className}`} tabIndex={0} role="button" aria-expanded={open} aria-describedby={open ? id : undefined}
      onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); if (open) setOpen(false); else show(); } }}
      onPointerEnter={event => { if (event.pointerType !== "touch") show(); }} onPointerLeave={scheduleClose} onFocus={() => { if (pointerType.current !== "touch") show(); }} onBlur={scheduleClose}
      onPointerDown={event => { pointerType.current = event.pointerType; }}
      onClick={event => { if (pointerType.current === "touch") { if (!open) { event.preventDefault(); event.stopPropagation(); show(); } else if (!event.currentTarget.closest("a")) setOpen(false); } pointerType.current = ""; }}>
      {children}
    </span>
    {open && position && createPortal(<div ref={cardRef} id={id} role="tooltip" tabIndex={0} className="result-explanation" style={{ left: position.left, top: position.top }}
      onPointerEnter={cancelClose} onPointerLeave={scheduleClose} onFocus={cancelClose} onBlur={scheduleClose}
      onClick={event => { event.stopPropagation(); }}>
      <span className="result-explanation-eyebrow">About this result</span>
      <strong>{explanation.title}</strong>
      <p><b>Meaning</b>{explanation.basis}</p>
      {explanation.source && <p><b>Information used</b>{explanation.source}</p>}
      {explanation.calculation && <div className="result-explanation-formula"><b>Calculation</b>{explanation.calculation}</div>}
      {explanation.inputs?.length ? <details className="result-explanation-inputs" onToggle={() => setPosition(current => current ? { ...current } : current)}><summary>Saved values for this result</summary><ul>{explanation.inputs.map((input, index) => <li key={index}>{input}</li>)}</ul></details> : null}
      {explanation.note && <small><b>Important</b>{explanation.note}</small>}
      {explanation.interpretation && <p><b>For management</b>{explanation.interpretation}</p>}
    </div>, document.body)}
  </>;
}

export function ResultValue({ metric, row, children, className, inline }: {
  metric: string;
  row?: Partial<AccountDecisionRow> | null;
  children: ReactNode;
  className?: string;
  inline?: boolean;
}) {
  const explanation = resultExplanation(metric, row);
  if (row) {
    explanation.source = `${row.account ?? "This account"}; saved analysis reference ${row.analysis_reference_date ?? "unavailable"}. Several collection rows for one invoice do not multiply a sale.`;
    if (metric === "provenance") explanation.inputs = [row.business_category, row.primary_business_type, row.account_status].filter((value): value is string => Boolean(value));
    if (metric === "frequency") explanation.calculation = `Count distinct valid Sales Invoices in the preceding 24 months: ${row.frequency_count ?? "unavailable"}.`;
    if (metric === "monetary") explanation.calculation = `Sum each valid Sales Invoice once in the preceding 24 months: PHP ${row.monetary_value?.toLocaleString("en-PH", { minimumFractionDigits: 2 }) ?? "unavailable"}.`;
    if (metric === "rfm_frequency") explanation.calculation = `Count distinct valid Sales Invoices across the available history: ${row.full_history_frequency ?? "unavailable"}.`;
    if (metric === "rfm_monetary") explanation.calculation = `Sum valid Sales Invoice amounts across the available history: PHP ${row.full_history_monetary?.toLocaleString("en-PH", { minimumFractionDigits: 2 }) ?? "unavailable"}.`;
    if (metric === "settlement") explanation.calculation = `${row.settlement_invoice_count ?? "Unavailable"} eligible reconciled invoices contribute to this saved mean of ${decimal(row.average_settlement_days)} days. Missing durations are excluded, not zero.`;
  }
  return <ExplainedValue explanation={explanation} className={className} inline={inline}>{children}</ExplainedValue>;
}
