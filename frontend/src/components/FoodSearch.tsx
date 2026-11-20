import { useState, type FormEvent } from "react";

import { createFood, fetchFoods, type Food, type FoodCreate } from "../api/foods";

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Something went wrong";
}

function labelField(name: string, label: string, inputMode?: "decimal") {
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
        className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
      />
    </div>
  );
}

export function FoodSearch({ onAdd }: { onAdd: (food: Food) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Food[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

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
      source: "user_label",
      confidence: text("confidence") === "low" ? "low" : "high",
      aliases: text("aliases")
        .split(",")
        .map((alias) => alias.trim())
        .filter((alias) => alias.length > 0),
    };

    setBusy(true);
    try {
      const created = await createFood(payload);
      setShowCreate(false);
      onAdd(created);
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
              <button
                type="button"
                aria-label={`Add ${result.name}`}
                onClick={() => onAdd(result)}
                className="shrink-0 rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Add
              </button>
            </li>
          ))}
        </ul>
      )}

      {!showCreate ? (
        <button
          type="button"
          onClick={() => {
            setError(null);
            setShowCreate(true);
          }}
          className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Create a food from a label
        </button>
      ) : (
        <form
          onSubmit={handleCreate}
          className="w-full min-w-0 space-y-3 rounded-lg border border-gray-200 bg-white p-3"
        >
          <h3 className="text-sm font-medium text-gray-900">Create a food from a label</h3>
          {labelField("name", "Name")}
          {labelField("brand", "Brand")}
          {labelField("serving_label", "Serving label")}
          {labelField("serving_grams", "Serving grams", "decimal")}
          {labelField("calories", "Calories", "decimal")}
          {labelField("protein_g", "Protein (g)", "decimal")}
          {labelField("carbs_g", "Carbs (g)", "decimal")}
          {labelField("fat_g", "Fat (g)", "decimal")}
          {labelField("fiber_g", "Fiber (g)", "decimal")}
          {labelField("sugar_g", "Sugar (g)", "decimal")}
          {labelField("sodium_mg", "Sodium (mg)", "decimal")}
          <div className="space-y-1">
            <label htmlFor="food-confidence" className="block text-xs font-medium text-gray-700">
              Confidence
            </label>
            <select
              id="food-confidence"
              name="confidence"
              defaultValue="high"
              className="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
            >
              <option value="high">High</option>
              <option value="low">Low</option>
            </select>
          </div>
          {labelField("aliases", "Aliases (comma-separated)")}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="shrink-0 rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              Create food
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
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
