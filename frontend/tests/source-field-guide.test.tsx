import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SourceFieldGuide } from "@/components/source-field-guide";

test("all ten source fields explain actual validation without turning missing EWT into zero", async () => {
  render(<SourceFieldGuide />);
  expect(document.querySelectorAll("details")).toHaveLength(10);
  for (const name of ["ACCOUNT NAMES","SI NO.","SI DATE","SI AMOUNT","CR NO.","CR DATE","CR AMOUNT","EWT","PAYMENT MODE","PAYMENT STATUS"]) {
    const summary=screen.getByText(name,{exact:true});
    expect(summary.tagName).toBe("SUMMARY");
    await userEvent.click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
  }
  expect(screen.getByText(/blank is not zero/)).toBeInTheDocument();
  expect(screen.getByText(/preserve leading zeros/)).toBeInTheDocument();
  expect(screen.getByText(/partial or unsupported statuses require review/)).toBeInTheDocument();
  expect(screen.getByText(/does not impose a fixed payment-method list/)).toBeInTheDocument();
});
