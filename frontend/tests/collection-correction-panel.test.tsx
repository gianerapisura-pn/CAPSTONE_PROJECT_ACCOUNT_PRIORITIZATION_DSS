import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { apiFetch } from "@/lib/api";
import { CollectionCorrectionPanel } from "@/components/collection-correction-panel";

const reload = vi.fn();
let loading = false;
let error = "";
let status = "pending";
let empty = false;
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/use-api", () => ({
  useApi: () => ({
    data: empty ? [] : [{
      collection_correction_review_id: "review-1",
      status,
      selected_raw_source_row_id: status === "resolved" ? "row-2" : null,
      reason: status === "resolved" ? "Verified source receipt." : null,
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
    error, loading, reload,
  }),
}));

test("administrator chooses one raw row and gives a reason before resolution", async () => {
  vi.mocked(apiFetch).mockResolvedValueOnce({ status: "resolved" });
  const user = userEvent.setup();
  render(<CollectionCorrectionPanel />);

  await user.click(screen.getByRole("button", {name:"Review corrections"}));
  expect(screen.getByText(/CR 2026-01-10 \/ 90/)).toBeInTheDocument();
  const resolve = screen.getByRole("button", { name: "Resolve correction" });
  expect(resolve).toBeDisabled();
  await user.click(screen.getAllByRole("radio")[1]);
  expect(resolve).toBeDisabled();
  await user.click(screen.getAllByRole("radio")[0]);
  expect(screen.getAllByRole("radio")[1]).not.toBeChecked();
  await user.click(screen.getAllByRole("radio")[1]);
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


test("empty queues render no wrapper, table, dropdown or history control", () => {
 empty = true;
 try { const {container} = render(<CollectionCorrectionPanel/>); expect(container).toBeEmptyDOMElement(); }
 finally { empty = false; }
});

test("loading is a compact status and errors remain visible with Retry", async () => {
 loading = true;
 const view = render(<CollectionCorrectionPanel/>);
 expect(screen.getByRole("status")).toHaveTextContent("Checking collection corrections");
 expect(view.container.querySelector(".data-section")).toBeNull();
 loading = false; error = "Request denied";
 view.rerender(<CollectionCorrectionPanel/>);
 expect(screen.getByRole("alert")).toHaveTextContent("Request denied");
 await userEvent.click(screen.getByRole("button", {name:"Retry"}));
 expect(reload).toHaveBeenCalled();
 expect(screen.queryByText(/No pending/)).not.toBeInTheDocument();
 error = "";
});

test("history is opened on demand and previously resolved evidence stays read-only", async () => {
 status = "resolved";
 try {
  render(<CollectionCorrectionPanel/>);
  expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", {name:"View correction history"}));
  expect(screen.getByText("Resolution reason: Verified source receipt.")).toBeInTheDocument();
  expect(screen.getAllByRole("radio")[1]).toBeChecked();
  for (const radio of screen.getAllByRole("radio")) expect(radio).toBeDisabled();
  expect(screen.queryByRole("button", {name:"Resolve correction"})).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", {name:"Close correction review"}));
  expect(screen.queryByRole("heading")).not.toBeInTheDocument();
 } finally {status = "pending";}
});

test("failed resolution retains the conflict and surfaces the error", async () => {
 vi.mocked(apiFetch).mockRejectedValueOnce(new Error("Resolution was not authorized"));
 render(<CollectionCorrectionPanel/>);
 await userEvent.click(screen.getByRole("button", {name:"Review corrections"}));
 await userEvent.click(screen.getAllByRole("radio")[0]);
 await userEvent.type(screen.getByRole("textbox", {name:"Resolution reason"}), "   ");
 expect(screen.getByRole("button", {name:"Resolve correction"})).toBeDisabled();
 await userEvent.type(screen.getByRole("textbox", {name:"Resolution reason"}), "Confirmed source receipt.");
 await userEvent.click(screen.getByRole("button", {name:"Resolve correction"}));
 expect(await screen.findByRole("alert")).toHaveTextContent("Resolution was not authorized");
 expect(screen.getAllByRole("radio")).toHaveLength(2);
 expect(screen.queryByText(/explicit analytics rerun is required/)).not.toBeInTheDocument();
});
