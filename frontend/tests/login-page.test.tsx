import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import LoginPage from "@/app/login/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    demo: true,
    signIn: vi.fn(),
    demoSignIn: vi.fn(),
  }),
}));

test("demo mode retains the isolated demo workspace button", async () => {
  vi.stubEnv("NEXT_PUBLIC_DEMO_API_URL", "http://127.0.0.1:8011");
  render(<LoginPage />);
  expect(await screen.findByRole("button", {
    name: /Enter isolated demo workspace/i,
  })).toBeInTheDocument();
  expect(screen.getByText("Demo mode is active")).toBeInTheDocument();
});
