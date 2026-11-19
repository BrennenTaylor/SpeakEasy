import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchHealth } from "./health";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("fetchHealth", () => {
  it("returns the parsed body for a valid response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));
    await expect(fetchHealth()).resolves.toEqual({ status: "ok" });
  });

  it("rejects a 200 with the wrong shape", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "degraded" })));
    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiError);
  });

  it("rejects a non-JSON body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>proxy error</html>", { status: 200 })),
    );
    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiError);
  });

  it("reports the status code for a non-2xx response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "boom" }, 503)));
    await expect(fetchHealth()).rejects.toThrow(/503/);
  });

  it("wraps a network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiError);
  });

  it("reports a timeout when the server never responds", async () => {
    const timeout = new AbortController();
    timeout.abort(new DOMException("timed out", "TimeoutError"));
    vi.spyOn(AbortSignal, "timeout").mockReturnValue(timeout.signal);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
        const signal = init?.signal;
        return new Promise<Response>((_resolve, reject) => {
          if (signal?.aborted) reject(signal.reason);
          else signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        });
      }),
    );

    await expect(fetchHealth()).rejects.toThrow(/did not respond/i);
  }, 1000);
});
