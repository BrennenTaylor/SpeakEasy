import { requestJson } from "./client";
import type { MacroStrings } from "./meals";

export type CandidateView = {
  name: string;
  brand: string;
  serving_label: string;
  serving_grams: string;
  quantity: string;
  source: "usda_fdc" | "web_search";
  source_url: string | null;
  confidence: "high" | "low";
  incomplete: boolean;
  missing_fields: string[];
} & { [Key in keyof MacroStrings]: string | null };

export type InterpretResult = {
  candidates: CandidateView[];
  warnings: string[];
};

const MACRO_KEYS = [
  "calories",
  "protein_g",
  "carbs_g",
  "fat_g",
  "fiber_g",
  "sugar_g",
  "sodium_mg",
] as const satisfies readonly (keyof MacroStrings)[];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isCandidateView(value: unknown): value is CandidateView {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.name === "string" &&
    typeof value.brand === "string" &&
    typeof value.serving_label === "string" &&
    typeof value.serving_grams === "string" &&
    typeof value.quantity === "string" &&
    (value.source === "usda_fdc" || value.source === "web_search") &&
    isNullableString(value.source_url) &&
    (value.confidence === "high" || value.confidence === "low") &&
    typeof value.incomplete === "boolean" &&
    Array.isArray(value.missing_fields) &&
    value.missing_fields.every((field) => typeof field === "string") &&
    MACRO_KEYS.every((key) => isNullableString(value[key]))
  );
}

function isInterpretResult(value: unknown): value is InterpretResult {
  return (
    isRecord(value) &&
    Array.isArray(value.candidates) &&
    value.candidates.every(isCandidateView) &&
    Array.isArray(value.warnings) &&
    value.warnings.every((warning) => typeof warning === "string")
  );
}

export function interpretMeal(description: string, signal?: AbortSignal): Promise<InterpretResult> {
  return requestJson(
    "/api/meals/interpret",
    { method: "POST", body: JSON.stringify({ description }), signal },
    isInterpretResult,
    30_000,
  );
}
