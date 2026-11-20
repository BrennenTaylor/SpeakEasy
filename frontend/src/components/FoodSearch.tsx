import { useState, type FormEvent } from "react";

import { createFood, fetchFoods, updateFood, type Food, type FoodCreate } from "../api/foods";

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Something went wrong";
}

function labelField(name: string, label: string, inputMode?: "decimal", defaultValue?: string) {
  return (
    <div className="space-y-1">
      <label htmlFor={`food-${name}`} className="block text-xs font-medium text-gray-700">
        {label}
      </label>
      <input
        id={`food-${name}`}
        name={name}
        type="text"
        inputMode={inputMode}
        defaultValue={defaultValue}
        className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
      />
    </div>
  );
}

export type FoodPrefill = Omit<FoodCreate, "source" | "confidence"> & {
  source?: FoodCreate["source"];
  confidence?: FoodCreate["confidence"];
};

type Props = {
  onAdd: (food: Food) => void;
  prefill?: FoodPrefill | null;
  onPrefillUsed?: () => void;
};

export function FoodSearch({ onAdd, prefill, onPrefillUsed }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Food[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [editingFood, setEditingFood] = useState<Food | null>(null);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      setResults(await fetchFoods(query));
      setHasSearched(true);
    } catch (cause) {
      setResults([]);
      setHasSearched(false);
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  function openCreateForm() {
    setError(null);
    setEditingFood(null);
    setShowCreate(true);
  }

  function openEditForm(foodToEdit: Food) {
    setError(null);
    setEditingFood(foodToEdit);
    onPrefillUsed?.();
    setShowCreate(true);
  }

  function closeForm() {
    setEditingFood(null);
    setShowCreate(false);
    onPrefillUsed?.();
  }

  const initial = editingFood ?? prefill;
  const formVisible = showCreate || Boolean(prefill);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const values = new FormData(event.currentTarget);
    const text = (name: string) => String(values.get(name) ?? "");
    const payload: FoodCreate = {
      name: text("name"),
      brand: text("brand"),
      serving_label: text("serving_label"),
      serving_grams: text("serving_grams"),
      calories: text("calories"),
      protein_g: text("protein_g"),
      carbs_g: text("carbs_g"),
      fat_g: text("fat_g"),
      fiber_g: text("fiber_g"),
      sugar_g: text("sugar_g"),
      sodium_mg: text("sodium_mg"),
      source: editingFood?.source ?? "user_label",
      source_url: text("source_url") || null,
      confidence: text("confidence") === "low" ? "low" : "high",
      aliases: text("aliases")
        .split(",")
        .map((alias) => alias.trim())
        .filter((alias) => alias.length > 0),
    };

    setBusy(true);
    try {
      const saved = editingFood
        ? await updateFood(editingFood.id, payload)
        : await createFood(payload);
      closeForm();
      onAdd(saved);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="food-search-heading" className="w-full min-w-0 space-y-4">
      <h2 id="food-search-heading" className="text-sm font-medium text-gray-700">
        Find a food
      </h2>

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm break-words text-red-900"
        >
          {error}
        </p>
      )}

      <form onSubmit={handleSearch} className="space-y-2">
        <label htmlFor="food-search-query" className="block text-sm font-medium text-gray-700">
          Search foods
        </label>
        <div className="flex gap-2">
          <input
            id="food-search-query"
            name="query"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="e.g. nuggets"
            className="min-w-0 flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={busy}
            className="shrink-0 rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            Search
          </button>
        </div>
      </form>

      {busy && <p className="text-sm text-gray-600">Working…</p>}

      {hasSearched && results.length === 0 && !error && (
        <p className="text-sm text-gray-600">No foods found.</p>
      )}

      {results.length > 0 && (
        <ul className="space-y-2">
          {results.map((result) => (
            <li
              key={result.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-gray-200 bg-white p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-gray-900">{result.name}</p>
                <p className="truncate text-xs text-gray-600">
                  <span>{result.brand}</span>
                  <span aria-hidden="true"> · </span>
                  <span>{result.serving_label}</span>
                </p>
                <p className="text-xs text-gray-600">{result.calories} kcal</p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  aria-label={`Add ${result.name}`}
                  onClick={() => onAdd(result)}
                  className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Add
                </button>
                <button
                  type="button"
                  aria-label={`Edit ${result.name}`}
                  onClick={() => openEditForm(result)}
                  className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Edit
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {!formVisible ? (
        <button
          type="button"
          onClick={openCreateForm}
          className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Create a food from a label
        </button>
      ) : (
        <form
          key={editingFood?.id ?? JSON.stringify(prefill) ?? "new"}
          onSubmit={handleCreate}
          className="w-full min-w-0 space-y-3 rounded-lg border border-gray-200 bg-white p-3"
        >
          <h3 className="text-sm font-medium text-gray-900">
            {editingFood ? "Edit saved food" : "Create a food from a label"}
          </h3>
          {labelField("name", "Name", undefined, initial?.name)}
          {labelField("brand", "Brand", undefined, initial?.brand)}
          {labelField("serving_label", "Serving label", undefined, initial?.serving_label)}
          {labelField("serving_grams", "Serving grams", "decimal", initial?.serving_grams)}
          {labelField("calories", "Calories", "decimal", initial?.calories)}
          {labelField("protein_g", "Protein (g)", "decimal", initial?.protein_g)}
          {labelField("carbs_g", "Carbs (g)", "decimal", initial?.carbs_g)}
          {labelField("fat_g", "Fat (g)", "decimal", initial?.fat_g)}
          {labelField("fiber_g", "Fiber (g)", "decimal", initial?.fiber_g)}
          {labelField("sugar_g", "Sugar (g)", "decimal", initial?.sugar_g)}
          {labelField("sodium_mg", "Sodium (mg)", "decimal", initial?.sodium_mg)}
          <div className="space-y-1">
            <label htmlFor="food-confidence" className="block text-xs font-medium text-gray-700">
              Confidence
            </label>
            <select
              id="food-confidence"
              name="confidence"
              defaultValue={initial?.confidence ?? "high"}
              className="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
            >
              <option value="high">High</option>
              <option value="low">Low</option>
            </select>
          </div>
          {labelField(
            "aliases",
            "Aliases (comma-separated)",
            undefined,
            initial?.aliases?.join(", "),
          )}
          <input type="hidden" name="source_url" defaultValue={initial?.source_url ?? ""} />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="shrink-0 rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {editingFood ? "Save food" : "Create food"}
            </button>
            <button
              type="button"
              onClick={closeForm}
              className="shrink-0 rounded border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
