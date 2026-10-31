import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { AuditLogPanel } from "@/components/audit-log-panel";

const calls = vi.hoisted(() => ({ paths: [] as string[] }));
vi.mock("@/lib/use-api", () => ({ useApi: (path: string) => {
  calls.paths.push(path);
  const page = path.includes("page=2") ? 2 : 1;
  return { data: { items: [{ id: String(page), created_at: "2026-10-31T08:00:00Z", actor: "Giane", action: "import preview", record_type: "import batch" }], total: 12, page, page_size: 10, total_pages: 2 }, loading: false, error: "", reload: vi.fn() };
} }));

test("audit log uses the existing ten-row navigation and descriptive columns", () => {
  render(<AuditLogPanel />);
  expect(screen.getByRole("heading", { name: "Activity audit log" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Previous audit log page" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Next audit log page" }));
  expect(calls.paths.at(-1)).toBe("/audit-log?page=2&page_size=10");
  expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next audit log page" })).toBeDisabled();
});
