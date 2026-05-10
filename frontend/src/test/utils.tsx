import { render, screen, waitFor } from "@testing-library/react";
import type userEvent from "@testing-library/user-event";
import { expect } from "vitest";
import App from "../App.tsx";

export function renderAt(path: string) {
  window.history.pushState(null, "", path);
  return render(<App />);
}

/** `findByRole` matches disabled buttons; clicks on those no-op. Wait until enabled. */
export async function clickEnabledButton(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
  index = 0,
) {
  await waitFor(() => {
    const buttons = screen.getAllByRole("button", { name });
    expect(buttons[index]).toBeDefined();
    expect(buttons[index]).not.toBeDisabled();
  });
  await user.click(screen.getAllByRole("button", { name })[index]);
}
