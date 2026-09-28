import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AccountContextPanel } from "@/components/account-context-panel";

const useApi = vi.fn((path: string) => ({
  data: { items: [{
    account_key: "a063", account: "ROD DE GUIA", entity_type: "Individual/Personal",
    business_category: "Personal", primary_business_type: "Personal", account_status: null,
    last_verified: null, verification_type: null, verification_date: null,
    verification_basis: null, b2b_priority_eligible: false, current_actionable: false,
    verification_status: "verified",
  }], total: 1, publication_note: "A new run is required." },
  error: "", loading: false, reload: vi.fn(), path,
}));
vi.mock("@/lib/use-api", () => ({ useApi: (path: string) => useApi(path) }));
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));

test("context admin uses canonical taxonomy, controlled status, provenance, and pending/all views", async () => {
  const user = userEvent.setup();
  render(<AccountContextPanel />);
  expect(screen.getByRole("option", { name: "Company" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Condominium Association" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Client-Confirmed Active" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Client-Confirmed Closed" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Client confirmation" })).toBeInTheDocument();
  expect(screen.getByLabelText("ROD DE GUIA B2B eligible")).toBeDisabled();
  expect(screen.getByLabelText("ROD DE GUIA verification basis")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "All" }));
  expect(useApi).toHaveBeenLastCalledWith("/account-context?status=all");
});