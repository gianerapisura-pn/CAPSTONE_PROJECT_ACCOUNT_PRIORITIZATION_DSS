import { fireEvent, render, screen, within } from "@testing-library/react";
import { vi } from "vitest";
import SensitivityPage from "@/app/(protected)/analytics/sensitivity/page";

const { state } = vi.hoisted(() => ({ state: { missingWeight: false } }));
vi.mock("@/lib/use-api", () => ({ useApi: () => ({
  data: {
    analysis_run_id: "saved-run",
    critic_weights: { recency: 0.3611623465698157, frequency: 0.23172179091738496,
      monetary: 0.12298946506730116, ...(state.missingWeight ? {} : { settlement: 0.2841263974454982 }) },
    summaries: [{ weight_range: 0.1, iterations: 100, mean_spearman: 0.9995,
      min_spearman: 0.9987, max_spearman: 1, group_movement_rate: 0.0005, max_group_movement_rate: 0.0241 },
    { weight_range: 0.2, iterations: 100, mean_spearman: 0.9989,
      min_spearman: 0.9953, max_spearman: 1, group_movement_rate: 0.007, max_group_movement_rate: 0.0482 }],
  }, error: "", loading: false, reload: vi.fn(),
}) }));

afterEach(() => { state.missingWeight = false; });

test("shows saved weights prominently and keeps computations optional without changing table values", () => {
  render(<SensitivityPage />);
  const weights = screen.getByRole("region", { name: "Published CRITIC weights" });
  for (const value of ["36.12%", "23.17%", "12.30%", "28.41%"]) {
    expect(within(weights).getByText(value).closest("strong")).toBeInTheDocument();
  }
  expect(screen.getByText("200")).toBeInTheDocument();
  expect(screen.getByText(/not a chance of future sales/)).toBeInTheDocument();
  const details = screen.getAllByText("Details");
  expect(details).toHaveLength(2);
  for (const trigger of details) {
    const disclosure = trigger.closest("details")!;
    expect(disclosure).not.toHaveAttribute("open");
    fireEvent.click(trigger);
    expect(disclosure).toHaveAttribute("open");
    fireEvent.click(trigger);
    expect(disclosure).not.toHaveAttribute("open");
  }
  expect(screen.getByText(/Weight\(j\) = C\(j\)/)).toBeInTheDocument();
  expect(screen.getByText(/accounting for ties/)).toBeInTheDocument();
  expect(screen.getByText(/accounts whose test Priority Group differs/)).toBeInTheDocument();
  const table = screen.getByRole("table");
  expect(within(table).getAllByRole("columnheader")).toHaveLength(7);
  expect(within(table).getAllByRole("row")).toHaveLength(3);
  for (const value of ["0.9995", "0.9987", "0.9989", "0.9953", "0.05%", "2.41%", "0.70%", "4.82%"]) {
    expect(within(table).getByText(value)).toBeInTheDocument();
  }
});

test("does not present a missing published weight as a calculated zero", () => {
  state.missingWeight = true;
  render(<SensitivityPage />);
  expect(screen.getByText("Unavailable")).toBeInTheDocument();
  expect(screen.queryByText("0.00%")).not.toBeInTheDocument();
});
