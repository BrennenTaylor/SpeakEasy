import { HealthCheck } from "./components/HealthCheck";
import { MealLogger } from "./components/MealLogger";

export default function App() {
  return (
    <main className="mx-auto min-h-dvh max-w-md px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Calorie Tracker</h1>
        <p className="mt-1 text-sm text-gray-600">Log a meal in plain language.</p>
      </header>
      <section aria-labelledby="status-heading">
        <h2 id="status-heading" className="mb-2 text-sm font-medium text-gray-700">
          Server status
        </h2>
        <HealthCheck />
      </section>
      <section aria-labelledby="logger-heading" className="mt-6">
        <h2 id="logger-heading" className="mb-2 text-sm font-medium text-gray-700">
          What did you eat?
        </h2>
        <MealLogger />
      </section>
    </main>
  );
}
