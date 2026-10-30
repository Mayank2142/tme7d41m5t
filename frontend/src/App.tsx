import { useQuery } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { loadAccuracy, loadDecision, loadQuality } from "./api/analysis";
import { type Configuration, loadConfiguration } from "./api/client";
import { DownloadButton, ErrorNotice, Loading, RouteLink, WindMark } from "./components/common";
import { MotionEffects, MotionRegion } from "./components/Motion";
import { ViewIcon, WindScene } from "./components/WindScene";
import {
  CUTOFF,
  type Filters,
  hrefFor,
  JANUARY,
  selectionError,
  selectionFrom,
  useLocation,
  type View,
} from "./state";
import { AccuracyView } from "./views/Accuracy";
import { DecisionView } from "./views/Decision";
import { MethodologyView } from "./views/Methodology";

function Shell({
  children,
  configuration,
}: {
  children: ReactNode;
  configuration?: Configuration;
}) {
  return (
    <div className="app-shell">
      <MotionEffects />
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="site-header">
        <a className="brand" href="/">
          <span className="brand-mark">
            <WindMark />
          </span>
          <span className="brand-name">
            Wind Desk<small>Wind intelligence</small>
          </span>
        </a>
        <div className="header-context">
          <span className="header-period">January 2026</span>
          <span className="header-market">
            <span className="header-market-dot" />
            GB national wind
          </span>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
      <footer>
        <span>
          {configuration?.data_attribution ?? "Data source: Elexon"}{" "}
          {configuration && (
            <a
              className="footer-licence"
              href={configuration.data_licence_url}
              target="_blank"
              rel="noreferrer"
            >
              Licence ↗
            </a>
          )}
        </span>
      </footer>
    </div>
  );
}
function FilterForm({
  view,
  filters,
  navigate,
  dirtyChanged,
}: {
  view: View;
  filters: Filters;
  navigate: (href: string) => void;
  dirtyChanged: (dirty: boolean) => void;
}) {
  const [draft, setDraft] = useState(filters);
  const [submitted, setSubmitted] = useState(false);
  const error = submitted ? selectionError(view, draft) : null;
  function change(key: keyof Filters, value: string) {
    const next = { ...draft, [key]: value };
    setDraft(next);
    dirtyChanged(hrefFor(view, next) !== hrefFor(view, filters));
  }
  function apply(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!selectionError(view, draft)) {
      navigate(hrefFor(view, draft));
      dirtyChanged(false);
    }
  }
  if (view === "methodology")
    return (
      <div className="method-scope">
        <strong>January source release</strong>
        <span>Decisions 1–31 Jan · Delivery 2 Jan–1 Feb 2026 · Europe/London</span>
      </div>
    );
  return (
    <form className="filters" onSubmit={apply} noValidate aria-label="Analysis selection">
      {view === "decision" ? (
        <label>
          Purchase decision date
          <input
            aria-invalid={!JANUARY.test(draft.date)}
            type="date"
            min="2026-01-01"
            max="2026-01-31"
            required
            value={draft.date}
            onChange={(event) => change("date", event.target.value)}
          />
        </label>
      ) : (
        <>
          <label>
            First decision date
            <input
              aria-invalid={!JANUARY.test(draft.from)}
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              required
              value={draft.from}
              onChange={(event) => change("from", event.target.value)}
            />
          </label>
          <label>
            Last decision date
            <input
              aria-invalid={!JANUARY.test(draft.to) || draft.to < draft.from}
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              required
              value={draft.to}
              onChange={(event) => change("to", event.target.value)}
            />
          </label>
        </>
      )}
      <label>
        Desk cutoff · GMT
        <input
          aria-invalid={!CUTOFF.test(draft.cutoff)}
          type="time"
          step={60}
          required
          value={draft.cutoff}
          onChange={(event) => change("cutoff", event.target.value)}
          aria-describedby="cutoff-help"
        />
      </label>
      <button type="submit" className="primary">
        Apply selection <span aria-hidden="true">→</span>
      </button>
      <p id="cutoff-help" className="filter-help">
        Illustrative desk time · Europe/London
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
function Workbench({
  configuration,
  location,
  navigate,
  checkRelease,
  checkingRelease,
  configurationError,
}: {
  configuration: Configuration;
  location: string;
  navigate: (href: string, replace?: boolean) => void;
  checkRelease: () => Promise<Configuration | undefined>;
  checkingRelease: boolean;
  configurationError: unknown;
}) {
  const { view, filters, problem } = selectionFrom(
    location,
    configuration.dataset.release_id ?? "",
    configuration.default_cutoff_local,
  );
  const canonical = hrefFor(view, filters);
  const [dirty, setDirty] = useState(false);
  const [shareState, setShareState] = useState("");
  const [releaseMessage, setReleaseMessage] = useState("");
  useEffect(() => {
    if (!problem && canonical !== location) navigate(canonical, true);
  }, [canonical, problem, location, navigate]);
  useEffect(() => {
    if (location === window.location.pathname + window.location.search) {
      setDirty(false);
      setShareState("");
      document.getElementById("page-title")?.focus({ preventScroll: true });
    }
  }, [location]);
  const enabled = !problem && Boolean(filters.release);
  const decision = useQuery({
    queryKey: ["decision", filters.date, filters.cutoff, filters.release],
    queryFn: ({ signal }) => loadDecision(filters, signal),
    enabled: enabled && view === "decision",
    retry: false,
  });
  const accuracy = useQuery({
    queryKey: ["accuracy", filters.from, filters.to, filters.cutoff, filters.release],
    queryFn: ({ signal }) => loadAccuracy(filters, signal),
    enabled: enabled && view === "accuracy",
    retry: false,
  });
  const quality = useQuery({
    queryKey: ["quality", filters.release],
    queryFn: ({ signal }) => loadQuality(filters.release, signal),
    enabled: enabled && view === "methodology",
    retry: false,
  });
  const query = view === "decision" ? decision : view === "accuracy" ? accuracy : quality;
  const result =
    view === "decision" ? decision.data : view === "accuracy" ? accuracy.data : undefined;
  const noRelease =
    !filters.release &&
    configuration.dataset.release_id === null &&
    !new URL(location, "http://workbench.local").searchParams.has("release_id");
  const reset = () =>
    navigate(
      hrefFor(view, {
        date: "2026-01-31",
        from: "2026-01-01",
        to: "2026-01-31",
        cutoff: configuration.default_cutoff_local,
        release: configuration.dataset.release_id ?? "",
      }),
    );
  async function refreshRelease() {
    setReleaseMessage("");
    const current = await checkRelease();
    if (current?.dataset.release_id) {
      navigate(hrefFor(view, { ...filters, release: current.dataset.release_id }));
      setReleaseMessage("Using the latest available data.");
    } else if (current)
      setReleaseMessage("Source data is unavailable. Your current selection is unchanged.");
  }
  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareState("Link copied");
    } catch {
      setShareState("Copy the current address from your browser to share this selection.");
    }
  }
  return (
    <Shell configuration={configuration}>
      <WindScene view={view} />
      <nav className="view-tabs" aria-label="Workspace views">
        {(["decision", "accuracy", "methodology"] as const).map((item) => (
          <RouteLink
            key={item}
            navigate={navigate}
            href={hrefFor(item, filters)}
            aria-current={view === item ? "page" : undefined}
          >
            <ViewIcon view={item} />
            {item === "decision"
              ? "Decision outlook"
              : item === "accuracy"
                ? "Forecast accuracy"
                : "Data & methodology"}
          </RouteLink>
        ))}
      </nav>
      <div className="source-status">
        <span className="source-label">
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <ellipse cx="10" cy="4" rx="6" ry="2" />
            <path d="M4 4v6c0 1.1 2.7 2 6 2s6-.9 6-2V4M4 10v6c0 1.1 2.7 2 6 2s6-.9 6-2v-6" />
          </svg>
          Elexon wind data
        </span>
        <div className="source-actions">
          {configuration.dataset.release_id &&
            configuration.dataset.release_id !== filters.release && (
              <span className="source-update-note">Newer data available</span>
            )}
          <button
            type="button"
            className="source-update"
            onClick={refreshRelease}
            disabled={checkingRelease || dirty}
          >
            {checkingRelease ? "Updating…" : "Use latest data"}
          </button>
        </div>
      </div>
      {releaseMessage && (
        <p className="feedback" role="status">
          {releaseMessage}
        </p>
      )}
      {configurationError !== null && (
        <ErrorNotice
          error={configurationError}
          retry={refreshRelease}
          title="Could not update source data"
        />
      )}
      {noRelease ? (
        <div className="panel unavailable">
          <WindMark />
          <h2>January source data is unavailable</h2>
          <p>
            {configuration.dataset.status === "unavailable"
              ? "The stored dataset could not be reached. Check the service and try again."
              : "An accepted source release is needed before this workspace can run an analysis."}
          </p>
          <button type="button" onClick={refreshRelease} disabled={checkingRelease}>
            Check again
          </button>
        </div>
      ) : (
        <>
          <FilterForm
            key={location}
            view={view}
            filters={filters}
            navigate={navigate}
            dirtyChanged={setDirty}
          />
          {problem && (
            <div className="notice error" role="alert">
              <div>
                <strong>Check this selection</strong>
                <p>{problem}</p>
              </div>
              <button type="button" onClick={reset}>
                Reset to January defaults
              </button>
            </div>
          )}
          {dirty && (
            <div className="notice warning" role="status">
              <div>
                <strong>Unapplied changes</strong>
                <p>
                  Apply the selection to update the analysis. The result below still uses the last
                  applied filters.
                </p>
              </div>
            </div>
          )}
          {!problem && (
            <>
              {query.isError && (
                <ErrorNotice
                  error={query.error}
                  retry={() => {
                    void query.refetch();
                  }}
                  title={
                    query.data
                      ? "Refresh failed; the last successful result remains below"
                      : "Could not load this selection"
                  }
                />
              )}
              {query.isPending && (
                <Loading
                  label={
                    view === "methodology"
                      ? "Loading source provenance…"
                      : "Loading the selected analysis…"
                  }
                />
              )}
              {query.data && (
                <>
                  <div className="result-toolbar">
                    {query.isFetching && <span role="status">Refreshing selected analysis…</span>}
                    <div>
                      <button
                        type="button"
                        onClick={() => {
                          void query.refetch();
                        }}
                        disabled={dirty || query.isFetching}
                      >
                        ↻ Refresh {view === "methodology" ? "data" : "analysis"}
                      </button>
                      <button type="button" onClick={copyLink} disabled={dirty || query.isFetching}>
                        Copy view link
                      </button>
                      {result && (
                        <DownloadButton
                          key={result.analysis_context_id}
                          result={result}
                          disabled={dirty || query.isFetching || query.isError}
                          reload={() => {
                            void query.refetch();
                          }}
                        />
                      )}
                    </div>
                  </div>
                  {shareState && (
                    <p className="feedback" role="status">
                      {shareState}
                    </p>
                  )}
                  <MotionRegion
                    key={result?.analysis_context_id ?? quality.data?.release_id ?? view}
                    aria-busy={query.isFetching}
                    className={query.isError ? "last-result" : undefined}
                  >
                    {view === "decision" && decision.data && (
                      <DecisionView
                        key={decision.data.analysis_context_id}
                        result={decision.data}
                        filters={filters}
                        navigate={navigate}
                      />
                    )}
                    {view === "accuracy" && accuracy.data && (
                      <AccuracyView
                        key={accuracy.data.analysis_context_id}
                        result={accuracy.data}
                        filters={filters}
                        navigate={navigate}
                      />
                    )}
                    {view === "methodology" && quality.data && (
                      <MethodologyView data={quality.data} />
                    )}
                  </MotionRegion>
                </>
              )}
            </>
          )}
        </>
      )}
    </Shell>
  );
}
export default function App() {
  const { location, navigate } = useLocation();
  const configuration = useQuery({
    queryKey: ["configuration"],
    queryFn: ({ signal }) => loadConfiguration(signal),
    staleTime: Infinity,
    retry: false,
  });
  async function checkRelease() {
    const result = await configuration.refetch();
    return result.isError ? undefined : result.data;
  }
  if (configuration.data)
    return (
      <Workbench
        configuration={configuration.data}
        location={location}
        navigate={navigate}
        checkRelease={checkRelease}
        checkingRelease={configuration.isFetching}
        configurationError={configuration.isError ? configuration.error : null}
      />
    );
  return (
    <Shell>
      <div className="page-intro">
        <div>
          <h1>Wind forecast workbench</h1>
          <p className="intro-copy">Preparing the source release and analysis policies.</p>
        </div>
      </div>
      {configuration.isPending ? (
        <Loading label="Connecting to the workspace…" />
      ) : (
        <ErrorNotice
          error={configuration.error}
          retry={() => {
            void configuration.refetch();
          }}
          title="Workspace unavailable"
        />
      )}
    </Shell>
  );
}
