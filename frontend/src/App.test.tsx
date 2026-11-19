import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the app title inside a phone-width container", () => {
    const { container } = render(<App />);
    expect(screen.getByRole("heading", { name: /calorie tracker/i })).toBeInTheDocument();
    expect(container.querySelector(".max-w-md")).not.toBeNull();
  });
});
