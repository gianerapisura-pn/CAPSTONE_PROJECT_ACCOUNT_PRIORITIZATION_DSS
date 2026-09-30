import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { apiFetch } from "@/lib/api";
import { CollectionCorrectionPanel } from "@/components/collection-correction-panel";

const reload = vi.fn();
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/use-api", () => ({
  useApi: () => ({
    data: [{
      collection_correction_review_id: "review-1",
      status: "pending",
      selected_raw_source_row_id: null,
      reason: null,
      candidates: [
        {
          raw_source_row_id: "row-1", import_batch_id: "batch-11111111",
          source_sheet: "CSV", source_row_number: 2, account_name: "ACME",
          si_no: "SI-1", si_date: "2026-01-01", si_amount: "100",
          cr_no: "CR-1", cr_date: "2026-01-10", cr_amount: "100",
          ewt: "0", payment_mode: "Bank", payment_status: "Fully Paid",
        },
        {
          raw_source_row_id: "row-2", import_batch_id: "batch-22222222",
          source_sheet: "CSV", source_row_number: 2, account_name: "ACME",
          si_no: "SI-1", si_date: "2026-01-01", si_amount: "100",
          cr_no: "CR-1", cr_date: "2026-01-10", cr_amount: "90",
          ewt: "0", payment_mode: "Bank", payment_status: "Fully Paid",
        },
      ],
    }],
    error: "", loading: false, reload,
  }),
}));

test("administrator chooses one raw row and gives a reason before resolution", async () => {
  vi.mocked(apiFetch).mockResolvedValueOnce({ status: "resolved" });
  const user = userEvent.setup();
  render(<CollectionCorrectionPanel />);

  expect(screen.getByText(/CR 2026-01-10 \/ 90/)).toBeInTheDocument();
  const resolve = screen.getByRole("button", { name: "Resolve correction" });
  expect(resolve).toBeDisabled();
  await user.click(screen.getAllByRole("radio")[1]);
  expect(resolve).toBeDisabled();
  await user.type(screen.getByRole("textbox", { name: "Resolution reason" }), "Verified against collection receipt.");
  await user.click(resolve);

  expect(apiFetch).toHaveBeenCalledWith(
    "/collection-corrections/review-1/resolve",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        selected_raw_source_row_id: "row-2",
        reason: "Verified against collection receipt.",
      }),
    }),
  );
  expect(await screen.findByText(/explicit analytics rerun is required/)).toBeInTheDocument();
  expect(reload).toHaveBeenCalled();
});
