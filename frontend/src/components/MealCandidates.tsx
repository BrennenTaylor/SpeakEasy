import { useEffect, useRef, useState } from "react";

import { createFood, type Food, type FoodCreate } from "../api/foods";
import { interpretMeal, type CandidateView } from "../api/interpretation";
import { MACRO_ROWS, type MacroStrings } from "../api/meals";

type Props = {
  rawInput: string;
  onAdd: (food: Food, quantity: string) => void;
  onComplete?: (candidate: CandidateView) => void;
};

type CompleteCandidate = CandidateView & MacroStrings;

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Something went wrong";
}

function isCompleteCandidate(candidate: CandidateView): candidate is CompleteCandidate {
  return !candidate.incomplete && MACRO_ROWS.every(({ key }) => typeof candidate[key] === "string");
}

function badgeFor(candidate: CandidateView): { label: string; low: boolean } {
  if (candidate.source === "usda_fdc") {
    return candidate.confidence === "high" && !candidate.incomplete
      ? { label: "USDA · high confidence", low: false }
      : { label: "USDA · low confidence", low: true };
  }
  return { label: "Web · low confidence", low: true };
}

function foodPayload(candidate: CompleteCandidate): FoodCreate {
  return {
    name: candidate.name,
    brand: candidate.brand,
    serving_label: candidate.serving_label,
    serving_grams: candidate.serving_grams,
    source: candidate.source,
    source_url: candidate.source_url,
    confidence: candidate.confidence,
    aliases: [],
    calories: candidate.calories,
    protein_g: candidate.protein_g,
    carbs_g: candidate.carbs_g,
    fat_g: candidate.fat_g,
    fiber_g: candidate.fiber_g,
    sugar_g: candidate.sugar_g,
    sodium_mg: candidate.sodium_mg,
  };
}

function CandidateCard({
  candidate,
  onAdd,
  onComplete,
}: {
  candidate: CandidateView;
  onAdd: (food: Food, quantity: string) => void;
  onComplete?: (candidate: CandidateView) => void;
}) {
  const [quantity, setQuantity] = useState(candidate.quantity);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const badge = badgeFor(candidate);

  async function handleAdd() {
    if (!isCompleteCandidate(candidate)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const saved = await createFood(foodPayload(candidate));
      onAdd(saved, quantity);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="w-full min-w-0 space-y-2 rounded-lg border border-gray-200 bg-white p-3">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="break-words text-sm font-medium text-gray-900">{candidate.name}</p>
          <p className="break-words text-xs text-gray-600">
            {candidate.brand && <span>{candidate.brand} · </span>}
            {candidate.serving_label}
          </p>
        </div>
        <span
          className={
            badge.low
              ? "shrink-0 rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-900"
              : "shrink-0 rounded bg-green-50 px-2 py-1 text-xs font-medium text-green-800"
          }
        >
          {badge.label}
        </span>
      </div>

      <dl className="grid w-full min-w-0 grid-cols-2 gap-x-3 gap-y-1">
        {MACRO_ROWS.map(({ key, label }) => (
          <div key={key} className="flex min-w-0 justify-between gap-2 text-xs">
            <dt className="text-gray-600">{label}</dt>
            <dd className="font-medium text-gray-900">{candidate[key] ?? "—"}</dd>
          </div>
        ))}
      </dl>

      {error && (
        <p role="alert" className="break-words text-xs text-red-800">
          {error}
        </p>
      )}

      {candidate.incomplete ? (
        <div className="space-y-2">
          <p className="text-xs text-amber-900">Missing: {candidate.missing_fields.join(", ")}</p>
          {onComplete && (
            <button
              type="button"
              onClick={() => onComplete(candidate)}
              className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Complete with a label
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs font-medium text-gray-700">
            Qty
            <input
              type="text"
              inputMode="decimal"
              value={quantity}
              aria-label={`Quantity for ${candidate.name}`}
              onChange={(event) => setQuantity(event.target.value)}
              className="ml-1 w-16 rounded border border-gray-300 px-1.5 py-1 text-sm"
            />
          </label>
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleAdd()}
            aria-label={`Add ${candidate.name}`}
            className="shrink-0 rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Add
          </button>
        </div>
      )}
    </li>
  );
}

export function MealCandidates({ rawInput, onAdd, onComplete }: Props) {
  const [candidates, setCandidates] = useState<CandidateView[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(
    () => () => {
      controllerRef.current?.abort();
      controllerRef.current = null;
    },
    [],
  );

  async function handleFind() {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setError(null);
    setCandidates([]);
    setWarnings([]);
    setSearched(false);
    setLoading(true);
    try {
      const result = await interpretMeal(rawInput.trim(), controller.signal);
      if (!controller.signal.aborted) {
        setCandidates(result.candidates);
        setWarnings(result.warnings);
        setSearched(true);
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        setError(errorMessage(cause));
        setSearched(false);
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }

  return (
    <section aria-labelledby="meal-candidates-heading" className="w-full min-w-0 space-y-3">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <h2 id="meal-candidates-heading" className="text-sm font-medium text-gray-700">
          Suggested foods
        </h2>
        <button
          type="button"
          disabled={rawInput.trim() === "" || loading}
          onClick={() => void handleFind()}
          className="shrink-0 rounded border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Find foods
        </button>
      </div>

      {loading && <p className="text-sm text-gray-600">Finding foods…</p>}
      {error && (
        <p
          role="alert"
          className="break-words rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900"
        >
          {error}
        </p>
      )}
      {warnings.map((warning) => (
        <p key={warning} className="break-words text-xs text-amber-900">
          {warning}
        </p>
      ))}
      {searched && candidates.length === 0 && !loading && (
        <p className="text-sm text-gray-600">
          No foods found. Add one with the form below or search for it manually.
        </p>
      )}

      {candidates.length > 0 && (
        <ul className="space-y-2">
          {candidates.map((candidate, index) => (
            <CandidateCard
              key={`${candidate.name}-${index}`}
              candidate={candidate}
              onAdd={onAdd}
              onComplete={onComplete}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
