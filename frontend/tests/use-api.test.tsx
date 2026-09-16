import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

const { apiFetchMock } = vi.hoisted(() => ({ apiFetchMock: vi.fn() }));
vi.mock("@/lib/api", () => ({ apiFetch: apiFetchMock }));

import { useApi } from "@/lib/use-api";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}

function Harness({ path }: { path: string }) {
  const { data, error, loading } = useApi<string>(path);
  return <div>
    <span>{loading ? "loading" : "settled"}</span>
    <span>{data ?? "no data"}</span>
    <span>{error || "no error"}</span>
  </div>;
}

beforeEach(() => {
  apiFetchMock.mockReset();
});

test("newest request wins when an older response resolves last", async () => {
  const older = deferred<string>();
  const newer = deferred<string>();
  apiFetchMock.mockImplementation((path: string) => path === "/old" ? older.promise : newer.promise);

  const view = render(<Harness path="/old" />);
  await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith(
    "/old",
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  ));

  view.rerender(<Harness path="/new" />);
  await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith(
    "/new",
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  ));

  await act(async () => { newer.resolve("new result"); });
  expect(await screen.findByText("new result")).toBeInTheDocument();
  expect(screen.getByText("settled")).toBeInTheDocument();

  await act(async () => { older.resolve("stale result"); });
  expect(screen.getByText("new result")).toBeInTheDocument();
  expect(screen.queryByText("stale result")).not.toBeInTheDocument();
  expect(screen.getByText("settled")).toBeInTheDocument();
  expect(screen.getByText("no error")).toBeInTheDocument();
});
