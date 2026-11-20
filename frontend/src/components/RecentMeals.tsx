import type { MacroStrings, Meal } from "../api/meals";

const MACRO_ROWS: { key: keyof MacroStrings; label: string }[] = [
  { key: "calories", label: "Calories" },
  { key: "protein_g", label: "Protein (g)" },
  { key: "carbs_g", label: "Carbs (g)" },
  { key: "fat_g", label: "Fat (g)" },
  { key: "fiber_g", label: "Fiber (g)" },
  { key: "sugar_g", label: "Sugar (g)" },
  { key: "sodium_mg", label: "Sodium (mg)" },
];

export function RecentMeals({ meals }: { meals: Meal[] }) {
  return (
    <section aria-labelledby="recent-meals-heading" className="w-full min-w-0 space-y-3">
      <h3 id="recent-meals-heading" className="text-sm font-medium text-gray-700">
        Recent meals
      </h3>

      {meals.length === 0 ? (
        <p className="text-sm text-gray-600">No meals logged yet.</p>
      ) : (
        <ul className="space-y-2">
          {meals.map((meal) => (
            <li
              key={meal.id}
              className="w-full min-w-0 space-y-2 rounded-lg border border-gray-200 bg-white p-3"
            >
              <p className="text-sm font-medium text-gray-900 break-words">{meal.raw_input}</p>
              <time dateTime={meal.eaten_at} className="block text-xs text-gray-600 break-all">
                {meal.eaten_at}
              </time>
              <dl className="grid w-full min-w-0 grid-cols-2 gap-x-3 gap-y-0.5">
                {MACRO_ROWS.map(({ key, label }) => (
                  <div key={key} className="flex min-w-0 justify-between gap-2 text-xs">
                    <dt className="text-gray-600">{label}</dt>
                    <dd className="font-medium text-gray-900">{meal.totals[key]}</dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
