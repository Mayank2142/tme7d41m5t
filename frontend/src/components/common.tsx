import { type AnchorHTMLAttributes, type ReactNode, useEffect, useRef, useState } from "react";
import { downloadCsv, ServiceError } from "../api/analysis";
import type { AccuracyResponse, DecisionResponse } from "../api/types";
import { number, reasonLabel } from "../format";

export function WindMark() {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <path d="M7 13h18a4 4 0 1 0-4-4M7 21h26M7 29h12a4 4 0 1 1-4 4" />
    </svg>
  );
}
export function RouteLink({
  navigate,
  href,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; navigate: (href: string) => void }) {
  return (
    <a
      href={href}
      {...props}
      onClick={(event) => {
        if (
          event.button === 0 &&
          !event.ctrlKey &&
          !event.metaKey &&
          !event.shiftKey &&
          !event.altKey &&
          href
        ) {
          event.preventDefault();
          navigate(href);
        }
      }}
    />
  );
}
export function ScrollRegion({
  children,
  label,
  className = "",
}: {
  children: ReactNode;
  label: string;
  className?: string;
}) {
  return (
    // biome-ignore lint/a11y/noNoninteractiveTabindex: A named scroll container needs keyboard focus so arrow keys can reach off-screen table columns.
    <section className={`table-wrap ${className}`} tabIndex={0} aria-label={label}>
      {children}
    </section>
  );
}
export function Metric({
  label,
  value,
  unit,
  detail,
  tone,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  detail: ReactNode;
  tone?: string;
}) {
  return (
    <article className={`metric ${tone ?? ""}`}>
      <h2>{label}</h2>
      <div className="metric-value">
        {value}
        {unit && <span>{unit}</span>}
      </div>
      <p>{detail}</p>
    </article>
  );
}
export function ErrorNotice({
  error,
  retry,
  title = "Could not load this analysis",
}: {
  error: unknown;
  retry: () => void;
  title?: string;
}) {
  const message =
    error instanceof ServiceError
      ? error.message
      : "The service could not be reached. Check the connection and try again.";
  return (
    <div className="notice error" role="alert">
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
        {error instanceof ServiceError && error.requestId && (
          <small>Request reference: {error.requestId}</small>
        )}
      </div>
      <button type="button" onClick={retry}>
        Try again
      </button>
    </div>
  );
}
export function Loading({ label = "Loading selected analysis…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="loading">
      <span className="spinner" />
      {label}
      <div className="skeleton-grid">
        {[0, 1, 2, 3].map((key) => (
          <span key={key} />
        ))}
      </div>
    </div>
  );
}
export function Status({ state, reason }: { state: string; reason: string | null }) {
  return (
    <span
      className={`badge ${state === "valid" || state === "paired" ? "good" : "warning"}`}
      title={reason ?? undefined}
    >
      {state === "valid" || state === "paired" ? "Valid" : reasonLabel(reason)}
    </span>
  );
}
export function SourceIds({ ids }: { ids: string[] }) {
  return ids.length ? (
    <details className="source-ids">
      <summary>Source record{ids.length > 1 ? "s" : ""}</summary>
      {ids.map((id) => (
        <code key={id}>{id}</code>
      ))}
    </details>
  ) : (
    <span className="muted">—</span>
  );
}
export function AnalysisReference({ result }: { result: DecisionResponse | AccuracyResponse }) {
  return (
    <details className="analysis-reference">
      <summary>
        Analysis reference <code>{result.analysis_context_id.slice(0, 12)}</code>
      </summary>
      <dl>
        <div>
          <dt>Context</dt>
          <dd>
            <code>{result.analysis_context_id}</code>
          </dd>
        </div>
        <div>
          <dt>Dataset release</dt>
          <dd>
            <code>{result.context.release_id}</code>
          </dd>
        </div>
        <div>
          <dt>Source parser</dt>
          <dd>{result.context.source_parser}</dd>
        </div>
        <div>
          <dt>Application build</dt>
          <dd>{result.context.build_sha}</dd>
        </div>
      </dl>
      <a href={result.source.data_quality_url} target="_blank" rel="noreferrer">
        Open source quality JSON ↗
      </a>
    </details>
  );
}
export function DownloadButton({
  result,
  disabled,
  reload,
}: {
  result: DecisionResponse | AccuracyResponse;
  disabled: boolean;
  reload: () => void;
}) {
  const [status, setStatus] = useState<"idle" | "busy" | "done">("idle");
  const [error, setError] = useState<unknown>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function download() {
    setStatus("busy");
    setError(null);
    controller.current = new AbortController();
    try {
      const { blob, filename } = await downloadCsv(result, controller.current.signal);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setStatus("done");
    } catch (error) {
      if (!controller.current.signal.aborted) {
        setError(error);
        setStatus("idle");
      }
    }
  }
  return (
    <div className="download-control">
      <button
        className="primary"
        type="button"
        disabled={disabled || status === "busy"}
        onClick={download}
      >
        {status === "busy" ? "Preparing CSV…" : "↓ Download CSV"}
      </button>
      {status === "done" && <span role="status">Download prepared</span>}
      {error !== null && (
        <div className="download-error" role="alert">
          <span>
            {error instanceof ServiceError ? error.message : "Download failed. Please try again."}
          </span>
          <button type="button" onClick={reload}>
            Reload analysis
          </button>
        </div>
      )}
    </div>
  );
}
export function CoverageNotice({
  expected,
  valid,
  label,
}: {
  expected: number;
  valid: number;
  label: string;
}) {
  if (valid === expected) return null;
  return (
    <div className="notice warning" role="status">
      <div>
        <strong>{valid === 0 ? "No valid data for this selection" : "Partial coverage"}</strong>
        <p>
          {number(valid)} of {number(expected)} {label}. Missing or invalid values remain gaps and
          are excluded from metrics.
        </p>
      </div>
    </div>
  );
}
