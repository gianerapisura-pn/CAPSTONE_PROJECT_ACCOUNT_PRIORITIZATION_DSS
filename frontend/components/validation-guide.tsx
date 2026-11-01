import { Info } from "lucide-react";
import styles from "./validation-guide.module.css";

// Technical text documents saved evidence without changing analytical results.
export const validationGuides = {
  context: [
    "Start here: which results are we checking?",
    "The study forecast and its model details come from registered, verified study evidence. Current ranking and sensitivity counts come from the published run shown above.",
    "Future SI means at least one valid Sales Invoice in the stated future window. No Future SI means none predicted in that window, not account closure. Account-scenario rows count repeated checks, not different accounts.",
    "A pending forecast can be checked only after its full outcome window has ended and complete invoice coverage has been verified. The SHA-256 code identifies the approved model file; it is not a performance score.",
  ],
  development: [
    "Why check the historical examples?",
    "These saved development records show what the model learned from at each historical cutoff: a date when only information already available could be used.",
    "Read one row as one cutoff year. An account-cutoff observation is one account assessed at one date; the same account can appear in several years. Future-sales share is Future Sales observations divided by all observations in that row.",
    "Unequal class counts explain why accuracy alone can be misleading: a model could look accurate by mostly choosing the more common class. Macro F1 checks both classes, rather than allowing the larger class to dominate.",
  ],
  horizon: [
    "First, how far ahead should the forecast look?",
    "This historical screening compared 3-, 6-, and 12-month future windows using the same Extra Trees method before selecting the final CatBoost model.",
    "The horizontal axis names the future window. The vertical axis shows historical scores from 0 to 1. Macro F1 balances performance across both classes; Future recall is the share of actual buyers correctly identified.",
    "This explains the recorded choice of a 12-month target. It is not a comparison of current CatBoost forecasts, and Extra Trees is not the deployed model.",
  ],
  benchmark: [
    "Next, which model performed best in the recorded tests?",
    "The bars use saved model-comparison results from chronological tests: each evaluation follows the training period, so later purchases are not available as earlier inputs.",
    "Each bar names a model and shows its mean Macro F1, giving each test year equal weight. Higher is better on this measure. Green identifies the selected CatBoost model; other bars are historical comparisons.",
    "A small score gap is a small recorded difference, not proof of a large business advantage. These tests do not establish the accuracy of an unfinished future window.",
  ],
  metrics: [
    "What do the selected-model comparison scores mean?",
    "This table compares saved historical scores for CatBoost and Extra Trees. It does not run a new model or change the approved CatBoost deployment.",
    "Macro F1 averages the two class F1 scores. Mean error is the fraction classified incorrectly, so lower is better. Balanced accuracy averages the two class recall rates. Future recall measures actual buyers found; Future F1 balances finding buyers with avoiding false buyer alerts.",
    "MCC summarizes agreement between predicted and actual classes: 1 is perfect, 0 indicates no correlation, and -1 is complete disagreement. Other scores here range from 0 to 1. Read several measures together, not accuracy alone.",
  ],
  yearly: [
    "Was performance similar from year to year?",
    "Each row contains one saved chronological CatBoost evaluation year, using earlier information for its predictions and later observed invoices to check them.",
    "Missed Future counts actual buyers predicted not to buy. False Future counts predicted buyers who had no valid invoice in the outcome window. Error and Future recall are percentages; Macro F1 and balanced accuracy are 0-to-1 scores.",
    "Compare rows to see variation hidden by an overall average. These are historical tests, not confirmed results for the pending study forecast.",
  ],
  canonical: [
    "Why show the complete model comparison?",
    "This is the registered full historical comparison, including a Majority Baseline that always selects the more common class.",
    "Rank here orders model test scores, not client accounts. Higher Macro F1 and Future recall are better; lower mean error is better. Compare the selected model with both alternatives and the simple baseline.",
    "The baseline helps show whether a sophisticated model adds value beyond a simple guess. No model in this table changes the current account priority formula.",
  ],
  lookback: [
    "How much past information was considered?",
    "These saved checks compare historical input windows. Lookback means how far into the past the model reads; it is different from the next-12-month period being predicted.",
    "Each row names a past-data window in months. Compare Macro F1, balanced accuracy, Future-class F1, and error across those windows. Higher scores are better, except error, where lower is better.",
    "This documents an input-window design check. It does not mean the client must delete older records or manually change the frozen model after an import.",
  ],
  later: [
    "Did the model also work in later completed periods?",
    "These registered confirmations compare historical predictions with invoices observed after their stated cutoff and through their outcome end date.",
    "Actual Future / No Future are observed account counts; Predicted Future / No Future are model classifications. Error is the wrong-classification share, accuracy is the correct share, and Macro F1 balances both classes.",
    "Different periods can have different eligible accounts. These checks provide later historical evidence, not confirmed accuracy for the separate pending study forecast.",
  ],
  features: [
    "Does the choice of model inputs matter?",
    "The saved three-part historical development checks compare the selected seven predictors with smaller input sets. A predictor is a measured input, such as previous purchase frequency.",
    "Each row names an input set. Features counts its inputs; mean Macro F1 summarizes its historical two-class performance. Difference from all seven subtracts the selected seven-input score: positive is higher, negative is lower.",
    "This checks dependence on the chosen inputs. A better score in one diagnostic is not an instruction to replace the approved model; the deployed CatBoost file remains unchanged.",
  ],
  weights: [
    "Now, what determines the account review order?",
    "These are the four weights saved with the published run. CRITIC derives their shares from variation and overlap in the eligible accounts' Recency, Frequency, Monetary, and Settlement measures.",
    "A weight is a factor's share of the Final Priority Score calculation; the shares total 100%, apart from display rounding. Additive MCS combines the normalized factor values using these shares.",
    "A larger share means more influence in that score formula, not a purchase probability. CatBoost's predicted class is separate and contributes nothing to Final Priority Score.",
  ],
  sensitivity: [
    "Would small weight changes alter the review order?",
    "The published sensitivity checks vary CRITIC weights within each stated percentage range and compare the resulting order with the original published order. These are saved scenarios, not new browser calculations.",
    "The chart's horizontal axis shows the allowed weight-change range. Its lines show average and lowest Spearman rank agreement. A value near 1 means similar order. In the table, Max group movement is the largest share changing High, Medium, or Low group in one tested scenario.",
    "Stable overall order can still include individual group changes. These checks assess robustness to weight choices, not future purchases; original scores, ranks, and groups remain published unchanged.",
  ],
  backtest: [
    "Did historically prioritized accounts contain later sales value?",
    "At each saved cutoff, only information available then forms the eligible ranking. The selected top-decile accounts are checked against valid Sales Invoice value recorded in the following 12 months.",
    "Eligible is the available account population n; Selected is the selected count k. Random k/n is the expected value share for a same-size random selection. Sales value captured is the selected accounts' share of the eligible population's next-year invoice value. Lift divides captured share by k/n.",
    "On the chart, each bar is a cutoff year and the dashed line is lift 1. Above 1 exceeds random expectation; below 1 falls short. For example, 2 means twice the expected value share, not twice as many buyers or proof that using the DSS increased sales.",
  ],
  removal: [
    "Does the ranking depend on keeping all four factors?",
    "Each saved diagnostic removes one criterion, recalculates the comparison ranking with the remaining criteria, and compares it with the full four-factor study ranking.",
    "Removed criterion names the omitted factor. Rank Spearman measures order agreement; Priority Group changes counts accounts assigned a different group. Remaining weight range shows the smallest and largest shares among the retained factors.",
    "Changes show why omitting a factor matters. This is a diagnostic comparison only: the official system still uses all four criteria and does not delete any account or result.",
  ],
  historicalRemoval: [
    "What happened when a factor was omitted in past years?",
    "These saved study checks repeat criterion removal at historical cutoffs and examine the selected accounts' following-12-month sales value.",
    "Each row combines a cutoff and removed criterion. Eligible and Selected count accounts in that test; Capture rate is the selected share of subsequent invoice value. Lift compares that share with the same-size random expectation.",
    "Compare the same cutoff across omitted factors. Differences identify historical dependence on criteria, not approved replacement formulas. Ten rows appear per page; changing pages does not rerun the analytics.",
  ],
  boundary: [
    "Which accounts were close to changing Priority Group?",
    "This saved study list contains account-and-weight-range observations with at least one group change in the tested sensitivity scenarios.",
    "Baseline group is the original group. Group changes counts scenarios where that account changed group; Scenario change rate divides that count by tested scenarios in that range. Maximum rank movement is its largest position change. An account may appear at several ranges.",
    "A larger change rate suggests its group assignment is more sensitive to weight choices. These are hypothetical changes, not new official group assignments or additional unique accounts.",
  ],
  influence: [
    "Could one account strongly affect the shared weights?",
    "Each saved check temporarily leaves out one account, recalculates CRITIC weights, and compares the remaining accounts' results with their baseline. No account is deleted from the system.",
    "Removed account names the test omission. Maximum weight change is the largest absolute difference across the four weights; 0.01 means one percentage point. Rank Spearman compares order among the remaining accounts; Group movement is their share changing group. Recomputed weights show the comparison's new shares.",
    "Small weight changes and agreement near 1 indicate limited influence in that test. This is a diagnostic of population dependence, not an account-quality score or permission to exclude an account.",
  ],
  alternatives: [
    "Would another weighting or scoring method give similar results?",
    "These locked study comparisons check CRITIC against alternative weighting and additive MCS against TOPSIS, a different way of combining criteria.",
    "Each row names a method comparison. Rank Spearman measures account-order agreement. Group agreement is the share retaining the same group; Group changes counts accounts assigned a different group.",
    "Agreement supports robustness; disagreement identifies method sensitivity. Entropy, Equal Weighting, and TOPSIS are supplementary evidence only, not methods silently applied to the live ranking.",
  ],
  alternativeBacktests: [
    "How did the comparison methods behave in completed historical tests?",
    "These registered study summaries combine historical cutoff tests for each named method. They are separate from the latest operational backtest results above.",
    "Periods counts tests; Lift above random counts periods with lift greater than 1. Mean lift averages period lifts; Minimum lift is the weakest period. Pooled future sales capture combines captured invoice value across periods and divides by their combined eligible future invoice value.",
    "Check both average and weakest-period results. A historical advantage on sales-value capture does not prove that a method causes sales or should replace the approved four-factor review method.",
  ],
  incidence: [
    "How often did accounts in each historical group buy again?",
    "The saved completed tests pool account-year observations by their historical Priority Group. One company can contribute one observation in several different years.",
    "Buyer account-years have at least one valid invoice in the next 12 months. Buyer incidence divides these by all eligible account-years in that group. Share of succeeding SI value is that group's share of total subsequent invoice value, not its buyer percentage.",
    "Read buying frequency and invoice-value share as different measures. These historical rates are neither today's individual purchase probabilities nor proof that the priority assignment caused buying.",
  ],
  annual: [
    "How much did the review order change between years?",
    "Each saved row compares consecutive historical year-end rankings for accounts present in both years. New or absent accounts are not counted as matched accounts.",
    "Rank Spearman near 1 means a similar order. Mean normalized movement averages each matched account's absolute change in rank percentile, adjusting for different population sizes; pp means percentage points. Changed group counts matched accounts moving between High, Medium, and Low.",
    "Movement can reflect changing purchase and payment history, not a software error. A stable review order does not guarantee future purchases or mean every account kept its group.",
  ],
  recency: [
    "Why compare the priority method with a simple recent-purchase rule?",
    "The saved study comparison uses matching historical cutoffs to compare the official four-factor method with selecting accounts by Recency alone: how recently they purchased.",
    "Mean historical lift averages the selected accounts' next-year invoice-value share relative to a same-size random selection. Only matched cutoff evidence supports the displayed comparison. Higher lift means greater historical value capture on this specific measure.",
    "The official method balances purchase recency, frequency, value, and settlement for account review. It is not designed only to maximize next-year sales-value capture. A simple rule performing better on this diagnostic must not be hidden or treated as a causal result.",
  ],
  relationship: [
    "Is a higher priority score associated with later buying?",
    "These saved historical diagnostics compare Final Priority Scores with actual purchases and invoice values in each following year; they do not use CatBoost predictions.",
    "Buyer-discrimination AUC measures how often a buyer has a higher FPS than a nonbuyer: 0.5 is no discrimination and 1 is perfect. FPS versus next-year SI Spearman measures score/value association: near 1 is positive, near 0 is weak, and negative means an opposite pattern. Recency-only lift is the simple rule's value capture versus random.",
    "A relationship can be weak even when the review method is stable. FPS is a multicriteria review score, not a calibrated purchase probability or a promised sales amount.",
  ],
  bootstrap: [
    "How uncertain are differences between historical groups?",
    "These saved checks repeatedly resample whole accounts, keeping each account's historical observations together, to examine variation in buyer-incidence differences.",
    "The contrast names the first group minus the second. Observed difference is their buyer-rate gap in percentage points. The 2.5% and 97.5% bounds enclose the middle 95% of resampled gaps; Resamples counts repeated draws. A negative gap means the first group had the lower rate.",
    "If the interval includes zero, the direction of the difference is uncertain in these resamples. Excluding zero still does not establish a causal effect, an individual purchase probability, or guaranteed future performance.",
  ],
} as const;

