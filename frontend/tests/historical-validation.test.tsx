import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AnnualGroupOutcomes, AnnualRankingHistory, rankMovement, type HistoricalRanking } from "@/components/historical-validation";
import { useApi } from "@/lib/use-api";

vi.mock("@/lib/use-api", () => ({ useApi: vi.fn() }));
const previous = { year: 2024, rank: 20, fps: .5, population: 78, priority_group: "Medium", positions: 8, group_changed: true };
const row: HistoricalRanking = { account_key: "QA001", account_name: "Test business", cutoff: "2025-12-31", year: 2025, rank: 12, fps: .61234, priority_group: "High", population: 83, designation: "Official study baseline", evaluation_end: "2026-12-31", outcome_status: "pending", subsequent_si_value: null, source_member: "study.csv", source_member_sha256: "abc", previous };
const reload = vi.fn();
function response(items = [row]) { return { study_reference_date: "2025-12-31", years: [2018,2024,2025], year: 2025, population: 83, page: 1, page_size: 10, total: 83, items }; }
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useApi).mockReturnValue({ data: response(), loading: false, error: "", reload });
});

test("saved rank and pending outcome remain clear in keyboard-accessible inline details", async () => {
  render(<AnnualRankingHistory />);
  expect(screen.getByLabelText("Ranking year")).toHaveValue("2025");
  expect(screen.getByText("#12")).toBeVisible();
  expect(screen.getByText("0.6123")).toBeVisible();
  const account = screen.getByRole("button", { name: "Test business" });
  account.focus();
  await userEvent.keyboard("{Enter}");
  expect(account).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("region", {name:"Test business historical explanation"}).closest("table")).toBeNull();
  expect(screen.getByText(/rank #20 among 78 accounts/)).toBeVisible();
  expect(screen.getByText(/Pending complete and verified actual SI coverage/)).toBeVisible();
  expect(screen.getByText(/do not identify which business factor/)).toBeVisible();
  await userEvent.click(account);
  expect(account).toHaveAttribute("aria-expanded", "false");
});

test("year, search and page changes use server filters without renumbering", async () => {
  render(<AnnualRankingHistory />);
  await userEvent.click(screen.getByRole("button",{name:"Next"}));
  expect(vi.mocked(useApi).mock.lastCall?.[0]).toContain("page=2");
  await userEvent.type(screen.getByLabelText("Find a historical account"),"Test");
  expect(vi.mocked(useApi).mock.lastCall?.[0]).toContain("search=Test");
  expect(vi.mocked(useApi).mock.lastCall?.[0]).toContain("page=1");
  await userEvent.selectOptions(screen.getByLabelText("Ranking year"),"2018");
  expect(vi.mocked(useApi).mock.lastCall?.[0]).toContain("year=2018");
  expect(screen.getByText("#12")).toBeVisible();
});

test("missing comparison and observed SI value are distinct from forecasts", async () => {
  vi.mocked(useApi).mockReturnValue({data:response([{...row,previous:null,year:2018,cutoff:"2018-12-31",evaluation_end:"2019-12-31",outcome_status:"observed",subsequent_si_value:1250}]),loading:false,error:"",reload});
  render(<AnnualRankingHistory />);
  expect(screen.getByText("No comparable previous-year rank")).toBeVisible();
  await userEvent.click(screen.getByRole("button",{name:"Test business"}));
  expect(screen.getByText(/Subsequently observed SI value through 2019/)).toBeVisible();
  expect(screen.getByText(/not used to calculate that FPS/)).toBeVisible();
  expect(screen.queryByText(/Pending complete/)).not.toBeInTheDocument();
  expect(rankMovement({...previous,positions:-8})).toBe("↓ 8 positions");
  expect(rankMovement({...previous,positions:0})).toBe("Same rank");
});

test("loading, unavailable and empty states never show stale ranking rows", async () => {
  vi.mocked(useApi).mockReturnValue({data:response(),loading:true,error:"",reload});
  const {rerender}=render(<AnnualRankingHistory />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading");
  expect(screen.queryByRole("button",{name:"Test business"})).not.toBeInTheDocument();
  vi.mocked(useApi).mockReturnValue({data:response(),loading:false,error:"Verified evidence unavailable",reload});
  rerender(<AnnualRankingHistory />);
  expect(screen.getByRole("alert")).toHaveTextContent("Verified evidence unavailable");
  await userEvent.click(screen.getByRole("button",{name:"Retry historical rankings"}));
  expect(reload).toHaveBeenCalledOnce();
  vi.mocked(useApi).mockReturnValue({data:{...response([]),total:0},loading:false,error:"",reload});
  rerender(<AnnualRankingHistory />);
  expect(screen.getByRole("status")).toHaveTextContent("No historical accounts match");
});

test("annual groups are always visible, retain exceptions and explain their denominators", async () => {
  const rows=[{year:2021,priority_group:"Low",accounts:22,buyers_group:1,purchase_incidence:1/22,next_year_sales:10207887.38,universe_sales:15780371.23,sales_capture:.6468724487668469}, {year:2022,priority_group:"High",accounts:23,buyers_group:3,purchase_incidence:3/23,next_year_sales:3331137.38,universe_sales:12234074.18,sales_capture:.2722835689067238}];
  const before=JSON.stringify(rows);
  render(<AnnualGroupOutcomes rows={rows}/>);
  expect(screen.getByRole("heading", {name:/Annual Priority Group Outcomes/})).toBeVisible();
  expect(screen.getByRole("table")).toBeVisible();
  expect(screen.queryByRole("button", {name:/View annual breakdown/})).not.toBeInTheDocument();
  expect(screen.getByText("27.23%")).toBeVisible();
  await userEvent.selectOptions(screen.getByLabelText("Group-outcome cutoff year"),"2021");
  expect(screen.getByText("64.69%")).toBeVisible();
  const table=screen.getByRole("table");
  expect(within(table).getByText("Low")).toBeVisible();
  await userEvent.hover(screen.getByText("4.55%"));
  expect(screen.getByRole("tooltip").querySelector(".result-interpretation")).toHaveTextContent("1 of 22 Low Priority accounts");
  expect(await screen.findByText(/1 subsequent buyers ÷ 22 accounts/)).not.toBeVisible();
  await userEvent.click(screen.getByText("Definition and calculation"));
  expect(await screen.findByText(/1 subsequent buyers ÷ 22 accounts/)).toBeVisible();
  expect(screen.getByRole("tooltip")).toHaveTextContent("1 of 22 Low Priority accounts");
  await userEvent.keyboard("{Escape}");
  await userEvent.hover(screen.getByText("64.69%"));
  expect(screen.getByRole("tooltip").querySelector(".result-interpretation")).toHaveTextContent("64.69%");
  await userEvent.click(screen.getByText("Definition and calculation"));
  expect(await screen.findByText(/not buyer count or collected cash/)).toBeVisible();
  expect(JSON.stringify(rows)).toBe(before);
  expect(screen.getByRole("table")).toBeVisible();
});
