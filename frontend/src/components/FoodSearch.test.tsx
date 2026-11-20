import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FoodSearch } from "./FoodSearch";

const food = {
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

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("FoodSearch", () => {
  it("lists matching foods and calls onAdd", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([food]));
    vi.stubGlobal("fetch", fetchMock);
    const onAdd = vi.fn();

    render(<FoodSearch onAdd={onAdd} />);

    await user.type(screen.getByRole("textbox", { name: /search foods/i }), "nuggets");
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    expect(await screen.findByText("Costco nuggets")).toBeInTheDocument();
    expect(screen.getByText("Kirkland Signature")).toBeInTheDocument();
    expect(screen.getByText("4 pieces")).toBeInTheDocument();
    expect(screen.getByText(/250\.0000/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /add costco nuggets/i }));
    expect(onAdd).toHaveBeenCalledWith(food);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/foods?q=nuggets&limit=20",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("creates a food from label values and calls onAdd", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(food, 201));
    vi.stubGlobal("fetch", fetchMock);
    const onAdd = vi.fn();

    render(<FoodSearch onAdd={onAdd} />);

    await user.click(screen.getByRole("button", { name: /create a food from a label/i }));

    await user.type(screen.getByRole("textbox", { name: /name/i }), "Costco nuggets");
    await user.type(screen.getByRole("textbox", { name: /brand/i }), "Kirkland Signature");
    await user.type(screen.getByRole("textbox", { name: /serving label/i }), "4 pieces");
    await user.type(screen.getByRole("textbox", { name: /serving grams/i }), "88");
    await user.type(screen.getByRole("textbox", { name: /calories/i }), "250.0000");
    await user.type(screen.getByRole("textbox", { name: /protein/i }), "14.0000");
    await user.type(screen.getByRole("textbox", { name: /carbs/i }), "16.0000");
    await user.type(screen.getByRole("textbox", { name: /fat/i }), "14.0000");
    await user.type(screen.getByRole("textbox", { name: /fiber/i }), "1.0000");
    await user.type(screen.getByRole("textbox", { name: /sugar/i }), "2.0000");
    await user.type(screen.getByRole("textbox", { name: /sodium/i }), "400.0000");
    await user.selectOptions(screen.getByRole("combobox", { name: /confidence/i }), "high");
    await user.type(screen.getByRole("textbox", { name: /aliases/i }), "those costco nuggets");

    await user.click(screen.getByRole("button", { name: /^create food$/i }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledWith(food));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/foods",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"name":"Costco nuggets"'),
      }),
    );
  });

  it("pre-fills the form from a result and sends a PATCH with changed values", async () => {
    const user = userEvent.setup();
    const updated = { ...food, name: "Costco nuggets (updated)", calories: "275.0000" };
    const fetchMock = vi.fn((input: unknown, init?: RequestInit): Promise<Response> => {
      const method = init?.method ?? "GET";
      if (String(input).startsWith("/api/foods?") && method === "GET") {
        return Promise.resolve(jsonResponse([food]));
      }
      if (String(input) === "/api/foods/1" && method === "PATCH") {
        return Promise.resolve(jsonResponse(updated));
      }
      return Promise.resolve(jsonResponse({ detail: "not found" }, 404));
    });
    vi.stubGlobal("fetch", fetchMock);
    const onAdd = vi.fn();

    render(<FoodSearch onAdd={onAdd} />);

    await user.type(screen.getByRole("textbox", { name: /search foods/i }), "nuggets");
    await user.click(screen.getByRole("button", { name: /^search$/i }));
    expect(await screen.findByText("Costco nuggets")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /edit costco nuggets/i }));

    expect(screen.getByRole("textbox", { name: /^name$/i })).toHaveValue("Costco nuggets");
    expect(screen.getByRole("textbox", { name: /^calories$/i })).toHaveValue("250.0000");
    expect(screen.getByRole("textbox", { name: /aliases/i })).toHaveValue("those costco nuggets");
    expect(screen.getByRole("combobox", { name: /confidence/i })).toHaveValue("high");

    await user.clear(screen.getByRole("textbox", { name: /^name$/i }));
    await user.type(screen.getByRole("textbox", { name: /^name$/i }), updated.name);
    await user.clear(screen.getByRole("textbox", { name: /^calories$/i }));
    await user.type(screen.getByRole("textbox", { name: /^calories$/i }), updated.calories);
    await user.click(screen.getByRole("button", { name: /^save food$/i }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledWith(updated));
    const patchCall = fetchMock.mock.calls.find(
      ([input, init]) => String(input) === "/api/foods/1" && init?.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    const body = JSON.parse(String(patchCall?.[1]?.body));
    expect(body.name).toBe(updated.name);
    expect(body.calories).toBe(updated.calories);
    expect(body.source).toBe("user_label");
  });

  it("preserves provider provenance when editing a sourced food", async () => {
    const user = userEvent.setup();
    const sourcedFood = {
      ...food,
      id: 2,
      name: "Chick-fil-A sandwich",
      source: "usda_fdc",
      source_url: "https://fdc.example/170790",
      confidence: "low",
    };
    const fetchMock = vi.fn((input: unknown, init?: RequestInit): Promise<Response> => {
      const method = init?.method ?? "GET";
      if (String(input).startsWith("/api/foods?") && method === "GET") {
        return Promise.resolve(jsonResponse([sourcedFood]));
      }
      if (String(input) === "/api/foods/2" && method === "PATCH") {
        return Promise.resolve(jsonResponse(sourcedFood));
      }
      return Promise.resolve(jsonResponse({ detail: "not found" }, 404));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<FoodSearch onAdd={vi.fn()} />);

    await user.type(screen.getByRole("textbox", { name: /search foods/i }), "sandwich");
    await user.click(screen.getByRole("button", { name: /^search$/i }));
    await user.click(await screen.findByRole("button", { name: /edit chick-fil-a sandwich/i }));

    await user.clear(screen.getByRole("textbox", { name: /^name$/i }));
    await user.type(screen.getByRole("textbox", { name: /^name$/i }), "Chick-fil-A sandwich B");
    await user.click(screen.getByRole("button", { name: /^save food$/i }));

    const patchCall = fetchMock.mock.calls.find(
      ([input, init]) => String(input) === "/api/foods/2" && init?.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    const body = JSON.parse(String(patchCall?.[1]?.body));
    expect(body.source).toBe("usda_fdc");
    expect(body.source_url).toBe("https://fdc.example/170790");
    expect(body.confidence).toBe("low");
  });

  it("shows an error when search fails", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "unavailable" }, 503)));

    render(<FoodSearch onAdd={vi.fn()} />);

    await user.type(screen.getByRole("textbox", { name: /search foods/i }), "nuggets");
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/503/i);
  });
});
