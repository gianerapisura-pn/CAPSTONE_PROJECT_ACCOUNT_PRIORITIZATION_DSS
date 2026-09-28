import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import SettingsPage from "@/app/(protected)/settings/page";

vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({ user: { role: "administrator" } }),
}));

vi.mock("@/lib/use-api", () => ({
  useApi: (path: string) => {
    if (path === "/settings/methodology") return { data: {
      source_schema: ["ACCOUNT NAMES"], analytics_config: { target_horizon_months: 12 },
      rfm: "Descriptive RFM.",
      settlement: "Observed SI-to-final-valid-CR duration using only cutoff-known, reconciled, nonnegative evidence.",
      mcs: "CRITIC and additive MCS.", priority_groups: "Tie-preserving ranked thirds.",
      future_data_rule: "Validated committed data.",
    }, error: "", loading: false, reload: vi.fn() };
    if (path === "/models/current") return { data: {
      status: "active", model_version: "extra_trees_stage8", model_family: "Extra Trees",
      selected_outcome_horizon: 12, validation_metrics: { macro_f1: 0.8015103929068558 },
    }, error: "", loading: false, reload: vi.fn() };
    if (path.startsWith("/account-context")) return { data: {
      items: [], total: 0, publication_note: "A new run is required.",
    }, error: "", loading: false, reload: vi.fn() };
    return { data: [], error: "", loading: false, reload: vi.fn() };
  },
}));

test("settings displays settlement and real registered Macro F1 contracts", () => {
  render(<SettingsPage />);
  expect(screen.getByRole("heading", { name: "Historical Settlement Duration" })).toBeInTheDocument();
  expect(screen.getByText(
    "Observed SI-to-final-valid-CR duration using only cutoff-known, reconciled, nonnegative evidence.",
  )).toBeInTheDocument();
  expect(screen.getByText("Macro F1")).toBeInTheDocument();
  expect(screen.getByText("0.8015")).toBeInTheDocument();
});