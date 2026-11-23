import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Food } from "../api/foods";
import type { MatchView } from "../api/interpretation";
import { MealCandidates } from "./MealCandidates";

const mocks = vi.hoisted(() => ({
  interpretMeal: vi.fn(),
  createFood: vi.fn(),
}));

vi.mock("../api/interpretation", () => ({ interpretMeal: mocks.interpretMeal }));
vi.mock("../api/foods", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/foods")>();
  return { ...actual, createFood: mocks.createFood };
});

const webMatch: MatchView = {
  name: "Chick-fil-A Nuggets",
  brand: "Chick-fil-A",
  serving_label: "12 pieces",
  serving_grams: "170.0000",
  quantity: "1.0000",
  source: "web_search",
  source_url: "https://www.chick-fil-a.com/menu/nuggets",
  confidence: "low",
  incomplete: false,
  missing_fields: [],
  calories: "390.0000",
  protein_g: "36.0000",
  carbs_g: "14.0000",
  fat_g: "21.0000",
  fiber_g: "1.0000",
  sugar_g: "1.0000",
  sodium_mg: "1210.0000",
  match_id: "web:0",
  source_key: null,
  rank: 1,
  rank_reasons: ["name match", "complete macros", "web source"],
};

const stripsMatch: MatchView = {
  name: "CHICK-FIL-A, Chick-n-Strips",
  brand: "CHICK-FIL-A",
  serving_label: "2 strips",
  serving_grams: "113.0000",
  quantity: "1.0000",
  source: "usda_fdc",
  source_url: "https://fdc.nal.usda.gov/food-details/170790/nutrients",
  confidence: "high",
  incomplete: false,
  missing_fields: [],
  calories: "271.2000",
  protein_g: "28.5000",
  carbs_g: "12.4000",
  fat_g: "12.1000",
  fiber_g: "0.9000",
  sugar_g: "0.6000",
  sodium_mg: "820.0000",
  match_id: "usda:170790",
  source_key: "170790",
  rank: 2,
  rank_reasons: ["brand match", "complete macros", "USDA source"],
};

const webFood: Food = {
  id: 21,
  name: webMatch.name,
  brand: webMatch.brand,
  serving_label: webMatch.serving_label,
  serving_grams: webMatch.serving_grams,
  source: "web_search",
  source_url: webMatch.source_url,
  confidence: "low",
  aliases: [],
  calories: "390.0000",
  protein_g: "36.0000",
  carbs_g: "14.0000",
  fat_g: "21.0000",
  fiber_g: "1.0000",
  sugar_g: "1.0000",
  sodium_mg: "1210.0000",
  created_at: "2026-11-22T12:00:00",
};

const stripsFood: Food = {
  id: 22,
  name: stripsMatch.name,
  brand: stripsMatch.brand,
  serving_label: stripsMatch.serving_label,
  serving_grams: stripsMatch.serving_grams,
  source: "usda_fdc",
  source_url: stripsMatch.source_url,
  confidence: "high",
  aliases: [],
  calories: "271.2000",
  protein_g: "28.5000",
  carbs_g: "12.4000",
  fat_g: "12.1000",
  fiber_g: "0.9000",
  sugar_g: "0.6000",
  sodium_mg: "820.0000",
  created_at: "2026-11-22T12:00:00",
};

function usdaMatch(rank: number, name: string): MatchView {
  return {
    ...stripsMatch,
    name,
    match_id: `usda:${100 + rank}`,
    source_key: String(100 + rank),
    rank,
  };
}

const m1 = usdaMatch(1, "Nuggets, breaded, restaurant");
const m2 = usdaMatch(2, "Chicken nuggets, frozen");
// Array order deliberately differs from rank order: the picker displays by
// rank, so m3 (rank 4) stays hidden until "Show more" reveals it.
const m3 = usdaMatch(4, "Nuggets, plant-based");
const m4 = usdaMatch(3, "Chicken bites, breaded");

afterEach(() => {
  vi.clearAllMocks();
});