export const validationContexts: Record<keyof typeof validationGuides, string> = {
  context: "Study forecasts and current ranking results refer to their stated dates; predictions are not confirmed sales.",
  development: "Historical training examples show how often accounts bought again after each cutoff.",
  horizon: "Compares historical forecast windows before the final model was selected.",
  benchmark: "Compares models on completed historical tests; higher Macro F1 means better performance across both classes.",
  metrics: "Compares CatBoost with Extra Trees on several historical performance measures.",
  yearly: "Shows whether CatBoost's historical performance varied across evaluation years.",
  canonical: "Full historical model comparison; these positions rank models, not client accounts.",
  lookback: "Compares how much past purchase history was used as model input, not how far ahead it predicts.",
  later: "Checks earlier predictions against purchases observed in later, completed periods.",
  features: "Checks how historical model performance changes when different sets of inputs are used.",
  weights: "Published CRITIC weights show each factor's share in the Final Priority Score; predictions are excluded.",
  sensitivity: "Tests whether account rankings and Priority Groups change when criterion weights are adjusted.",
  backtest: "Compares the top-ranked accounts' next-year invoice-value share with a same-size random selection.",
  removal: "Checks how omitting one factor changes the four-factor study ranking.",
  historicalRemoval: "Checks next-year sales-value capture when one factor is omitted at historical cutoffs.",
  boundary: "Lists account-and-range tests where weight changes moved an account to another Priority Group.",
  influence: "Checks how much each account affects the shared CRITIC weights; no account is deleted.",
  alternatives: "Compares study rankings under alternative weighting and scoring methods; the official method is unchanged.",
  alternativeBacktests: "Compares alternative methods' sales-value capture across completed historical periods.",
  incidence: "Shows how often historical group members bought again and their share of next-year invoice value.",
  annual: "Compares consecutive historical rankings for accounts present in both years.",
  recency: "Compares the four-factor method with selecting accounts by their most recent purchase alone.",
  relationship: "Checks whether higher priority scores were associated with later purchases and invoice value.",
  bootstrap: "Shows uncertainty in historical buyer-rate differences; an interval containing zero has an uncertain direction.",
};

