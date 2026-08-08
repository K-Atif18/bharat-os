import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ErrorBoundary from "@/app/error";

describe("ErrorBoundary", () => {
  it("offers recovery without exposing the raw error", () => {
    const reset = vi.fn();
    render(<ErrorBoundary error={new Error("sensitive backend detail")} reset={reset} />);

    expect(screen.getByRole("alert")).toHaveTextContent("No application was submitted");
    expect(screen.queryByText("sensitive backend detail")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
