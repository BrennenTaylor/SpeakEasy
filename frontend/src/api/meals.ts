import { requestJson } from "./client";

export type MacroStrings = {
  calories: string;
  protein_g: string;
  carbs_g: string;
  fat_g: string;
  fiber_g: string;
  sugar_g: string;
  sodium_mg: string;
};

export type MealItem = MacroStrings & {
  id: number;
  food_id: number;
  quantity: string;
  unit: "serving";
  serving_label: string;
  serving_grams: string;
  source: string;
  confidence: string;
  created_at: string;
};

export type Meal = {
  id: number;
  raw_input: string;
  eaten_at: string;
  created_at: string;
  items: MealItem[];
  totals: MacroStrings;
};

export type MealCreate = {
  raw_input: string;
  eaten_at: string;
  items: { food_id: number; quantity: string; unit?: "serving" }[];
};

export const MACRO_ROWS = [
  { key: "calories", label: "Calories" },
  { key: "protein_g", label: "Protein (g)" },
  { key: "carbs_g", label: "Carbs (g)" },
  { key: "fat_g", label: "Fat (g)" },
  { key: "fiber_g", label: "Fiber (g)" },
  { key: "sugar_g", label: "Sugar (g)" },
  { key: "sodium_mg", label: "Sodium (mg)" },
] as const satisfies readonly { key: keyof MacroStrings; label: string }[];

const MACRO_KEYS = MACRO_ROWS.map((row) => row.key);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isMacroStrings(value: unknown): value is MacroStrings & Record<string, unknown> {
  if (!isRecord(value)) {
    return false;
  }
  return MACRO_KEYS.every((key) => typeof value[key] === "string");
}

function isMealItem(value: unknown): value is MealItem {
  if (!isMacroStrings(value)) {
    return false;
  }
  return (
    typeof value.id === "number" &&
    typeof value.food_id === "number" &&
    typeof value.quantity === "string" &&
    value.unit === "serving" &&
    typeof value.serving_label === "string" &&
    typeof value.serving_grams === "string" &&
    typeof value.source === "string" &&
    typeof value.confidence === "string" &&
    typeof value.created_at === "string"
  );
}

function isMeal(value: unknown): value is Meal {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "number" &&
    typeof value.raw_input === "string" &&
    typeof value.eaten_at === "string" &&
    typeof value.created_at === "string" &&
    Array.isArray(value.items) &&
    value.items.every(isMealItem) &&
    isMacroStrings(value.totals)
  );
}

function isMealList(value: unknown): value is Meal[] {
  return Array.isArray(value) && value.every(isMeal);
}

export function fetchMeals(signal?: AbortSignal): Promise<Meal[]> {
  return requestJson("/api/meals?limit=20", { method: "GET", signal }, isMealList);
}

export function createMeal(payload: MealCreate): Promise<Meal> {
  return requestJson("/api/meals", { method: "POST", body: JSON.stringify(payload) }, isMeal);
}

export function previewMeal(payload: MealCreate, signal?: AbortSignal): Promise<MacroStrings> {
  return requestJson(
    "/api/meals/preview",
    { method: "POST", body: JSON.stringify(payload), signal },
    isMacroStrings,
  );
}
