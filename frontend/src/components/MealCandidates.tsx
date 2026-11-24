import { useEffect, useRef, useState } from "react";

import { createFood, type Food, type FoodCreate } from "../api/foods";
import { interpretMeal, type FoodMatchGroup, type MatchView } from "../api/interpretation";
import { MACRO_ROWS, type MacroStrings } from "../api/meals";

type Props = {
  rawInput: string;
  onAdd: (food: Food, quantity: string) => void;
  onComplete?: (match: MatchView) => void;
};

type CompleteMatch = Omit<MatchView, "serving_grams"> & MacroStrings & { serving_grams: string };

type Selection = { group: FoodMatchGroup; match: MatchView };

function selectionKey(groupId: string, matchId: string): string {
  // Match ids repeat across groups (each group has its own "web:0", and two
  // groups can offer the same FDC record), so saved-food tracking keys on the
  // group's selection, not the match alone.
  return `${groupId}:${matchId}`;
}

const INITIAL_VISIBLE_MATCHES = 3;

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Something went wrong";
}

function isCompleteMatch(match: MatchView): match is CompleteMatch {
  return (
    !match.incomplete &&
    typeof match.serving_grams === "string" &&
    MACRO_ROWS.every(({ key }) => typeof match[key] === "string")
  );
}

function badgeFor(match: MatchView): { label: string; low: boolean } {
  if (match.source === "usda_fdc") {
    return match.confidence === "high" && !match.incomplete
      ? { label: "USDA · high confidence", low: false }
      : { label: "USDA · low confidence", low: true };
  }
  return { label: "Web · low confidence", low: true };
}

function foodPayload(match: CompleteMatch): FoodCreate {
  return {
    name: match.name,
    brand: match.brand,
    serving_label: match.serving_label,
    serving_grams: match.serving_grams,
    source: match.source,
    source_url: match.source_url,
    confidence: match.confidence,
    aliases: [],
    calories: match.calories,
    protein_g: match.protein_g,
    carbs_g: match.carbs_g,
    fat_g: match.fat_g,
    fiber_g: match.fiber_g,
    sugar_g: match.sugar_g,
    sodium_mg: match.sodium_mg,
  };
}

function MatchCard({
  group,
  match,
  selected,
  onSelect,
  onComplete,
}: {
  group: FoodMatchGroup;
  match: MatchView;
  selected: boolean;
  onSelect: (matchId: string) => void;
  onComplete?: (match: MatchView) => void;
}) {
  const badge = badgeFor(match);

  return (
    <li className="w-full min-w-0 space-y-2 rounded-lg border border-gray-200 bg-white p-3">
      <label className="flex min-w-0 cursor-pointer items-start gap-2">
        <input
          type="radio"
          name={`match-group-${group.group_id}`}
          checked={selected}
          onChange={() => onSelect(match.match_id)}
          aria-label={`${badge.label}: ${match.name}`}
          className="mt-1 shrink-0"
        />
        <span className="min-w-0 flex-1">
          <span className="block break-words text-sm font-medium text-gray-900">{match.name}</span>
          <span className="block break-words text-xs text-gray-600">
            {match.brand && <span>{match.brand} · </span>}
            {match.serving_label}
            {match.serving_grams !== null && ` (${match.serving_grams} g)`}
          </span>
        </span>
        <span
          className={
            badge.low
              ? "shrink-0 rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-900"
              : "shrink-0 rounded bg-green-50 px-2 py-1 text-xs font-medium text-green-800"
          }
        >
          {badge.label}
        </span>
      </label>

      <dl className="grid w-full min-w-0 grid-cols-2 gap-x-3 gap-y-1">
        {MACRO_ROWS.map(({ key, label }) => (
          <div key={key} className="flex min-w-0 justify-between gap-2 text-xs">
            <dt className="text-gray-600">{label}</dt>
            <dd className="font-medium text-gray-900">{match[key] ?? "—"}</dd>
          </div>
        ))}
      </dl>

      {match.rank_reasons.length > 0 && (
        <p className="break-words text-xs text-gray-600">
          Rank {match.rank}: {match.rank_reasons.join(" · ")}
        </p>
      )}

      {match.source_url && (
        <a
          href={match.source_url}
          target="_blank"
          rel="noreferrer"
          className="text-xs font-medium text-blue-700 underline"
        >
          View source
        </a>
      )}

      {match.incomplete && (
        <div className="space-y-2">
          <p className="text-xs text-amber-900">Missing: {match.missing_fields.join(", ")}</p>
          {selected && onComplete && (
            <button
              type="button"
              onClick={() => onComplete(match)}
              className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Complete with a label
            </button>
          )}
        </div>
      )}
    </li>
  );
}

