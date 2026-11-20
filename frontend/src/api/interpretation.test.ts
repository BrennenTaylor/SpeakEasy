import { afterEach, describe, expect, it, vi } from "vitest";

import { interpretMeal } from "./interpretation";

const result = {
  candidates: [
    {
      name: "Chick-fil-A sandwich",
      brand: "Chick-fil-A",
      serving_label: "1 sandwich",
      serving_grams: "187.0000",
      quantity: "1.0000",
      source: "usda_fdc",
      source_url: "https://fdc.example/170790",
      confidence: "high",
      incomplete: false,
      missing_fields: [],
      calories: "465.6300",
      protein_g: "30.4000",
      carbs_g: "39.1000",
      fat_g: "20.9000",
      fiber_g: "2.6000",
      sugar_g: "0.0000",
      sodium_mg: "1407.0000",
    },
  ],
  warnings: [],
};

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

describe("interpretation client", () => {
  it("parses an interpretation response and uses the long timeout", async () => {
    const timeoutSpy = vi.spyOn(AbortSignal, "timeout");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(result));
    vi.stubGlobal("fetch", fetchMock);

    await expect(interpretMeal("chick fil a sandwich")).resolves.toEqual(result);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/meals/interpret",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ description: "chick fil a sandwich" }),
      }),
    );
    expect(timeoutSpy).toHaveBeenCalledWith(30_000);
  });

  it("passes a caller signal through to the request", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(result));
    vi.stubGlobal("fetch", fetchMock);

    await interpretMeal("lunch", controller.signal);

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(init?.signal).toBeDefined();
  });

  it("rejects a candidate with an unknown source", async () => {
    const invalid = {
      ...result,
      candidates: [{ ...result.candidates[0], source: "made_up" }],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(invalid)));

    await expect(interpretMeal("lunch")).rejects.toThrow("Server returned an unexpected response");
  });

  it("accepts an incomplete candidate with null macros", async () => {
    const incomplete = {
      ...result,
      candidates: [
        {
          ...result.candidates[0],
          incomplete: true,
          missing_fields: ["sugar_g"],
          sugar_g: null,
        },
      ],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(incomplete)));

    await expect(interpretMeal("lunch")).resolves.toEqual(incomplete);
  });
});
