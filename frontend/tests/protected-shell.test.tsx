import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";

const replace = vi.fn();
const authState = vi.hoisted(() => ({
  role: "management" as "administrator" | "management",
  path: "/dashboard",
}));

vi.mock("next/navigation", () => ({
  usePathname: () => authState.path,
  useRouter: () => ({ replace }),
}));
vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({
    user: {
      userId: "u1",
      email: "user@example.test",
      role: authState.role,
      displayName: authState.role === "administrator" ? "Administrator" : "Manager",
      demo: false,
    },
    loading: false,
    signOut: vi.fn(),
  }),
}));

import { ProtectedShell } from "@/components/protected-shell";

beforeEach(() => {
  authState.role = "management";
  authState.path = "/dashboard";
});

test("management navigation includes the shared analytical workflow", async () => {
  const user = userEvent.setup();
  render(<ProtectedShell><div>Dashboard API content</div></ProtectedShell>);

  expect(screen.getByText("Dashboard API content")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Account Prioritization" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Detailed Analytics" })).toBeInTheDocument();
  const toggle = screen.getByRole("button", { name: "Advanced Analysis" });
  await user.click(toggle);
  for (const link of ["RFM", "Settlement", "With Future Sales", "Sensitivity"]) {
    expect(screen.getByRole("link", { name: link })).toBeInTheDocument();
  }
  expect(screen.queryByRole("link", { name: "Methodology & Governance" })).not.toBeInTheDocument();
});

test("administrator advanced navigation is collapsed by default and retains every route", async () => {
  authState.role = "administrator";
  const user = userEvent.setup();
  render(<ProtectedShell><div>Administrator content</div></ProtectedShell>);

  for (const group of ["Decision Support", "Reporting", "Data Management"]) {
    expect(screen.getByText(group)).toBeInTheDocument();
  }
  for (const link of ["Overview", "Account Prioritization", "Detailed Analytics", "Import Data", "Import History", "Analytics Runs"]) {
    expect(screen.getByRole("link", { name: link })).toBeInTheDocument();
  }
  const toggle = screen.getByRole("button", { name: "Advanced Analysis" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByRole("link", { name: "Methodology & Governance" })).toBeInTheDocument();

  await user.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  for (const link of ["RFM", "Settlement", "With Future Sales", "Sensitivity"]) {
    expect(screen.getByRole("link", { name: link })).toBeInTheDocument();
  }
});

test("management direct access to an administrator route is denied before page content renders", () => {
  authState.path = "/import";
  render(<ProtectedShell><div>Restricted import content</div></ProtectedShell>);

  expect(screen.getByRole("alert")).toHaveTextContent("Administrator access required");
  expect(screen.queryByText("Restricted import content")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Return to Overview" })).toHaveAttribute("href", "/dashboard");
});