export function MealCandidates({ rawInput, onAdd, onComplete }: Props) {
  const [groups, setGroups] = useState<FoodMatchGroup[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  // Matches whose Food already exists in the library. A retry after a partial
  // failure skips them so the same food is never created twice.
  const [createdKeys, setCreatedKeys] = useState<ReadonlySet<string>>(new Set());
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(
    () => () => {
      controllerRef.current?.abort();
      controllerRef.current = null;
    },
    [],
  );

  function selections(): Selection[] {
    const entries: Selection[] = [];
    for (const group of groups) {
      const match = group.matches.find((item) => item.match_id === selected[group.group_id]);
      if (match) {
        entries.push({ group, match });
      }
    }
    return entries;
  }

  function clearPicker() {
    setGroups([]);
    setWarnings([]);
    setSelected({});
    setExpandedGroups({});
    setSearched(false);
    setCreatedKeys(new Set());
    setAddError(null);
  }

  async function handleFind() {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setError(null);
    setAddError(null);
    setGroups([]);
    setWarnings([]);
    setSelected({});
    setExpandedGroups({});
    setSearched(false);
    // Group ids and match ids repeat between searches, so a new search must
    // not inherit the previous one's created-food tracking.
    setCreatedKeys(new Set());
    setLoading(true);
    try {
      const result = await interpretMeal(rawInput.trim(), controller.signal);
      if (!controller.signal.aborted) {
        // Display in rank order; the backend already ranks matches, this keeps
        // the picker correct even if a payload arrives out of order.
        const ordered = result.groups.map((group) => ({
          ...group,
          matches: [...group.matches].sort((a, b) => a.rank - b.rank),
        }));
        setGroups(ordered);
        setWarnings(result.warnings);
        setSelected(
          Object.fromEntries(
            ordered.map((group) => [group.group_id, group.matches[0]?.match_id ?? ""]),
          ),
        );
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

  async function handleAddSelected() {
    // Never save a partial meal: every selected match must be complete.
    const complete: { group: FoodMatchGroup; match: CompleteMatch }[] = [];
    for (const { group, match } of selections()) {
      if (!isCompleteMatch(match)) {
        return;
      }
      complete.push({ group, match });
    }
    if (complete.length === 0) {
      return;
    }
    // A retry after a partial failure must not re-create foods that were
    // already saved to the library.
    const pending = complete.filter(
      ({ group, match }) => !createdKeys.has(selectionKey(group.group_id, match.match_id)),
    );
    if (pending.length === 0) {
      clearPicker();
      return;
    }
    setAdding(true);
    setAddError(null);
    try {
      const results = await Promise.allSettled(
        pending.map(({ match }) => createFood(foodPayload(match))),
      );
      const created = new Set(createdKeys);
      const added: { food: Food; quantity: string }[] = [];
      const failed: { match: CompleteMatch; message: string }[] = [];
      pending.forEach(({ group, match }, index) => {
        const result = results[index];
        if (result?.status === "fulfilled") {
          created.add(selectionKey(group.group_id, match.match_id));
          added.push({ food: result.value, quantity: group.quantity });
        } else {
          // allSettled keeps result and pending indexes aligned; a missing
          // slot would mean the food was never attempted, so it stays a
          // failure the next retry can pick up.
          failed.push({
            match,
            message: result ? errorMessage(result.reason) : "Add never ran",
          });
        }
      });
      // Record created foods before any parent side effects so a retry can
      // never re-create them.
      setCreatedKeys(created);
      added.forEach(({ food, quantity }) => onAdd(food, quantity));
      if (failed.length > 0) {
        // Keep the picker so the failed foods can be retried; the next attempt
        // skips the matches that already saved successfully.
        const failures = failed.map(({ match, message }) => `${match.name}: ${message}`);
        setAddError(
          `Could not add ${failures.join("; ")}. Retry adds only the failed foods; already added foods are kept.`,
        );
      } else {
        // Nothing remains to retry: clear the picker so a second Add can never
        // re-create the same foods.
        clearPicker();
      }
    } catch (cause) {
      setAddError(errorMessage(cause));
    } finally {
      setAdding(false);
    }
  }

  const entries = selections();
  const allSelectedComplete =
    entries.length > 0 && entries.every(({ match }) => isCompleteMatch(match));

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
      {searched && groups.length === 0 && !loading && (
        <p className="text-sm text-gray-600">
          No foods found. Add one with the form below or search for it manually.
        </p>
      )}

      {groups.map((group) => {
        const expanded = expandedGroups[group.group_id] ?? false;
        const visible = expanded ? group.matches : group.matches.slice(0, INITIAL_VISIBLE_MATCHES);
        const hiddenCount = group.matches.length - visible.length;
        return (
          <div key={group.group_id} className="w-full min-w-0 space-y-2">
            <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
              <h3 className="break-words text-sm font-medium text-gray-900">{group.label}</h3>
              <span className="shrink-0 text-xs text-gray-600">Qty {group.quantity}</span>
            </div>
            <ul className="space-y-2">
              {visible.map((match) => (
                <MatchCard
                  key={match.match_id}
                  group={group}
                  match={match}
                  selected={selected[group.group_id] === match.match_id}
                  onSelect={(matchId) =>
                    setSelected((previous) => ({ ...previous, [group.group_id]: matchId }))
                  }
                  onComplete={onComplete}
                />
              ))}
            </ul>
            {hiddenCount > 0 && (
              <button
                type="button"
                onClick={() =>
                  setExpandedGroups((previous) => ({ ...previous, [group.group_id]: true }))
                }
                className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Show more ({hiddenCount})
              </button>
            )}
          </div>
        );
      })}

      {addError && (
        <p role="alert" className="break-words text-xs text-red-800">
          {addError}
        </p>
      )}

      {allSelectedComplete && (
        <button
          type="button"
          disabled={adding}
          onClick={() => void handleAddSelected()}
          className="w-full rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Add selected foods
        </button>
      )}
    </section>
  );
}
