import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Food } from "../api/foods";
import type { MacroStrings, Meal } from "../api/meals";
import { MealLogger } from "./MealLogger";

const food: Food = {
  id: 1,
  name: "Costco nuggets",
  brand: "Kirkland Signature",
  serving_label: "4 pieces",
  serving_grams: "88",
  source: "user_label",
  confidence: "high",
  aliases: ["those costco nuggets"],
  calories: "250.0000",
  protein_g: "14.0000",
  carbs_g: "16.0000",
  fat_g: "14.0000",
  fiber_g: "1.0000",
  sugar_g: "2.0000",
  sodium_mg: "400.0000",
  created_at: "2026-11-19T12:00:00",
};

const previewTotals: MacroStrings = {
  calories: "250.0000",
  protein_g: "14.0000",
  carbs_g: "16.0000",
  fat_g: "14.0000",
  fiber_g: "1.0000",
  sugar_g: "2.0000",
  sodium_mg: "400.0000",
};

const savedMeal: Meal = {
  id: 7,
  raw_input: "I ate two servings of nuggets",
  eaten_at: "2026-11-19T12:00:00+00:00",
  created_at: "2026-11-19T12:00:05+00:00",
  items: [
    {
      id: 11,
      food_id: food.id,
      quantity: "2",
      unit: "serving",
      serving_label: food.serving_label,
      serving_grams: food.serving_grams,
      source: food.source,
      confidence: food.confidence,
      created_at: food.created_at,
      ...previewTotals,
    },
  ],
  totals: {
    calories: "500.0000",
    protein_g: "28.0000",
    carbs_g: "32.0000",
    fat_g: "28.0000",
    fiber_g: "2.0000",
    sugar_g: "4.0000",
    sodium_mg: "800.0000",
  },
};

