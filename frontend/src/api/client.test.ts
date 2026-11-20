import { afterEach, describe, expect, it, vi } from "vitest";

import { RequestError, requestJson } from "./client";

type Payload = { value: string };

function isPayload(value: unknown): value is Payload {
  return (
    typeof value === "object" &&
    value !== null &&
    "value" in value &&
    typeof (value as { value: unknown }).value === "string"
  );
}

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

describe("requestJson", () => {
  it("returns the validated body for a valid JSON response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ value: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(requestJson("/api/test", { method: "GET" }, isPayload)).resolves.toEqual({
      value: "ok",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/test",
      expect.objectContaining({ method: "GET", headers: { accept: "application/json" } }),
    );
  });

  it("sends a JSON content type when a body is present", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ value: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    const body = JSON.stringify({ value: "sent" });

    await requestJson("/api/test", { method: "POST", body }, isPayload);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/test",
      expect.objectContaining({
        method: "POST",
        body,
        headers: { accept: "application/json", "content-type": "application/json" },
      }),
    );
  });

  it("reports the status for a non-2xx response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "boom" }, 503)));

    await expect(requestJson("/api/test", { method: "GET" }, isPayload)).rejects.toThrow(
      "Server responded with 503",
    );
  });

  it("reports a network failure as RequestError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const result = requestJson("/api/test", { method: "GET" }, isPayload);
    await expect(result).rejects.toBeInstanceOf(RequestError);
    await expect(result).rejects.toThrow("Could not reach the server");
  });

  it("rejects a non-JSON response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>proxy error</html>", { status: 200 })),
    );

    await expect(requestJson("/api/test", { method: "GET" }, isPayload)).rejects.toThrow(
      "Server returned a response that was not JSON",
    );
  });

  it("rejects a body with the wrong shape", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ value: 42 })));

    await expect(requestJson("/api/test", { method: "GET" }, isPayload)).rejects.toThrow(
      "Server returned an unexpected response",
    );
  });

  it("reports a timeout as RequestError", async () => {
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

    const result = requestJson("/api/test", { method: "GET" }, isPayload);
    await expect(result).rejects.toBeInstanceOf(RequestError);
    await expect(result).rejects.toThrow("Server did not respond");
  }, 1000);

  it("combines a caller-provided signal with the timeout", async () => {
    const controller = new AbortController();
    let captured: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
        captured = init?.signal ?? undefined;
        return Promise.resolve(jsonResponse({ value: "ok" }));
      }),
    );

    await requestJson("/api/test", { method: "GET", signal: controller.signal }, isPayload);

    expect(captured).not.toBe(controller.signal);
    expect(captured?.aborted).toBe(false);
    controller.abort();
    expect(captured?.aborted).toBe(true);
  });
});
