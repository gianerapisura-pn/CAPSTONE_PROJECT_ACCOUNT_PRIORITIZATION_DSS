import { render, screen } from "@testing-library/react";
import { beforeEach, vi } from "vitest";
import AccountDetailsPage from "@/app/(protected)/accounts/[accountKey]/page";

const state=vi.hoisted(()=>({query:"",key:"a064",loading:false,error:"",requests:[] as string[],dataKey:null as string|null}));
const scroll=vi.fn();
beforeEach(()=>{
 state.query="";state.key="a064";state.loading=false;state.error="";state.requests=[];state.dataKey=null;scroll.mockClear();
 Object.defineProperty(HTMLElement.prototype,"scrollIntoView",{value:scroll,configurable:true});
});
vi.mock("next/navigation", () => ({ useParams: () => ({ accountKey: state.key }), useSearchParams: () => new URLSearchParams(state.query) }));
vi.mock("@/lib/use-api", () => ({ useApi: (path:string) => { state.requests.push(path);return ({
  data: state.loading ? null : {
    account_key: state.dataKey ?? state.key, account: "ROSTRAM PROTECTIVE SYSTEM METIER COMPANY",
    navigation: {
      previous: { account_key: "a063", account: "Previous published account" },
      next: { account_key: "a065", account: "Next published account" },
    },
    decision: {
      account_key: "a064", account: "ROSTRAM PROTECTIVE SYSTEM METIER COMPANY",
      is_ranked: false, ranking_unavailable_reason: "Client-confirmed closed; excluded from the current actionable ranking.",
      mcs_eligibility_reason: "Client-confirmed closed; excluded from the current actionable ranking.",
      latest_valid_si_date: "2025-01-01", average_settlement_days: 12,
      settlement_invoice_count: 2, predicted_future_transaction_class: null,
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
    predictive: { predicted_future_transaction_class: null, model_version: null },
    critic_weights: {}, sensitivity: null,
    transactions: [{ invoice_group_id: "i1", si_no: "SI-1", si_date: "2025-01-01", si_amount: 100000, final_cr_date: "2025-01-13", payment_status: "Fully Paid", reconciled: true, import_batch_id: "batch-12345678" }],
  }, error: state.error, loading: state.loading, reload: vi.fn(),
});} }));

test("closed-since-2021 B2B detail keeps descriptive evidence but no 2025 prediction or current rank", () => {
  render(<AccountDetailsPage />);
  expect(screen.getByRole("link", { name: "Back to Filtered Accounts" })).toHaveAttribute("href", "/accounts");
  expect(screen.getByRole("link", { name: "Previous Account" })).toHaveAttribute("href", "/accounts/a063");
  expect(screen.getByRole("link", { name: "Next Account" })).toHaveAttribute("href", "/accounts/a065");
  expect(screen.getAllByText("Client-Confirmed Closed").length).toBeGreaterThan(0);
  expect(screen.getByText("Client-confirmed closed; excluded from the current actionable ranking.")).toBeInTheDocument();
  expect(screen.getByText("Direct PESLC client confirmation")).toBeInTheDocument();
  expect(screen.getByText("Official company/organization / Official company page")).toBeInTheDocument();
  expect(screen.getByText("Not actionable")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /RFM profile/ })).toBeInTheDocument();
  expect(screen.queryByText("With No Future Sales")).not.toBeInTheDocument();
  expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
  expect(screen.getByText("SI-1")).toBeInTheDocument();
  expect(screen.getAllByText("Not ranked").length).toBeGreaterThan(0);
});