type StubOptions = {
  preview?: MacroStrings;
  previewStatus?: number;
  meals?: Meal[];
  confirmStatus?: number;
  confirmBody?: unknown;
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function stubFetch(options: StubOptions = {}) {
  let storedMeals = options.meals ?? [];
  const fetchMock = vi.fn((input: unknown, init?: RequestInit): Promise<Response> => {
    const url = String(input);
    if (url.startsWith("/api/health")) {
      return Promise.resolve(jsonResponse({ status: "ok" }));
    }
    if (url.startsWith("/api/foods")) {
      return Promise.resolve(jsonResponse([food]));
    }
    if (url.startsWith("/api/meals/preview")) {
      const status = options.previewStatus ?? 200;
      return Promise.resolve(
        jsonResponse(
          status >= 400 ? { detail: "preview failed" } : (options.preview ?? previewTotals),
          status,
        ),
      );
    }
    if (url.startsWith("/api/meals?")) {
      return Promise.resolve(jsonResponse(storedMeals));
    }
    if (url === "/api/meals" && init?.method === "POST") {
      const status = options.confirmStatus ?? 201;
      if (status >= 400) {
        return Promise.resolve(jsonResponse(options.confirmBody ?? { detail: "failed" }, status));
      }
      storedMeals = [savedMeal, ...storedMeals];
      return Promise.resolve(jsonResponse(savedMeal, status));
    }
    return Promise.resolve(jsonResponse({ detail: "not found" }, 404));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

type FetchStub = ReturnType<typeof stubFetch>;

function findCall(stub: FetchStub, url: string, method: string) {
  return stub.mock.calls.find(([input, init]) => String(input) === url && init?.method === method);
}

function lastPreviewPayload(stub: FetchStub) {
  const calls = stub.mock.calls.filter(
    ([input, init]) => String(input) === "/api/meals/preview" && init?.method === "POST",
  );
  const body = String(calls.at(-1)?.[1]?.body ?? "{}");
  return JSON.parse(body) as { raw_input?: unknown; items?: unknown };
}

function lastPreviewItems(stub: FetchStub) {
  return lastPreviewPayload(stub).items;
}

function elementAt<T>(elements: T[], index: number): T {
  const element = elements[index];
  if (!element) {
    throw new Error(`Expected an element at index ${index}`);
  }
  return element;
}

async function addNuggets(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByRole("textbox", { name: /search foods/i }), "nuggets");
  await user.click(screen.getByRole("button", { name: /^search$/i }));
  await user.click(await screen.findByRole("button", { name: /add costco nuggets/i }));
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("MealLogger", () => {
  it("lets the user type a sentence, add a food, preview, and confirm", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch();
    render(<MealLogger />);

    await user.type(
      screen.getByRole("textbox", { name: /describe your meal/i }),
      "two servings of nuggets",
    );
    await addNuggets(user);

    expect(await screen.findByText("250.0000")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /quantity for costco nuggets/i })).toHaveValue("1");

    const previewCall = findCall(fetchMock, "/api/meals/preview", "POST");
    expect(previewCall).toBeDefined();
    const previewPayload = JSON.parse(String(previewCall?.[1]?.body));
    expect(previewPayload.raw_input).toBe("two servings of nuggets");
    expect(previewPayload.items).toEqual([{ food_id: 1, quantity: "1", unit: "serving" }]);
    expect(typeof previewPayload.eaten_at).toBe("string");

    await user.click(screen.getByRole("button", { name: /^confirm$/i }));

    const createCall = findCall(fetchMock, "/api/meals", "POST");
    expect(createCall).toBeDefined();
    const createPayload = JSON.parse(String(createCall?.[1]?.body));
    expect(createPayload.raw_input).toBe("two servings of nuggets");
    expect(createPayload.items).toEqual([{ food_id: 1, quantity: "1", unit: "serving" }]);
    expect(typeof createPayload.eaten_at).toBe("string");

    await waitFor(() =>
      expect(
        screen.queryByRole("textbox", { name: /quantity for costco nuggets/i }),
      ).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("textbox", { name: /describe your meal/i })).toHaveValue("");
  });

  it("shows a backend error when confirm fails", async () => {
    const user = userEvent.setup();
    stubFetch({
      confirmStatus: 422,
      confirmBody: { detail: "Food not found" },
    });
    render(<MealLogger />);

    await user.type(
      screen.getByRole("textbox", { name: /describe your meal/i }),
      "two servings of nuggets",
    );
    await addNuggets(user);
    await user.click(screen.getByRole("button", { name: /^confirm$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/422/i);
    expect(screen.queryByText(savedMeal.raw_input)).not.toBeInTheDocument();
  });

  it("keeps Confirm disabled until a food is added", async () => {
    const user = userEvent.setup();
    stubFetch();
    render(<MealLogger />);

    const confirm = screen.getByRole("button", { name: /^confirm$/i });
    expect(confirm).toBeDisabled();

    await user.type(
      screen.getByRole("textbox", { name: /describe your meal/i }),
      "two servings of nuggets",
    );
    expect(confirm).toBeDisabled();

    await addNuggets(user);
    await waitFor(() => expect(confirm).toBeEnabled());
  });

  it("shows recent meals after a successful confirm", async () => {
    const user = userEvent.setup();
    stubFetch();
    render(<MealLogger />);

    expect(screen.getByText(/no meals logged yet/i)).toBeInTheDocument();

    await user.type(
      screen.getByRole("textbox", { name: /describe your meal/i }),
      "two servings of nuggets",
    );
    await addNuggets(user);
    await user.click(screen.getByRole("button", { name: /^confirm$/i }));

    expect(await screen.findByText(savedMeal.raw_input)).toBeInTheDocument();
    expect(screen.getByText(savedMeal.eaten_at)).toBeInTheDocument();
    expect(screen.getByText("500.0000")).toBeInTheDocument();
  });

  it("keeps two copies of the same food as independent rows", async () => {
    const user = userEvent.setup();
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const fetchMock = stubFetch();
    render(<MealLogger />);

    await user.type(
      screen.getByRole("textbox", { name: /describe your meal/i }),
      "two servings of nuggets",
    );
    await addNuggets(user);
    await user.click(screen.getByRole("button", { name: /add costco nuggets/i }));

    const quantities = screen.getAllByRole("textbox", { name: /quantity for costco nuggets/i });
    expect(quantities).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: /remove costco nuggets/i })).toHaveLength(2);

    await user.clear(elementAt(quantities, 0));
    await user.type(elementAt(quantities, 0), "2");

    expect(elementAt(quantities, 0)).toHaveValue("2");
    expect(elementAt(quantities, 1)).toHaveValue("1");
    await waitFor(() =>
      expect(lastPreviewItems(fetchMock)).toEqual([
        { food_id: 1, quantity: "2", unit: "serving" },
        { food_id: 1, quantity: "1", unit: "serving" },
      ]),
    );
    expect(errorSpy.mock.calls.flat().join(" ")).not.toMatch(/same key/i);
  });

  it("removing one copy of a food leaves the other row intact", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch();
    render(<MealLogger />);

    await user.type(
      screen.getByRole("textbox", { name: /describe your meal/i }),
      "two servings of nuggets",
    );
    await addNuggets(user);
    await user.click(screen.getByRole("button", { name: /add costco nuggets/i }));

    const quantities = screen.getAllByRole("textbox", { name: /quantity for costco nuggets/i });
    await user.clear(elementAt(quantities, 0));
    await user.type(elementAt(quantities, 0), "2");
    await user.click(
      elementAt(screen.getAllByRole("button", { name: /remove costco nuggets/i }), 0),
    );

    const remaining = screen.getAllByRole("textbox", { name: /quantity for costco nuggets/i });
    expect(remaining).toHaveLength(1);
    expect(elementAt(remaining, 0)).toHaveValue("1");
    await waitFor(() =>
      expect(lastPreviewItems(fetchMock)).toEqual([{ food_id: 1, quantity: "1", unit: "serving" }]),
    );
  });

  it("previews and enables Confirm when a description is typed after adding a food", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch();
    render(<MealLogger />);

    const confirm = screen.getByRole("button", { name: /^confirm$/i });
    expect(confirm).toBeDisabled();

    await addNuggets(user);
    expect(confirm).toBeDisabled();
    expect(findCall(fetchMock, "/api/meals/preview", "POST")).toBeUndefined();

    await user.type(
      screen.getByRole("textbox", { name: /describe your meal/i }),
      "two servings of nuggets",
    );

    await waitFor(() =>
      expect(lastPreviewPayload(fetchMock).raw_input).toBe("two servings of nuggets"),
    );
    expect(screen.getByText("250.0000")).toBeInTheDocument();
    await waitFor(() => expect(confirm).toBeEnabled());

    await user.click(confirm);
    expect(findCall(fetchMock, "/api/meals", "POST")).toBeDefined();
  });

  it("keeps Confirm disabled and does not save after the description is cleared", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch();
    render(<MealLogger />);

    const description = screen.getByRole("textbox", { name: /describe your meal/i });
    await user.type(description, "two servings of nuggets");
    await addNuggets(user);
    const confirm = screen.getByRole("button", { name: /^confirm$/i });
    await waitFor(() => expect(confirm).toBeEnabled());

    await user.clear(description);

    expect(confirm).toBeDisabled();
    expect(screen.queryByText("250.0000")).not.toBeInTheDocument();
    await user.click(confirm);
    expect(findCall(fetchMock, "/api/meals", "POST")).toBeUndefined();
  });

  it("clears totals and blocks Confirm when a preview fails", async () => {
    const user = userEvent.setup();
    const options: StubOptions = {};
    const fetchMock = stubFetch(options);
    render(<MealLogger />);

    await user.type(
      screen.getByRole("textbox", { name: /describe your meal/i }),
      "two servings of nuggets",
    );
    await addNuggets(user);
    await waitFor(() => expect(screen.getByText("250.0000")).toBeInTheDocument());
    const confirm = screen.getByRole("button", { name: /^confirm$/i });
    await waitFor(() => expect(confirm).toBeEnabled());

    options.previewStatus = 503;
    const quantity = screen.getByRole("textbox", { name: /quantity for costco nuggets/i });
    await user.clear(quantity);
    await user.type(quantity, "2");

    expect(await screen.findByRole("alert")).toHaveTextContent(/503/i);
    await waitFor(() => expect(screen.queryByText("250.0000")).not.toBeInTheDocument());
    expect(confirm).toBeDisabled();
    expect(findCall(fetchMock, "/api/meals", "POST")).toBeUndefined();
  });
});
