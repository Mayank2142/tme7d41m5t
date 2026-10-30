import { useEffect, useId, useRef, useState } from "react";

interface ReferenceField {
  label: string;
  value: string;
  description?: string;
  identifier?: boolean;
}

function ReferenceIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z" />
      <path d="M14 3v6h6M8 13h8M8 17h5" />
    </svg>
  );
}

function ReferenceValue({ label, value, description, identifier = true }: ReferenceField) {
  const [status, setStatus] = useState<"idle" | "copied" | "unavailable">("idle");
  useEffect(() => {
    if (status !== "copied") return;
    const timeout = window.setTimeout(() => setStatus("idle"), 2500);
    return () => window.clearTimeout(timeout);
  }, [status]);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setStatus("copied");
    } catch {
      setStatus("unavailable");
    }
  }
  return (
    <div className="reference-field">
      <dt className="reference-field-heading">
        <span>{label}</span>
        <button
          type="button"
          className="reference-copy"
          aria-label={`Copy ${label.toLowerCase()}`}
          onClick={copy}
        >
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <rect x="7" y="7" width="9" height="10" rx="2" />
            <path d="M12 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h2" />
          </svg>
          {status === "copied" ? "Copied" : "Copy"}
        </button>
      </dt>
      <dd>
        {identifier ? <code>{value}</code> : <span className="reference-value">{value}</span>}
        {description && <p className="reference-field-description">{description}</p>}
        <span
          className={status === "unavailable" ? "reference-copy-help" : "sr-only"}
          role="status"
        >
          {status === "copied" && `${label} copied`}
          {status === "unavailable" &&
            "Copy is unavailable. Select the reference above to copy it manually."}
        </span>
      </dd>
    </div>
  );
}

export function ReferenceDialog({
  title,
  description,
  fields,
  triggerLabel = "View references",
  triggerName,
}: {
  title: string;
  description: string;
  fields: ReferenceField[];
  triggerLabel?: string;
  triggerName?: string;
}) {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open || !dialog.current) return;
    const element = dialog.current;
    const previousOverflow = document.body.style.overflow;
    element.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
      trigger.current?.focus({ preventScroll: true });
    };
  }, [open]);

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className="reference-trigger"
        aria-haspopup="dialog"
        aria-label={triggerName}
        onClick={() => setOpen(true)}
      >
        {triggerLabel}
        <span aria-hidden="true">→</span>
      </button>
      {open && (
        <dialog
          ref={dialog}
          className="reference-dialog"
          aria-labelledby={`${id}-title`}
          aria-describedby={`${id}-description`}
          onClose={() => setOpen(false)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              dialog.current?.close();
            }
            if (event.key === "Tab") {
              const buttons =
                event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
              const first = buttons[0];
              const last = buttons[buttons.length - 1];
              const active = document.activeElement;
              if (event.shiftKey && (active === first || active === event.currentTarget)) {
                event.preventDefault();
                last?.focus();
              } else if (!event.shiftKey && (active === last || active === event.currentTarget)) {
                event.preventDefault();
                first?.focus();
              }
            }
          }}
          onClick={(event) => {
            if (event.target !== event.currentTarget) return;
            const bounds = event.currentTarget.getBoundingClientRect();
            if (
              event.clientX < bounds.left ||
              event.clientX > bounds.right ||
              event.clientY < bounds.top ||
              event.clientY > bounds.bottom
            )
              dialog.current?.close();
          }}
        >
          <div className="reference-dialog-content">
            <div className="reference-dialog-heading">
              <span className="reference-icon">
                <ReferenceIcon />
              </span>
              <button
                type="button"
                className="reference-close"
                aria-label="Close references"
                onClick={() => dialog.current?.close()}
              >
                <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="m5 5 10 10M15 5 5 15" />
                </svg>
              </button>
            </div>
            <h2 id={`${id}-title`}>{title}</h2>
            <p id={`${id}-description`} className="reference-dialog-description">
              {description}
            </p>
            <dl className="reference-fields">
              {fields.map((field) => (
                <ReferenceValue key={field.label} {...field} />
              ))}
            </dl>
            <p className="reference-dialog-footnote">
              References preserve the source and calculation history for this saved view.
            </p>
          </div>
        </dialog>
      )}
    </>
  );
}

export function ReferencePanel({
  title,
  description,
  fields,
}: {
  title: string;
  description: string;
  fields: ReferenceField[];
}) {
  return (
    <section className="reference-panel" aria-label={title}>
      <span className="reference-icon">
        <ReferenceIcon />
      </span>
      <div className="reference-panel-copy">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <ReferenceDialog title={title} description={description} fields={fields} />
    </section>
  );
}
