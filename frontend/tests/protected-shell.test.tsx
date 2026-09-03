import { render, screen } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

const replace = vi.fn();
const authState = vi.hoisted(() => ({
  role: "management" as "administrator" | "management",
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
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
});

test("management navigation shows only the operational decision workflow", () => {
  render(<ProtectedShell><div>Dashboard API content</div></ProtectedShell>);

  expect(screen.getByText("Dashboard API content")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Account Prioritization" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Detailed Analytics" })).toBeInTheDocument();
  expect(screen.getAllByRole("link")).toHaveLength(3);

  for (const hidden of ["Import Data", "Import History", "Analytics Runs", "Methodology & Governance", "RFM", "Settlement", "CART", "Sensitivity"]) {
    expect(screen.queryByRole("link", { name: hidden })).not.toBeInTheDocument();
  }
});

test("administrator navigation retains grouped operations and analysis details", () => {
  authState.role = "administrator";
  render(<ProtectedShell><div>Administrator content</div></ProtectedShell>);

  for (const group of ["Decision Support", "Reporting", "Data Management", "System / Governance", "Analysis Details"]) {
    expect(screen.getByText(group)).toBeInTheDocument();
  }
  for (const link of ["Overview", "Account Prioritization", "Detailed Analytics", "Import Data", "Import History", "Analytics Runs", "Methodology & Governance", "RFM", "Settlement", "CART", "Sensitivity"]) {
    expect(screen.getByRole("link", { name: link })).toBeInTheDocument();
  }
});
