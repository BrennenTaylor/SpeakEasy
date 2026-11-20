import { afterEach, describe, expect, it, vi } from "vitest";

import { createFood, fetchFoods, updateFood } from "./foods";

const food = {
  id: 1,
  name: "Costco nuggets",
  brand: "Kirkland Signature",
  serving_label: "4 pieces",
  serving_grams: "88",
  source: "user_label",
  confidence: "high",
  aliases: ["those costco nuggets"],
  calories: "250.0000",
  protein_g: "14.0000",
  carbs_g: "16.0000",
  fat_g: "14.0000",
  fiber_g: "1.0000",
  sugar_g: "2.0000",
  sodium_mg: "400.0000",
  created_at: "2026-11-19T12:00:00",
};

const payload = {
  name: food.name,
  brand: food.brand,
  serving_label: food.serving_label,
  serving_grams: food.serving_grams,
  source: "user_label" as const,
  confidence: "high" as const,
  aliases: food.aliases,
  calories: food.calories,
  protein_g: food.protein_g,
  carbs_g: food.carbs_g,
  fat_g: food.fat_g,
  fiber_g: food.fiber_g,
  sugar_g: food.sugar_g,
  sodium_mg: food.sodium_mg,
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

describe("food client", () => {
  it("fetches foods with an encoded query and a limit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([food]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchFoods("those costco nuggets")).resolves.toEqual([food]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/foods?q=those%20costco%20nuggets&limit=20",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("creates a food from a valid payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(food, 201));
    vi.stubGlobal("fetch", fetchMock);

    await expect(createFood(payload)).resolves.toEqual(food);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/foods",
      expect.objectContaining({ method: "POST", body: JSON.stringify(payload) }),
    );
  });

  it("updates only the supplied fields of a food", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(food));
    vi.stubGlobal("fetch", fetchMock);
    const changes = { calories: "999.0000" };

    await expect(updateFood(1, changes)).resolves.toEqual(food);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/foods/1",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify(changes) }),
    );
  });

  it("rejects a food list with the wrong shape", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([{ id: 1 }])));

    await expect(fetchFoods("nuggets")).rejects.toThrow("Server returned an unexpected response");
  });
});