export function ValidationGuide({ topic, contextVisible = true }: { topic: keyof typeof validationGuides; contextVisible?: boolean }) {
  const [title, purpose, reading, meaning] = validationGuides[topic];
  return <div className={styles.guide} data-validation-guide={topic} data-context-visible={contextVisible}>
    {contextVisible && <p className={styles.context}>{validationContexts[topic]}</p>}
    <details className={styles.details}>
      <summary title={`Technical details: ${title}`}><Info size={14} aria-hidden="true" />Details<span className={styles.srOnly}>: {title}</span></summary>
      <div className={styles.body}><p>{purpose}</p><p>{reading}</p><p>{meaning}</p></div>
    </details>
  </div>;
}

type Evidence = Readonly<Record<string, unknown>>;
type Topic = keyof typeof validationGuides;

// Display summaries use only saved rows, never thresholds that grade or alter analytics.
export function validationFinding(topic: Topic, rows: readonly Evidence[]): string | null {
  if (!rows.length) return null;
  const numbers = (key: string) => rows.flatMap(row => typeof row[key] === "number" && Number.isFinite(row[key]) ? [row[key] as number] : []);
  const range = (key: string, percentage = false) => {
    const values = numbers(key);
    if (!values.length) return "unavailable";
    const format = (value: number) => percentage ? `${(value * 100).toFixed(2)}%` : value.toFixed(4);
    return `${format(Math.min(...values))} to ${format(Math.max(...values))}`;
  };
  switch (topic) {
    case "sensitivity": {
      const movements = numbers("max_group_movement_rate");
      return `Mean rank agreement: ${range("mean_spearman")} (1 = identical order). Largest group movement: ${movements.length ? `${(Math.max(...movements) * 100).toFixed(2)}%` : "unavailable"} in a tested scenario.`;
    }
    case "backtest": {
      const lift = numbers("lift_over_expected_random");
      return lift.length ? `${lift.filter(value => value > 1).length} of ${lift.length} available historical tests exceeded random expectation; lift ranged from ${range("lift_over_expected_random")} times. This measures sales-value capture, not a causal sales increase.` : "Historical lift is unavailable.";
    }
    case "benchmark": case "metrics": case "canonical": {
      const a = rows.find(row => row.family === "CatBoost")?.mean_macro_f1;
      const b = rows.find(row => row.family === "Extra Trees")?.mean_macro_f1;
      return typeof a === "number" && Number.isFinite(a) && typeof b === "number" && Number.isFinite(b) ? `Historical mean Macro F1: CatBoost ${a.toFixed(4)}; Extra Trees ${b.toFixed(4)}. This does not establish pending-forecast accuracy.` : `${rows.length} model results recorded; the CatBoost/Extra Trees score comparison is incomplete.`;
    }
    case "yearly": case "later": return `Historical Macro F1: ${range("macro_f1")} across ${rows.length} recorded periods; not pending-forecast accuracy.`;
    case "influence": {
      const changes = numbers("maximum_absolute_weight_change");
      return `${rows.length} account-omission checks; largest weight change: ${changes.length ? `${(Math.max(...changes) * 100).toFixed(2)} percentage points` : "unavailable"}. Published weights are unchanged.`;
    }
    case "boundary": return `${rows.length} account-and-range observations had group changes; accounts may repeat. Published groups are unchanged.`;
    case "development": {
      const counts = numbers("observations");
      return counts.length === rows.length ? `${counts.reduce((sum, value) => sum + value, 0)} account-cutoff observations across ${rows.length} years, not distinct-company counts.` : "Development observation counts are incomplete.";
    }
    case "horizon": {
      const selected = rows.find(row => row.stage4_decision === "SELECTED");
      return selected ? `Recorded target choice: ${selected.horizon_months} months, selected before final model comparison.` : "The recorded target-window choice is unavailable.";
    }
    case "lookback": return `${rows.length} past-data windows compared; the future prediction horizon is unchanged.`;
    case "features": {
      const differences = numbers("delta_macro_f1_vs_all_7");
      return differences.length ? `${differences.filter(value => value > 0).length} of ${differences.length} recorded input sets scored above the seven-input reference; the frozen model is unchanged.` : "Input-set score differences are unavailable.";
    }
    case "weights": {
      const valid = rows.filter(row => typeof row.weight === "number" && Number.isFinite(row.weight));
      if (!valid.length) return "Published criterion weights are unavailable.";
      const maximum = Math.max(...valid.map(row => Number(row.weight)));
      const names = valid.filter(row => row.weight === maximum).map(row => String(row.criterion)).join(", ");
      return `Largest published weight: ${names} (${(maximum * 100).toFixed(2)}%); the four-factor score excludes predicted sales.`;
    }
    case "annual": return `Annual rank agreement: ${range("spearman_rho")} (1 = identical order); this checks review-order stability, not future purchases.`;
    case "incidence": return `Historical buyer incidence: ${range("purchase_incidence", true)} across saved groups; not individual purchase probabilities.`;
    case "relationship": return `FPS / next-year invoice-value association: ${range("spearman_fps_vs_next_year_si")}; association does not promise sales.`;
    case "bootstrap": {
      const bounds = rows.filter(row => typeof row.ci_2_5 === "number" && Number.isFinite(row.ci_2_5) && typeof row.ci_97_5 === "number" && Number.isFinite(row.ci_97_5));
      return bounds.length ? `${bounds.filter(row => Number(row.ci_2_5) <= 0 && Number(row.ci_97_5) >= 0).length} of ${bounds.length} available intervals include zero; those differences have an uncertain direction.` : "Saved uncertainty bounds are unavailable.";
    }
    case "removal": {
      const counts = numbers("group_changes");
      return counts.length ? `${Math.min(...counts)} to ${Math.max(...counts)} accounts changed group across omitted-factor tests; the official method retains all four factors.` : "Criterion-removal group-change counts are unavailable.";
    }
    case "historicalRemoval": return `${rows.length} historical cutoff-and-factor checks; supplementary comparisons, not replacement rankings.`;
    case "alternatives": return `Priority Group agreement: ${range("group_agreement", true)} across comparisons; official CRITIC/MCS results are unchanged.`;
    case "alternativeBacktests": return `Mean historical lift: ${range("mean_lift")} times across methods; these are supplementary comparisons.`;
    default: return null;
  }
}

export function ValidationFinding({ topic, rows }: { topic: Topic; rows: readonly Evidence[] }) {
  const finding = validationFinding(topic, rows);
  return finding ? <p className={styles.finding} data-validation-finding={topic}>{finding}</p> : null;
}
