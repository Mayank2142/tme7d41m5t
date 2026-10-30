// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { ReferencePanel } from "./References";

const reference = "a".repeat(64);
const clipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");
const showModal = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, "showModal");
const close = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, "close");
const writeText = vi.fn();

// jsdom does not implement native dialog methods; real-browser verification
// covers modal focus, background inertness, Escape and return focus.
beforeAll(() => {
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value(this: HTMLDialogElement) {
        this.open = true;
      },
    },
    close: {
      configurable: true,
      value(this: HTMLDialogElement) {
        if (!this.open) return;
        this.open = false;
        this.dispatchEvent(new Event("close"));
      },
    },
  });
});
beforeEach(() => {
  writeText.mockReset().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
});
afterEach(cleanup);
afterAll(() => {
  for (const [name, descriptor] of [
    ["showModal", showModal],
    ["close", close],
  ] as const) {
    if (descriptor) Object.defineProperty(HTMLDialogElement.prototype, name, descriptor);
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name);
  }
  if (clipboard) Object.defineProperty(navigator, "clipboard", clipboard);
  else Reflect.deleteProperty(navigator, "clipboard");
});

function mount() {
  return render(
    <ReferencePanel
      title="About this analysis"
      description="31 Jan 2026 · 09:00 GMT · Elexon wind data"
      fields={[{ label: "Analysis ID", value: reference }]}
    />,
  );
}

describe("reference details", () => {
  it("keeps full identifiers off the page until requested and restores scroll on close", () => {
    mount();
    expect(screen.queryByText(reference)).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /View references/ }));
    const dialog = screen.getByRole("dialog", { name: "About this analysis" });
    expect(screen.getByText(reference)).toBeInTheDocument();
    expect(document.body.style.overflow).toBe("hidden");
    const closeButton = screen.getByRole("button", { name: "Close references" });
    const copyButton = screen.getByRole("button", { name: "Copy analysis id" });
    closeButton.focus();
    fireEvent.keyDown(closeButton, { key: "Tab", shiftKey: true });
    expect(copyButton).toHaveFocus();
    fireEvent.keyDown(copyButton, { key: "Tab" });
    expect(closeButton).toHaveFocus();
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe("");
    expect(screen.getByRole("button", { name: /View references/ })).toHaveFocus();
  });
  it("copies the complete identifier with accessible confirmation", async () => {
    mount();
    fireEvent.click(screen.getByRole("button", { name: /View references/ }));
    fireEvent.click(screen.getByRole("button", { name: "Copy analysis id" }));
    await screen.findByText("Analysis ID copied");
    expect(writeText).toHaveBeenCalledExactlyOnceWith(reference);
  });
  it("offers manual copying when clipboard access is blocked and unlocks scroll on unmount", async () => {
    writeText.mockRejectedValueOnce(new Error("Clipboard blocked"));
    const view = mount();
    fireEvent.click(screen.getByRole("button", { name: /View references/ }));
    fireEvent.click(screen.getByRole("button", { name: "Copy analysis id" }));
    await screen.findByText(/Select the reference above to copy it manually/);
    expect(screen.getByText(reference)).toBeInTheDocument();
    view.unmount();
    expect(document.body.style.overflow).toBe("");
  });
});
