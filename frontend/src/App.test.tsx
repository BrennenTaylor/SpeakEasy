import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function stubFetch() {
  return vi.fn((input: unknown) => {
    const url = String(input);
    if (url.startsWith("/api/health")) {
      return Promise.resolve(jsonResponse({ status: "ok" }));
    }
    if (url.startsWith("/api/meals")) {
      return Promise.resolve(jsonResponse([]));
    }
    return Promise.resolve(jsonResponse({ detail: "not found" }, 404));
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the app title inside a phone-width container", () => {
    vi.stubGlobal("fetch", stubFetch());
    const { container } = render(<App />);
    expect(screen.getByRole("heading", { name: /calorie tracker/i })).toBeInTheDocument();
    expect(container.querySelector(".max-w-md")).not.toBeNull();
  });

  it("renders the server status section", () => {
    vi.stubGlobal("fetch", stubFetch());
    render(<App />);
    expect(screen.getByRole("heading", { name: /server status/i })).toBeInTheDocument();
  });

  it("renders the meal logger section", () => {
    vi.stubGlobal("fetch", stubFetch());
    render(<App />);
    expect(screen.getByRole("heading", { name: /what did you eat/i })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /describe your meal/i })).toBeInTheDocument();
  });
});
