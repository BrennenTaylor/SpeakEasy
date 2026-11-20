import type { Food } from "../api/foods";
import type { MacroStrings } from "../api/meals";

export type ReviewItem = { food: Food; quantity: string };

type Props = {
  items: ReviewItem[];
  totals: MacroStrings | null;
  submitting: boolean;
  onQuantityChange: (foodId: number, quantity: string) => void;
  onRemove: (foodId: number) => void;
  onConfirm: () => void;
};

const MACRO_ROWS: { key: keyof MacroStrings; label: string }[] = [
  { key: "calories", label: "Calories" },
  { key: "protein_g", label: "Protein (g)" },
  { key: "carbs_g", label: "Carbs (g)" },
  { key: "fat_g", label: "Fat (g)" },
  { key: "fiber_g", label: "Fiber (g)" },
  { key: "sugar_g", label: "Sugar (g)" },
  { key: "sodium_mg", label: "Sodium (mg)" },
];

export function MealReview({
  items,
  totals,
  submitting,
  onQuantityChange,
  onRemove,
  onConfirm,
}: Props) {
  return (
    <section aria-labelledby="meal-review-heading" className="w-full min-w-0 space-y-3">
      <h3 id="meal-review-heading" className="text-sm font-medium text-gray-700">
        Meal review
      </h3>

      {items.length === 0 ? (
        <p className="text-sm text-gray-600">Add a food to review this meal.</p>
      ) : (
        <ul className="space-y-2">
          {items.map(({ food, quantity }) => (
            <li
              key={food.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-gray-200 bg-white p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-gray-900">{food.name}</p>
                <p className="truncate text-xs text-gray-600">
                  <span>{food.serving_label}</span>
                  <span aria-hidden="true"> · </span>
                  <span>{food.calories} kcal</span>
                </p>
              </div>
              <label className="shrink-0 text-xs font-medium text-gray-700">
                Qty
                <input
                  type="text"
                  inputMode="decimal"
                  value={quantity}
                  aria-label={`Quantity for ${food.name}`}
                  onChange={(event) => onQuantityChange(food.id, event.target.value)}
                  className="ml-1 w-12 rounded border border-gray-300 px-1.5 py-1 text-sm"
                />
              </label>
              <button
                type="button"
                aria-label={`Remove ${food.name}`}
                onClick={() => onRemove(food.id)}
                className="shrink-0 rounded border border-gray-300 bg-white px-2 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {totals ? (
        <dl className="grid w-full min-w-0 grid-cols-2 gap-x-3 gap-y-1 rounded-lg border border-gray-200 bg-white p-3">
          {MACRO_ROWS.map(({ key, label }) => (
            <div key={key} className="flex min-w-0 justify-between gap-2 text-xs">
              <dt className="text-gray-600">{label}</dt>
              <dd className="font-medium text-gray-900">{totals[key]}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="text-sm text-gray-600">Totals appear after adding a food.</p>
      )}

      <button
        type="button"
        onClick={onConfirm}
        disabled={submitting || items.length === 0}
        className="w-full rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        Confirm
      </button>
    </section>
  );
}
