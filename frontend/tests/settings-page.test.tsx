import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import SettingsPage from "@/app/(protected)/settings/page";

const authState=vi.hoisted(()=>({role:"administrator"}));
vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({ user: { role: authState.role } }),
}));

vi.mock("@/lib/use-api", () => ({
  useApi: (path: string) => {
    if (path.startsWith("/audit-log")) return { data: { items: [], total: 0, page: 1, total_pages: 1, page_size: 10 }, error: "", loading: false, reload: vi.fn() };
    if (path === "/settings/methodology") return { data: {
      source_schema: ["ACCOUNT NAMES"], analytics_config: { target_horizon_months: 12 },
      rfm: "Descriptive RFM.",
      settlement: "Observed SI-to-final-valid-CR duration using only cutoff-known, reconciled, nonnegative evidence.",
      mcs: "CRITIC and additive MCS.", priority_groups: "Tie-preserving ranked thirds.",
      future_data_rule: "Validated committed data.",
    }, error: "", loading: false, reload: vi.fn() };
    if (path === "/models/current") return { data: {
      status: "active", model_version: "catboost_stage8", model_family: "CatBoost Classifier",
      selected_outcome_horizon: 12, validation_metrics: { macro_f1: 0.7997344352724599 },
    }, error: "", loading: false, reload: vi.fn() };
    if (path.startsWith("/account-context")) return { data: {
      items: [], total: 0, publication_note: "A new run is required.",
    }, error: "", loading: false, reload: vi.fn() };
    return { data: [], error: "", loading: false, reload: vi.fn() };
  },
}));

test("settings retains methodology while removing ordinary technical configuration clutter", () => {
  render(<SettingsPage />);
  expect(screen.getByRole("heading", { name: "Historical Settlement Duration" })).toBeInTheDocument();
  expect(screen.getByText(
    "Observed SI-to-final-valid-CR duration using only cutoff-known, reconciled, nonnegative evidence.",
  )).toBeInTheDocument();
  for(const label of ["Future Macro F1","Future outcomes checked","2025 study outcome check","Artifact SHA-256","Effective analytics configuration","Not flagged","catboost_stage8"]) expect(screen.queryByText(label)).not.toBeInTheDocument();
  expect(screen.getByRole("link",{name:/Required Source File Columns/})).toHaveAttribute("href","/import");
  expect(screen.getByText("No account information currently requires verification.")).toBeInTheDocument();
  expect(screen.queryByRole("heading",{name:/Account alias review/i})).not.toBeInTheDocument();
  expect(screen.getByText("Recheck completed prediction windows")).toBeInTheDocument();
});

test("management retains read-only methodology without administrator maintenance editors",()=>{
 authState.role="management";
 try{render(<SettingsPage/>);expect(screen.getByRole("heading",{name:"Historical Settlement Duration"})).toBeInTheDocument();expect(screen.queryByRole("heading",{name:"Account Information Management"})).not.toBeInTheDocument();expect(screen.queryByText("Recheck completed prediction windows")).not.toBeInTheDocument();expect(screen.queryByRole("link",{name:/Required Source File Columns/})).not.toBeInTheDocument();}finally{authState.role="administrator";}
});
