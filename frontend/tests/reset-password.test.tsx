import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import ResetPasswordPage from "@/app/reset-password/page";

const mocks = vi.hoisted(() => ({ screenPassword: vi.fn(), update: vi.fn(), signOut: vi.fn() }));
vi.mock("@/lib/password-screening", () => ({ isCompromisedPassword: mocks.screenPassword }));
vi.mock("@/lib/supabase", () => ({ getSupabaseClient: () => ({ auth: {
  getSession: async () => ({ data: { session: { user: { id: "synthetic" } } } }),
  onAuthStateChange: () => ({ data: { subscription: { unsubscribe: vi.fn() } } }),
  updateUser: mocks.update, signOut: mocks.signOut,
} }) }));
beforeEach(() => { vi.clearAllMocks(); mocks.screenPassword.mockResolvedValue(false); mocks.update.mockResolvedValue({ error: null }); mocks.signOut.mockResolvedValue({ error: null }); });

async function fill() {
  const user = userEvent.setup(); render(<ResetPasswordPage />);
  await user.type(await screen.findByLabelText("New password"), "Synthetic Example 42!");
  await user.type(screen.getByLabelText("Confirm new password"), "Synthetic Example 42!");
  return user;
}

test("does not query the provider while typing; screens before updating", async () => {
  const user = await fill(); expect(mocks.screenPassword).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Update password" }));
  await screen.findByText("Password updated. Sign in with your new password.");
  expect(mocks.screenPassword).toHaveBeenCalledWith("Synthetic Example 42!");
  expect(mocks.update).toHaveBeenCalledWith({ password: "Synthetic Example 42!" });
  expect(mocks.screenPassword.mock.invocationCallOrder[0]).toBeLessThan(mocks.update.mock.invocationCallOrder[0]);
  expect(mocks.signOut).toHaveBeenCalledTimes(1);
});

test("a breached password never reaches Supabase update", async () => {
  mocks.screenPassword.mockResolvedValue(true); const user = await fill();
  await user.click(screen.getByRole("button", { name: "Update password" }));
  await screen.findByText(/appears in known data breaches/);
  expect(mocks.update).not.toHaveBeenCalled(); expect(mocks.signOut).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Update password" })).toBeEnabled();
});

test("provider failure blocks the update and permits retry", async () => {
  mocks.screenPassword.mockRejectedValueOnce(new Error("Unavailable")); const user = await fill();
  await user.click(screen.getByRole("button", { name: "Update password" }));
  await screen.findByText(/password safety check is unavailable/);
  expect(mocks.update).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Update password" }));
  await screen.findByText("Password updated. Sign in with your new password.");
});

test("mismatch is rejected before screening or update", async () => {
  const user = await fill(); await user.type(screen.getByLabelText("Confirm new password"), "x");
  await user.click(screen.getByRole("button", { name: "Update password" }));
  expect(screen.getByText("The passwords do not match.")).toBeInTheDocument();
  expect(mocks.screenPassword).not.toHaveBeenCalled(); expect(mocks.update).not.toHaveBeenCalled();
});

test("Supabase rejection is reported without a success claim", async () => {
  mocks.update.mockResolvedValue({ error: { message: "Invalid recovery" } }); const user = await fill();
  await user.click(screen.getByRole("button", { name: "Update password" }));
  await screen.findByText(/Password could not be updated/); expect(mocks.signOut).not.toHaveBeenCalled();
});

test("the submit button stays disabled while screening is pending", async () => {
  let resolve!: (value: boolean) => void;
  mocks.screenPassword.mockReturnValue(new Promise<boolean>(done => { resolve = done; }));
  const user = await fill(); await user.click(screen.getByRole("button", { name: "Update password" }));
  expect(screen.getByRole("button", { name: "Updating..." })).toBeDisabled(); expect(mocks.update).not.toHaveBeenCalled();
  resolve(false); await waitFor(() => expect(mocks.update).toHaveBeenCalledTimes(1));
});
