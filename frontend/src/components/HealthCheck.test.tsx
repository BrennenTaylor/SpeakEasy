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

function createAbortableFetch() {
  return vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
    return new Promise((_resolve, reject) => {
      const signal = init?.signal;
      if (signal?.aborted) {
        reject(new DOMException("The operation was aborted", "AbortError"));
        return;
      }
      signal?.addEventListener(
        "abort",
        () => {
          reject(new DOMException("The operation was aborted", "AbortError"));
        },
        { once: true },
      );
    });
  });
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

  it("suppresses error state when unmounted during initial check", async () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const fetchMock = createAbortableFetch();
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<HealthCheck />);
    expect(screen.getByRole("status")).toHaveTextContent(/checking/i);

    unmount();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it("suppresses error state when unmounted during a retry request", async () => {
    const user = userEvent.setup();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    let callCount = 0;
    const fetchMock = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      if (callCount === 0) {
        callCount++;
        return Promise.reject(new TypeError("Failed to fetch"));
      }
      return new Promise((_resolve, reject) => {
        const signal = init?.signal;
        if (signal?.aborted) {
          reject(new DOMException("The operation was aborted", "AbortError"));
          return;
        }
        signal?.addEventListener(
          "abort",
          () => {
            reject(new DOMException("The operation was aborted", "AbortError"));
          },
          { once: true },
        );
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<HealthCheck />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not reach the server/i);

    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(screen.getByRole("status")).toHaveTextContent(/checking/i);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    unmount();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });
});
