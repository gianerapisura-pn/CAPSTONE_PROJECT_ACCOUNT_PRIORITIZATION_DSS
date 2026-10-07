import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import AccountDetailsPage from "@/app/(protected)/accounts/[accountKey]/page";

vi.mock("next/navigation", () => ({ useParams: () => ({ accountKey: "a064" }) }));
vi.mock("@/lib/use-api", () => ({ useApi: () => ({
  data: {
    account_key: "a064", account: "ROSTRAM PROTECTIVE SYSTEM METIER COMPANY",
    decision: {
      account_key: "a064", account: "ROSTRAM PROTECTIVE SYSTEM METIER COMPANY",
      is_ranked: false, ranking_unavailable_reason: "Client-confirmed closed; excluded from the current actionable ranking.",
      mcs_eligibility_reason: "Client-confirmed closed; excluded from the current actionable ranking.",
      latest_valid_si_date: "2025-01-01", average_settlement_days: 12,
      settlement_invoice_count: 2, predicted_future_transaction_class: "No Future Transaction",
    },
    priority: null,
    rfm: { recency_days: 600, frequency: 3, monetary: 100000, r_score: 2, f_score: 3, m_score: 4, rfm_mean_score: 3 },
    settlement: { average_settlement_days: 12 },
    context: {
      entity_type: "Company", business_category: "Corporate", primary_business_type: "Protective systems",
      account_status: "Client-Confirmed Closed", verification_type: "Client confirmation",
      verification_date: "2026-09-20", last_verified: "2026-09-21",
      verification_basis: "Direct PESLC client confirmation", current_actionable: false,
      status_confirming_role: "PESLC client representative",
      status_claim_scope: "PESLC account actionability",
      identity_source_type: "Official company/organization",
      identity_source_reference: "Official company page",
      identity_source_checked_on: "2026-10-04",
    },
    predictive: { predicted_future_transaction_class: "No Future Transaction", model_version: "extra_trees_stage8" },
    critic_weights: {}, sensitivity: null,
    transactions: [{ invoice_group_id: "i1", si_no: "SI-1", si_date: "2025-01-01", si_amount: 100000, final_cr_date: "2025-01-13", payment_status: "Fully Paid", reconciled: true, import_batch_id: "batch-12345678" }],
  }, error: "", loading: false, reload: vi.fn(),
}) }));

test("closed B2B detail keeps descriptive and predictive evidence but no current rank", () => {
  render(<AccountDetailsPage />);
  expect(screen.getAllByText("Client-Confirmed Closed").length).toBeGreaterThan(0);
  expect(screen.getByText("Client-confirmed closed; excluded from the current actionable ranking.")).toBeInTheDocument();
  expect(screen.getByText("Direct PESLC client confirmation")).toBeInTheDocument();
  expect(screen.getByText("Official company/organization / Official company page")).toBeInTheDocument();
  expect(screen.getByText("Not actionable")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /RFM profile/ })).toBeInTheDocument();
  expect(screen.getAllByText("No Future Transaction").length).toBeGreaterThan(0);
  expect(screen.getByText("SI-1")).toBeInTheDocument();
  expect(screen.getAllByText("Not ranked").length).toBeGreaterThan(0);
});
