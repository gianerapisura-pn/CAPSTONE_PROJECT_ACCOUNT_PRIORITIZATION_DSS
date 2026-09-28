import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import SettingsPage from "@/app/(protected)/settings/page";

vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({ user: { role: "management" } }),
}));

vi.mock("@/lib/use-api", () => ({
  useApi: () => ({
    data: {
      source_schema: ["ACCOUNT NAMES"],
      analytics_config: { target_horizon_months: 12 },
      rfm: "Descriptive RFM.",
      settlement: "Observed SI-to-final-valid-CR duration using only cutoff-known, reconciled, nonnegative evidence.",
      mcs: "CRITIC and additive MCS.",
      priority_groups: "Tie-preserving ranked thirds.",
      future_data_rule: "Validated committed data.",
    },
    error: "",
    loading: false,
    reload: vi.fn(),
  }),
}));

test("settings displays the historical settlement methodology contract", () => {
  render(<SettingsPage />);
  expect(screen.getByRole("heading", { name: "Historical Settlement Duration" })).toBeInTheDocument();
  expect(screen.getByText(
    "Observed SI-to-final-valid-CR duration using only cutoff-known, reconciled, nonnegative evidence.",
  )).toBeInTheDocument();
});