import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the app title inside a phone-width container", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));
    const { container } = render(<App />);
    expect(screen.getByRole("heading", { name: /calorie tracker/i })).toBeInTheDocument();
    expect(container.querySelector(".max-w-md")).not.toBeNull();
  });

  it("renders the server status section", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));
    render(<App />);
    expect(screen.getByRole("heading", { name: /server status/i })).toBeInTheDocument();
  });
});