for(const focus of ["rfm","settlement","priority"]){
 test(`${focus} waits for loaded account evidence, focuses once and preserves next-account context`,()=>{
  state.query=new URLSearchParams({focus,eligibility:"all",returnTo:`/analytics/${focus === "settlement" ? "settlement" : "rfm"}?page=2`}).toString();
  state.loading=true;
  const view=render(<AccountDetailsPage/>);
  expect(scroll).not.toHaveBeenCalled();
  state.loading=false;view.rerender(<AccountDetailsPage/>);
  expect(document.activeElement?.id).toBe(`account-${focus}`);
  expect(screen.getByRole("region",{name:focus === "rfm" ? "Historical RFM profile" : focus === "settlement" ? "Historical Settlement Duration" : "Current prioritization"})).toHaveFocus();
  expect(scroll).toHaveBeenCalledTimes(1);
  expect(scroll).toHaveBeenCalledWith({behavior:"auto",block:"start"});
  view.rerender(<AccountDetailsPage/>);
  expect(scroll).toHaveBeenCalledTimes(1);
  const next=new URL(screen.getByRole("link",{name:"Next Account"}).getAttribute("href")!,"https://example.test");
  expect(next.searchParams.get("focus")).toBe(focus);
  expect(next.searchParams.get("returnTo")).toContain("page=2");
  state.key="a065";view.rerender(<AccountDetailsPage/>);
  expect(scroll).toHaveBeenCalledTimes(2);
  expect(state.requests.every(path=>!path.includes("focus")&&!path.includes("returnTo"))).toBe(true);
 });
}

for(const source of ["rfm","settlement"]){
 test(`${source} has one clear originating-page back action`,()=>{
  state.query=new URLSearchParams({focus:source,eligibility:"all",returnTo:`/analytics/${source}?page=3`}).toString();
  render(<AccountDetailsPage/>);
  expect(screen.getByRole("link",{name:source === "rfm" ? "Back to RFM" : "Back to Settlement"})).toHaveAttribute("href",`/analytics/${source}?page=3`);
  expect(screen.queryByRole("link",{name:"View matching accounts"})).not.toBeInTheDocument();
  expect(screen.queryByRole("link",{name:"Back to Filtered Accounts"})).not.toBeInTheDocument();
 });
}

test("filtered-list return keeps filters and page while excluding focus metadata",()=>{
 state.query=new URLSearchParams({focus:"priority",viaList:"1",eligibility:"ranked",priority_group:"High",page:"2",returnTo:"/analytics/rfm?page=3"}).toString();
 render(<AccountDetailsPage/>);
 const back=new URL(screen.getByRole("link",{name:"Back to Filtered Accounts"}).getAttribute("href")!,"https://example.test");
 expect(back.searchParams.get("priority_group")).toBe("High");expect(back.searchParams.get("page")).toBe("2");
 expect(back.searchParams.has("focus")).toBe(false);expect(back.searchParams.has("viaList")).toBe(false);
 expect(document.activeElement?.id).toBe("account-priority");
});

test("direct, invalid and duplicate focus links retain the default without an automatic jump",()=>{
 const view=render(<AccountDetailsPage/>);
 expect(scroll).not.toHaveBeenCalled();
 for(const query of ["focus=unknown","focus=rfm&focus=settlement","focus=javascript:alert(1)"]){state.query=query;view.rerender(<AccountDetailsPage/>);expect(scroll).not.toHaveBeenCalled();expect(screen.getByRole("heading",{name:"Historical RFM profile"})).toBeInTheDocument();}
});

test("unsupported filters and API failures never trigger section focus or unsafe returns",()=>{
 state.query="focus=rfm&unauthorized_filter=x&returnTo=https://evil.test";
 const view=render(<AccountDetailsPage/>);expect(scroll).not.toHaveBeenCalled();
 expect(screen.queryByRole("link",{name:"Back to RFM"})).not.toBeInTheDocument();
 state.query="focus=settlement";state.error="Request denied";view.rerender(<AccountDetailsPage/>);
 expect(scroll).not.toHaveBeenCalled();expect(screen.getByText("Request denied")).toBeInTheDocument();
});


test("stale evidence from the prior account cannot consume the new account focus request",()=>{
 state.query="focus=rfm";
 const view=render(<AccountDetailsPage/>);expect(scroll).toHaveBeenCalledTimes(1);
 state.key="a065";state.dataKey="a064";view.rerender(<AccountDetailsPage/>);
 expect(scroll).toHaveBeenCalledTimes(1);
 state.dataKey=null;view.rerender(<AccountDetailsPage/>);expect(scroll).toHaveBeenCalledTimes(2);
});
