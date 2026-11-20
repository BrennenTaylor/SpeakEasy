import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Food } from "../api/foods";
import type { CandidateView } from "../api/interpretation";
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

const candidate: CandidateView = {
  name: "Chick-fil-A sandwich",
  brand: "Chick-fil-A",
  serving_label: "1 sandwich",
  serving_grams: "187.0000",
  quantity: "1.0000",
  source: "usda_fdc",
  source_url: "https://fdc.example/170790",
  confidence: "high",
  incomplete: false,
  missing_fields: [],
  calories: "465.6300",
  protein_g: "30.4000",
  carbs_g: "39.1000",
  fat_g: "20.9000",
  fiber_g: "2.6000",
  sugar_g: "0.0000",
  sodium_mg: "1407.0000",
};

const savedFood: Food = {
  id: 9,
  name: candidate.name,
  brand: candidate.brand,
  serving_label: candidate.serving_label,
  serving_grams: candidate.serving_grams,
  source: "usda_fdc",
  source_url: candidate.source_url,
  confidence: "high",
  aliases: [],
  calories: "465.6300",
  protein_g: "30.4000",
  carbs_g: "39.1000",
  fat_g: "20.9000",
  fiber_g: "2.6000",
  sugar_g: "0.0000",
  sodium_mg: "1407.0000",
  created_at: "2026-11-20T12:00:00",
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("MealCandidates", () => {
  it("shows a source badge and adds a complete candidate", async () => {
    const onAdd = vi.fn();
    mocks.interpretMeal.mockResolvedValue({ candidates: [candidate], warnings: [] });
    mocks.createFood.mockResolvedValue(savedFood);
    render(<MealCandidates rawInput="chick fil a sandwich" onAdd={onAdd} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    expect(await screen.findByText(candidate.name)).toBeInTheDocument();
    expect(screen.getByText(/usda · high confidence/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: `Add ${candidate.name}` }));

    await waitFor(() =>
      expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ source: "usda_fdc" }), "1.0000"),
    );
    expect(mocks.createFood).toHaveBeenCalledWith(
      expect.objectContaining({
        name: candidate.name,
        source: "usda_fdc",
        source_url: candidate.source_url,
        confidence: "high",
        calories: candidate.calories,
      }),
    );
  });

  it("uses the edited quantity", async () => {
    const onAdd = vi.fn();
    mocks.interpretMeal.mockResolvedValue({ candidates: [candidate], warnings: [] });
    mocks.createFood.mockResolvedValue(savedFood);
    render(<MealCandidates rawInput="sandwich" onAdd={onAdd} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    const quantity = await screen.findByRole("textbox", {
      name: `Quantity for ${candidate.name}`,
    });
    fireEvent.change(quantity, { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: `Add ${candidate.name}` }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledWith(savedFood, "2"));
  });

  it("shows a low-confidence badge for web candidates", async () => {
    mocks.interpretMeal.mockResolvedValue({
      candidates: [{ ...candidate, source: "web_search", confidence: "low" }],
      warnings: ["USDA lookup unavailable"],
    });
    render(<MealCandidates rawInput="rare food" onAdd={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

    expect(await screen.findByText(/web.*low confidence/i)).toBeInTheDocument();
    expect(screen.getByText("USDA lookup unavailable")).toBeInTheDocument();
  });

  it("shows low confidence for an incomplete USDA candidate", async () => {
    mocks.interpretMeal.mockResolvedValue({
      candidates: [
        {
          ...candidate,
          incomplete: true,
          missing_fields: ["sugar_g"],
          sugar_g: null,
          confidence: "low",
        },
      ],
      warnings: [],
    });
    render(<MealCandidates rawInput="sandwich" onAdd={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

    expect(await screen.findByText("USDA · low confidence")).toBeInTheDocument();
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
      resolveInterpret({ candidates: [], warnings: [] });
    });
    expect(await screen.findByText(/no foods found/i)).toBeInTheDocument();

    mocks.interpretMeal.mockRejectedValue(new Error("Server responded with 503"));
    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/503/i);
  });

  it("offers the create form for incomplete candidates but no Add button", async () => {
    const onComplete = vi.fn();
    mocks.interpretMeal.mockResolvedValue({
      candidates: [{ ...candidate, incomplete: true, missing_fields: ["sugar_g"], sugar_g: null }],
      warnings: [],
    });
    render(<MealCandidates rawInput="sandwich" onAdd={vi.fn()} onComplete={onComplete} />);

    fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

    expect(await screen.findByText(/missing: sugar_g/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: `Add ${candidate.name}` })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /complete with a label/i }));
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ incomplete: true }));
  });

  it("does not call the API on every keystroke", () => {
    const { rerender } = render(<MealCandidates rawInput="a" onAdd={vi.fn()} />);
    rerender(<MealCandidates rawInput="another description" onAdd={vi.fn()} />);

    expect(mocks.interpretMeal).not.toHaveBeenCalled();
  });
});
