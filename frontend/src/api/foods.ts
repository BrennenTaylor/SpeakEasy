import { requestJson } from "./client";
import { isMacroStrings, type MacroStrings } from "./meals";

export type FoodCreate = MacroStrings & {
  name: string;
  brand: string;
  serving_label: string;
  serving_grams: string;
  source?: "user_label";
  confidence: "high" | "low";
  aliases?: string[];
};

export type Food = MacroStrings & {
  id: number;
  name: string;
  brand: string;
  serving_label: string;
  serving_grams: string;
  source: "user_label";
  confidence: "high" | "low";
  aliases: string[];
  created_at: string;
};

function isFood(value: unknown): value is Food {
  if (!isMacroStrings(value)) {
    return false;
  }
  return (
    typeof value.id === "number" &&
    typeof value.name === "string" &&
    typeof value.brand === "string" &&
    typeof value.serving_label === "string" &&
    typeof value.serving_grams === "string" &&
    value.source === "user_label" &&
    (value.confidence === "high" || value.confidence === "low") &&
    Array.isArray(value.aliases) &&
    value.aliases.every((alias) => typeof alias === "string") &&
    typeof value.created_at === "string"
  );
}

function isFoodList(value: unknown): value is Food[] {
  return Array.isArray(value) && value.every(isFood);
}

export function fetchFoods(query: string, signal?: AbortSignal): Promise<Food[]> {
  return requestJson(
    `/api/foods?q=${encodeURIComponent(query)}&limit=20`,
    { method: "GET", signal },
    isFoodList,
  );
}

export function createFood(payload: FoodCreate): Promise<Food> {
  return requestJson("/api/foods", { method: "POST", body: JSON.stringify(payload) }, isFood);
}

export function updateFood(foodId: number, changes: Partial<FoodCreate>): Promise<Food> {
  return requestJson(
    `/api/foods/${foodId}`,
    { method: "PATCH", body: JSON.stringify(changes) },
    isFood,
  );
}
