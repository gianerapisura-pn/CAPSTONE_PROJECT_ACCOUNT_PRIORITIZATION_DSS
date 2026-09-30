import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { PowerBIRefreshStatus } from "@/components/power-bi-refresh-status";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { useAuth } from "@/components/auth-provider";

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/use-api", () => ({ useApi: vi.fn() }));
vi.mock("@/components/auth-provider", () => ({ useAuth: vi.fn() }));

const useApiMock = vi.mocked(useApi);
const useAuthMock = vi.mocked(useAuth);
const apiFetchMock = vi.mocked(apiFetch);
const reload = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();
  useAuthMock.mockReturnValue({ user: { role: "administrator" } } as ReturnType<typeof useAuth>);
  useApiMock.mockReturnValue({
    data: {
      analysis_run_id: "run-1", configured: true, status: "failed",
      attempt_count: 1, requested_at: null, completed_at: null,
      error_code: "power_bi_http_429",
    },
    error: "", loading: false, reload,
  });
  apiFetchMock.mockResolvedValue({});
});

test("administrator sees failed refresh and can retry without changing Web publication", async () => {
  render(<PowerBIRefreshStatus />);
  expect(screen.getByText("Power BI: Failed")).toBeInTheDocument();
  expect(screen.getByText(/Web DSS data remains published/)).toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole("button", { name: "Retry refresh" }));
  expect(apiFetchMock).toHaveBeenCalledWith(
    "/reports/power-bi-refresh/retry", { method: "POST" },
  );
  expect(reload).toHaveBeenCalled();
});

test("management sees status but no retry control", () => {
  useAuthMock.mockReturnValue({ user: { role: "management" } } as ReturnType<typeof useAuth>);
  render(<PowerBIRefreshStatus />);
  expect(screen.getByText("Power BI: Failed")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Retry refresh" })).not.toBeInTheDocument();
});

test("requested is distinct from completed", () => {
  useApiMock.mockReturnValue({
    data: {
      analysis_run_id: "run-1", configured: true, status: "requested",
      attempt_count: 1, requested_at: "2030-06-01T12:00:00Z",
      completed_at: null, error_code: null,
    },
    error: "", loading: false, reload,
  });
  render(<PowerBIRefreshStatus />);
  expect(screen.getByText("Power BI: Refresh requested")).toBeInTheDocument();
  expect(screen.getByText(/completion is pending/)).toBeInTheDocument();
  expect(screen.queryByText("Power BI: Completed")).not.toBeInTheDocument();
});