describe("MealCandidates", () => {
  it("shows ranked matches and adds only the selected one", async () => {
    const onAdd = vi.fn();
    mocks.interpretMeal.mockResolvedValue({
      groups: [
        {
          group_id: "0",
          label: "12 ct Chick-fil-A Nuggets",
          quantity: "1.0000",
          matches: [webMatch, stripsMatch],
        },
      ],
      warnings: [],
    });
    mocks.createFood.mockResolvedValue(stripsFood);
    render(<MealCandidates rawInput="nuggets" onAdd={onAdd} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    fireEvent.click(await screen.findByRole("radio", { name: /usda.*Chick-n-Strips/i }));
    fireEvent.click(screen.getByRole("button", { name: /add selected foods/i }));

    await waitFor(() =>
      expect(mocks.createFood).toHaveBeenCalledWith(
        expect.objectContaining({ name: "CHICK-FIL-A, Chick-n-Strips" }),
      ),
    );
    expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ id: stripsFood.id }), "1.0000");
    expect(mocks.createFood).not.toHaveBeenCalledWith(
      expect.objectContaining({ name: webMatch.name }),
    );
  });

  it("reveals remaining matches with Show more", async () => {
    mocks.interpretMeal.mockResolvedValue({
      groups: [{ group_id: "0", label: "Nuggets", quantity: "1", matches: [m1, m2, m3, m4] }],
      warnings: [],
    });
    render(<MealCandidates rawInput="nuggets" onAdd={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

    await screen.findByText(m1.name);
    expect(screen.queryByText(m3.name)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /show more/i }));
    expect(await screen.findByText(m3.name)).toBeInTheDocument();
  });

  it("incomplete selection opens prefill without creating food", async () => {
    const onComplete = vi.fn();
    mocks.interpretMeal.mockResolvedValue({
      groups: [
        {
          group_id: "0",
          label: "Nuggets",
          quantity: "1",
          matches: [
            { ...webMatch, incomplete: true, missing_fields: ["source_url"], source_url: null },
          ],
        },
      ],
      warnings: ["Web result has no valid source_url"],
    });
    render(<MealCandidates rawInput="nuggets" onAdd={vi.fn()} onComplete={onComplete} />);
    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

    expect(await screen.findByText(/missing: source_url/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add selected foods/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /complete with a label/i }));
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({ match_id: "web:0", source_url: null }),
    );
    expect(mocks.createFood).not.toHaveBeenCalled();
  });

  it("shows a source badge and adds the default complete selection", async () => {
    const onAdd = vi.fn();
    mocks.interpretMeal.mockResolvedValue({
      groups: [
        { group_id: "0", label: "Chick-n-Strips", quantity: "1.0000", matches: [stripsMatch] },
      ],
      warnings: [],
    });
    mocks.createFood.mockResolvedValue(stripsFood);
    render(<MealCandidates rawInput="chick fil a strips" onAdd={onAdd} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    expect(await screen.findByText(stripsMatch.name)).toBeInTheDocument();
    expect(screen.getByText(/usda · high confidence/i)).toBeInTheDocument();
    expect(screen.getByText(/brand match.*complete macros/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view source/i })).toHaveAttribute(
      "href",
      stripsMatch.source_url,
    );

    fireEvent.click(screen.getByRole("button", { name: /add selected foods/i }));

    await waitFor(() =>
      expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ id: stripsFood.id }), "1.0000"),
    );
    expect(mocks.createFood).toHaveBeenCalledWith(
      expect.objectContaining({
        name: stripsMatch.name,
        source: "usda_fdc",
        source_url: stripsMatch.source_url,
        confidence: "high",
        calories: stripsMatch.calories,
      }),
    );
  });

  it("uses the group quantity when adding", async () => {
    const onAdd = vi.fn();
    mocks.interpretMeal.mockResolvedValue({
      groups: [{ group_id: "0", label: "Strips", quantity: "2.0000", matches: [stripsMatch] }],
      warnings: [],
    });
    mocks.createFood.mockResolvedValue(stripsFood);
    render(<MealCandidates rawInput="two strips" onAdd={onAdd} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    fireEvent.click(await screen.findByRole("button", { name: /add selected foods/i }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledWith(stripsFood, "2.0000"));
  });

  it("adds the default selection of every group", async () => {
    const onAdd = vi.fn();
    mocks.interpretMeal.mockResolvedValue({
      groups: [
        { group_id: "0", label: "Nuggets", quantity: "1.0000", matches: [webMatch, stripsMatch] },
        { group_id: "1", label: "Strips", quantity: "2.0000", matches: [stripsMatch] },
      ],
      warnings: [],
    });
    mocks.createFood.mockImplementation(async (payload: { name: string }) =>
      payload.name === webMatch.name ? webFood : stripsFood,
    );
    render(<MealCandidates rawInput="nuggets and strips" onAdd={onAdd} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    fireEvent.click(await screen.findByRole("button", { name: /add selected foods/i }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledTimes(2));
    expect(onAdd).toHaveBeenCalledWith(webFood, "1.0000");
    expect(onAdd).toHaveBeenCalledWith(stripsFood, "2.0000");
  });

  it("hides Add selected foods until every selected match is complete", async () => {
    const incompleteWeb = {
      ...webMatch,
      incomplete: true,
      missing_fields: ["source_url"],
      source_url: null,
    };
    const completeWeb = {
      ...webMatch,
      name: "Chick-fil-A Nuggets, 12 ct",
      match_id: "web:1",
      rank: 2,
    };
    mocks.interpretMeal.mockResolvedValue({
      groups: [
        { group_id: "0", label: "Strips", quantity: "1", matches: [stripsMatch] },
        { group_id: "1", label: "Nuggets", quantity: "1", matches: [incompleteWeb, completeWeb] },
      ],
      warnings: [],
    });
    render(<MealCandidates rawInput="nuggets and strips" onAdd={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

    expect(await screen.findByText(stripsMatch.name)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add selected foods/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: /web.*nuggets, 12 ct/i }));
    expect(screen.getByRole("button", { name: /add selected foods/i })).toBeInTheDocument();
  });

  it("shows a low-confidence badge for web matches", async () => {
    mocks.interpretMeal.mockResolvedValue({
      groups: [{ group_id: "0", label: "Nuggets", quantity: "1", matches: [webMatch] }],
      warnings: ["USDA lookup unavailable"],
    });
    render(<MealCandidates rawInput="rare food" onAdd={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

    expect(await screen.findByText(/web.*low confidence/i)).toBeInTheDocument();
    expect(screen.getByText("USDA lookup unavailable")).toBeInTheDocument();
  });

  it("shows low confidence for an incomplete USDA match", async () => {
    mocks.interpretMeal.mockResolvedValue({
      groups: [
        {
          group_id: "0",
          label: "Strips",
          quantity: "1",
          matches: [
            {
              ...stripsMatch,
              incomplete: true,
              missing_fields: ["sugar_g"],
              sugar_g: null,
              confidence: "low",
            },
          ],
        },
      ],
      warnings: [],
    });
    render(<MealCandidates rawInput="strips" onAdd={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

    expect(await screen.findByText("USDA · low confidence")).toBeInTheDocument();
    expect(screen.getByText(/missing: sugar_g/i)).toBeInTheDocument();
  });

  it("shows loading, empty, and error states", async () => {
    let resolveInterpret: (value: unknown) => void = () => {};
    mocks.interpretMeal.mockReturnValue(
      new Promise((resolve) => {
        resolveInterpret = resolve;
      }),
    );
    render(<MealCandidates rawInput="lunch" onAdd={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    expect(screen.getByText(/finding foods/i)).toBeInTheDocument();

    await act(async () => {
      resolveInterpret({ groups: [], warnings: [] });
    });
    expect(await screen.findByText(/no foods found/i)).toBeInTheDocument();

    mocks.interpretMeal.mockRejectedValue(new Error("Server responded with 503"));
    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/503/i);
  });

  it("does not call the API on every keystroke", () => {
    const { rerender } = render(<MealCandidates rawInput="a" onAdd={vi.fn()} />);
    rerender(<MealCandidates rawInput="another description" onAdd={vi.fn()} />);

    expect(mocks.interpretMeal).not.toHaveBeenCalled();
  });
});
