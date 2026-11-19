import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HealthCheck } from "./HealthCheck";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function clickRetry(button: HTMLElement): void {
  const reactPropsKey = Object.keys(button).find((k) => k.startsWith("__reactProps$"));
  if (reactPropsKey) {
    (button as unknown as Record<string, { onClick?: () => void }>)[reactPropsKey]?.onClick?.();
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HealthCheck", () => {
  it("shows loading and then OK", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));
    render(<HealthCheck />);
    expect(screen.getByRole("status")).toHaveTextContent(/checking/i);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/connected/i));
  });

  it("shows an error and recovers on retry", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(jsonResponse({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    render(<HealthCheck />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not reach the server/i);

    await user.click(screen.getByRole("button", { name: /try again/i }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/connected/i));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("treats an unexpected payload as an error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "degraded" })));
    render(<HealthCheck />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/unexpected response/i);
  });

  it("keeps the retry button disabled while a request is in flight", async () => {
    const user = userEvent.setup();
    let resolve: (value: Response) => void = () => {};
    const pending = new Promise<Response>((r) => {
      resolve = r;
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: "ok" }))
      .mockReturnValueOnce(pending);
    vi.stubGlobal("fetch", fetchMock);

    render(<HealthCheck />);
    await screen.findByText(/connected/i);

    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(screen.getByRole("button", { name: /try again/i })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    resolve(jsonResponse({ status: "ok" }));
    await waitFor(() => expect(screen.getByRole("button", { name: /try again/i })).toBeEnabled());
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("aborts the live request on unmount", async () => {
    let capturedSignal: AbortSignal | null | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
        capturedSignal = init?.signal;
        return new Promise(() => {});
      }),
    );

    const { unmount } = render(<HealthCheck />);
    expect(capturedSignal).toBeDefined();
    expect(capturedSignal?.aborted).toBe(false);

    unmount();

    expect(capturedSignal?.aborted).toBe(true);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not allow an aborted in-flight request to overwrite visible state", async () => {
    let rejectFirst: (reason?: unknown) => void = () => {};
    const firstPromise = new Promise<Response>((_resolve, reject) => {
      rejectFirst = reject;
    });

    let resolveSecond: (value: Response) => void = () => {};
    const secondPromise = new Promise<Response>((resolve) => {
      resolveSecond = resolve;
    });

    let capturedFirstSignal: AbortSignal | null | undefined;
    let capturedSecondSignal: AbortSignal | null | undefined;

    const fetchMock = vi
      .fn()
      .mockImplementationOnce((_url: string, init?: RequestInit) => {
        capturedFirstSignal = init?.signal;
        return firstPromise;
      })
      .mockImplementationOnce((_url: string, init?: RequestInit) => {
        capturedSecondSignal = init?.signal;
        return secondPromise;
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<HealthCheck />);
    expect(screen.getByRole("status")).toHaveTextContent(/checking/i);
    expect(capturedFirstSignal?.aborted).toBe(false);

    clickRetry(screen.getByRole("button", { name: /try again/i }));

    expect(capturedFirstSignal?.aborted).toBe(true);
    expect(capturedSecondSignal?.aborted).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    rejectFirst(new DOMException("The operation was aborted", "AbortError"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/checking/i);

    resolveSecond(jsonResponse({ status: "ok" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/connected/i));
  });
});
