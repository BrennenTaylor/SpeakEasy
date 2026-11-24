import { useCallback, useEffect, useRef, useState } from "react";

import type { Food } from "../api/foods";
import type { MatchView } from "../api/interpretation";
import {
  createMeal,
  fetchMeals,
  previewMeal,
  type MacroStrings,
  type Meal,
  type MealCreate,
} from "../api/meals";
import { FoodSearch, type FoodPrefill } from "./FoodSearch";
import { MealCandidates } from "./MealCandidates";
import { MealReview, type ReviewItem } from "./MealReview";
import { RecentMeals } from "./RecentMeals";

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Something went wrong";
}

function payloadFor(rawInput: string, items: ReviewItem[]): MealCreate {
  return {
    raw_input: rawInput,
    eaten_at: new Date().toISOString(),
    items: items.map(({ food, quantity }) => ({
      food_id: food.id,
      quantity,
      unit: "serving",
    })),
  };
}

function prefillFromMatch(match: MatchView): FoodPrefill {
  const text = (value: string | null) => value ?? "";
  return {
    name: match.name,
    brand: match.brand,
    serving_label: match.serving_label,
    serving_grams: text(match.serving_grams),
    calories: text(match.calories),
    protein_g: text(match.protein_g),
    carbs_g: text(match.carbs_g),
    fat_g: text(match.fat_g),
    fiber_g: text(match.fiber_g),
    sugar_g: text(match.sugar_g),
    sodium_mg: text(match.sodium_mg),
    source: "user_label",
    source_url: match.source_url,
    confidence: "low",
    aliases: [],
  };
}

export function MealLogger() {
  const [rawInput, setRawInput] = useState("");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [totals, setTotals] = useState<MacroStrings | null>(null);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [foodPrefill, setFoodPrefill] = useState<FoodPrefill | null>(null);

  const previewControllerRef = useRef<AbortController | null>(null);
  const previewVersionRef = useRef(0);
  const reviewedVersionRef = useRef<number | null>(null);
  const nextItemIdRef = useRef(1);
  const itemsRef = useRef(items);
  const wasBlankRef = useRef(true);

  useEffect(() => {
    const controller = new AbortController();
    fetchMeals(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setMeals(result);
        }
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(errorMessage(cause));
        }
      });
    return () => controller.abort();
  }, [reloadKey]);

  useEffect(
    () => () => {
      previewControllerRef.current?.abort();
      previewControllerRef.current = null;
    },
    [],
  );

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  const invalidatePreview = useCallback(() => {
    previewControllerRef.current?.abort();
    previewControllerRef.current = null;
    previewVersionRef.current += 1;
    reviewedVersionRef.current = null;
    setTotals(null);
    setError(null);
  }, []);

  const runPreview = useCallback((nextRawInput: string, nextItems: ReviewItem[]) => {
    const version = previewVersionRef.current;
    previewControllerRef.current?.abort();
    previewControllerRef.current = null;
    if (nextItems.length === 0 || nextRawInput.trim() === "") {
      setTotals(null);
      return;
    }

    const controller = new AbortController();
    previewControllerRef.current = controller;
    previewMeal(payloadFor(nextRawInput, nextItems), controller.signal)
      .then((result) => {
        if (version !== previewVersionRef.current || controller.signal.aborted) {
          return;
        }
        setTotals(result);
        reviewedVersionRef.current = version;
      })
      .catch((cause: unknown) => {
        if (version !== previewVersionRef.current || controller.signal.aborted) {
          return;
        }
        setTotals(null);
        reviewedVersionRef.current = null;
        setError(errorMessage(cause));
      });
  }, []);

  useEffect(() => {
    const isBlank = rawInput.trim() === "";
    const justBecameNonBlank = wasBlankRef.current && !isBlank;
    wasBlankRef.current = isBlank;

    if (isBlank || justBecameNonBlank) {
      runPreview(rawInput, itemsRef.current);
      return;
    }

    const timer = window.setTimeout(() => runPreview(rawInput, itemsRef.current), 250);
    return () => window.clearTimeout(timer);
  }, [rawInput, runPreview]);

  function handleRawInputChange(value: string) {
    invalidatePreview();
    setRawInput(value);
  }

  function handleAdd(food: Food, quantity = "1") {
    invalidatePreview();
    // Build from the ref and update it synchronously: the picker adds every
    // selected group in one tick, so the render-closure `items` would be stale
    // for all but the first call and drop foods from the review.
    const nextItems = [...itemsRef.current, { id: nextItemIdRef.current++, food, quantity }];
    itemsRef.current = nextItems;
    setItems(nextItems);
    runPreview(rawInput, nextItems);
  }

  function handleQuantityChange(itemId: number, quantity: string) {
    invalidatePreview();
    const nextItems = items.map((item) => (item.id === itemId ? { ...item, quantity } : item));
    setItems(nextItems);
    runPreview(rawInput, nextItems);
  }

  function handleRemove(itemId: number) {
    invalidatePreview();
    const nextItems = items.filter((item) => item.id !== itemId);
    setItems(nextItems);
    runPreview(rawInput, nextItems);
  }

  async function handleConfirm() {
    if (
      rawInput.trim() === "" ||
      items.length === 0 ||
      totals === null ||
      submitting ||
      reviewedVersionRef.current !== previewVersionRef.current
    ) {
      return;
    }
    setError(null);
    setSubmitting(true);
    previewControllerRef.current?.abort();
    try {
      await createMeal(payloadFor(rawInput, items));
      invalidatePreview();
      setRawInput("");
      setItems([]);
      setReloadKey((key) => key + 1);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="w-full min-w-0 space-y-5">
      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm break-words text-red-900"
        >
          {error}
        </p>
      )}

      <div className="w-full min-w-0 space-y-1">
        <label htmlFor="meal-raw-input" className="block text-sm font-medium text-gray-700">
          Describe your meal
        </label>
        <textarea
          id="meal-raw-input"
          rows={2}
          value={rawInput}
          onChange={(event) => handleRawInputChange(event.target.value)}
          placeholder="e.g. two servings of nuggets"
          className="w-full min-w-0 rounded border border-gray-300 px-3 py-2 text-sm"
        />
      </div>

      <MealCandidates
        rawInput={rawInput}
        onAdd={handleAdd}
        onComplete={(match) => setFoodPrefill(prefillFromMatch(match))}
      />

      <FoodSearch
        onAdd={handleAdd}
        prefill={foodPrefill}
        onPrefillUsed={() => setFoodPrefill(null)}
      />

      <MealReview
        items={items}
        totals={totals}
        submitting={submitting}
        canConfirm={rawInput.trim() !== "" && totals !== null}
        onQuantityChange={handleQuantityChange}
        onRemove={handleRemove}
        onConfirm={() => void handleConfirm()}
      />

      <RecentMeals meals={meals} />
    </div>
  );
}
