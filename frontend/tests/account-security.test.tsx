import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import ProfilePage from "@/app/(protected)/profile/page";
import { requestEmailChange, requestPasswordReset } from "@/lib/account-security";
import { ResultValue } from "@/components/result-explanation";

const state = vi.hoisted(() => ({ role: "management", reset: vi.fn(), update: vi.fn(), api: vi.fn(), signOut: vi.fn() }));
vi.mock("@/lib/supabase", () => ({ getSupabaseClient: () => ({ auth: { resetPasswordForEmail: state.reset, updateUser: state.update } }) }));
vi.mock("@/lib/api", () => ({ apiFetch: (...args: unknown[]) => state.api(...args) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/components/auth-provider", () => ({ useAuth: () => ({ user: { role: state.role, demo: false }, refreshProfile: vi.fn(), signOut: state.signOut }) }));
vi.mock("@/lib/use-api", () => ({ useApi: () => ({ data: { user_id: "own-user", email: "manager@example.test", display_name: "Manager", role: state.role, status: "active" }, loading: false, error: "", reload: vi.fn() }) }));

beforeEach(() => { state.reset.mockResolvedValue({ error: null }); state.update.mockResolvedValue({ error: null }); state.api.mockResolvedValue({}); });

test.each(["administrator", "management"])("%s can update only their display name", async role => {
  state.role = role;
  const user = userEvent.setup();
  render(<ProfilePage />);
  await user.click(screen.getByRole("button", { name: "Edit Profile" }));
  await user.clear(screen.getByLabelText("Display name"));
  expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
  await user.type(screen.getByLabelText("Display name"), "PESLC Manager");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(state.api).toHaveBeenCalledWith("/profile", { method: "PATCH", body: JSON.stringify({ display_name: "PESLC Manager" }) }));
  expect(screen.queryByLabelText("Role")).not.toBeInTheDocument();
});

test("email changes use provider verification and recovery returns to the local reset route", async () => {
  await requestEmailChange("new@example.test");
  expect(state.update).toHaveBeenCalledWith({ email: "new@example.test" });
  await requestPasswordReset("manager@example.test");
  expect(state.reset).toHaveBeenCalledWith("manager@example.test", { redirectTo: new URL("/reset-password", window.location.origin).toString() });
});

test("result explanations open with keyboard and close with Escape", () => {
  render(<ResultValue metric="fps">0.5</ResultValue>);
  const value = screen.getByRole("button", { name: "0.5" });
  fireEvent.keyDown(value, { key: "Enter" });
  expect(screen.getByRole("tooltip")).toHaveTextContent("Final Priority Score");
  fireEvent.keyDown(window, { key: "Escape" });
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});
