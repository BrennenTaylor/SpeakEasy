import { afterEach, describe, expect, it, vi } from "vitest";

import { createMeal, fetchMeals, previewMeal } from "./meals";

const totals = {
  calories: "210.0000",
  protein_g: "15.0000",
  carbs_g: "17.0000",
  fat_g: "14.0000",
  fiber_g: "1.5000",
  sugar_g: "3.0000",
  sodium_mg: "600.0000",
};

const meal = {
  id: 9,
  raw_input: "two eggs and nuggets",
  eaten_at: "2026-11-19T12:00:00",
  created_at: "2026-11-19T12:00:01",
  items: [
    {
      id: 5,
      food_id: 1,
      quantity: "1.5",
      unit: "serving",
      serving_label: "4 pieces",
      serving_grams: "88",
      source: "user_label",
      confidence: "high",
      created_at: "2026-11-19T12:00:01",
      ...totals,
    },
  ],
  totals,
};

const payload = {
  raw_input: "two eggs and nuggets",
  eaten_at: "2026-11-19T12:00:00",
  items: [{ food_id: 1, quantity: "1.5" }],
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

describe("meal client", () => {
  it("previews totals from a meal payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(totals));
    vi.stubGlobal("fetch", fetchMock);

    await expect(previewMeal(payload)).resolves.toEqual(totals);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/meals/preview",
      expect.objectContaining({ method: "POST", body: JSON.stringify(payload) }),
    );
  });

  it("creates a meal from a valid payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(meal, 201));
    vi.stubGlobal("fetch", fetchMock);

    await expect(createMeal(payload)).resolves.toEqual(meal);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/meals",
      expect.objectContaining({ method: "POST", body: JSON.stringify(payload) }),
    );
  });

  it("fetches recent meals with a limit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([meal]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchMeals()).resolves.toEqual([meal]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/meals?limit=20",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("rejects totals with the wrong shape", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ calories: "210.0000" })));

    await expect(previewMeal(payload)).rejects.toThrow("Server returned an unexpected response");
  });
});
