import { useState } from "react";
import coastalWind from "../assets/coastal-wind.webp";
import offshoreWind from "../assets/offshore-wind.webp";
import type { View } from "../state";

const SCENES = {
  decision: {
    eyebrow: "Day-ahead decisions",
    title: "Wind outlook at the cutoff",
    description: "Wind forecasts available before each January purchase decision.",
  },
  accuracy: {
    eyebrow: "Historical performance",
    title: "Understand the forecast error",
    description: "Compare the forecast available at the cutoff with reported generation.",
  },
  methodology: {
    eyebrow: "Behind the numbers",
    title: "Data & methodology",
    description: "Elexon data, forecast selection and calculation rules.",
  },
};

export function ViewIcon({ view }: { view: View }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      {view === "decision" ? (
        <>
          <path d="M12 12v9M12 12 9 3M12 12l9-2M12 12l-6 7" />
          <circle cx="12" cy="12" r="1.6" />
        </>
      ) : view === "accuracy" ? (
        <>
          <path d="M4 4v16h16M7 14l4-5 4 3 5-6" />
          <path d="M7 17h13" strokeDasharray="2 3" />
        </>
      ) : (
        <path d="M5 4h14v16H5zM9 8h6M9 12h6M9 16h4" />
      )}
    </svg>
  );
}

export function WindScene({ view }: { view: View }) {
  const [compact, setCompact] = useState(false);
  const scene = SCENES[view];
  return (
    <section
      className={`wind-scene page-intro ${compact ? "is-compact" : ""}`}
      aria-labelledby="page-title"
    >
      <img
        className="wind-scene-image"
        src={offshoreWind}
        alt=""
        width="1440"
        height="960"
        fetchPriority="high"
        decoding="async"
      />
      <div className="wind-scene-shade" />
      <div className="wind-scene-copy" key={view}>
        <p className="scene-eyebrow">
          <span />
          {scene.eyebrow}
        </p>
        <h1 id="page-title" tabIndex={-1}>
          {scene.title}
        </h1>
        <p className="intro-copy">{scene.description}</p>
        <div className="scene-context">
          <span>Great Britain</span>
          <span>January 2026</span>
          <span>Historical pilot</span>
        </div>
      </div>
      <button
        type="button"
        className="scene-toggle"
        aria-pressed={compact}
        aria-label="Compact header"
        onClick={() => setCompact(!compact)}
      >
        <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d={compact ? "m5 8 5-4 5 4M5 12l5 4 5-4" : "m5 4 5 4 5-4M5 16l5-4 5 4"} />
        </svg>
        {compact ? "Expand scene" : "Compact view"}
      </button>
    </section>
  );
}

export function WindStory() {
  return (
    <section className="wind-story panel" aria-labelledby="wind-story-title">
      <figure>
        <img
          src={coastalWind}
          width="960"
          height="640"
          loading="lazy"
          decoding="async"
          alt="Wind turbines on green coastal hills"
        />
        <figcaption>Coastal wind landscape</figcaption>
      </figure>
      <div className="wind-story-copy">
        <p className="story-eyebrow">From changing winds to clearer decisions</p>
        <h2 id="wind-story-title">A forecast is a view of what might come.</h2>
        <p>
          Wind changes with the weather. This workspace preserves the forecast available at a
          decision cutoff, then uses reported generation to understand how it performed.
        </p>
        <div className="story-steps">
          <span>
            <ViewIcon view="decision" />
            Inspect the outlook
          </span>
          <span>
            <ViewIcon view="accuracy" />
            Measure the miss
          </span>
          <span>
            <ViewIcon view="methodology" />
            Trace the source
          </span>
        </div>
      </div>
    </section>
  );
}

export function MetricIcon({ label }: { label: string }) {
  const kind = /coverage|targets/i.test(label)
    ? "coverage"
    : /issue|retrieval/i.test(label)
      ? "clock"
      : /peak/i.test(label)
        ? "peak"
        : /error|bias/i.test(label)
          ? "error"
          : "wind";
  return (
    <span className="metric-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        {kind === "coverage" ? (
          <>
            <circle cx="12" cy="12" r="8" />
            <path d="m8 12 3 3 5-6" />
          </>
        ) : kind === "clock" ? (
          <>
            <circle cx="12" cy="12" r="8" />
            <path d="M12 7v5l3 2" />
          </>
        ) : kind === "peak" ? (
          <path d="M4 19h16M5 15l5-7 4 4 5-8M15 4h4v4" />
        ) : kind === "error" ? (
          <>
            <path d="M4 12h16M7 8v8M12 5v14M17 9v6" />
            <circle cx="7" cy="8" r="1" />
            <circle cx="17" cy="16" r="1" />
          </>
        ) : (
          <path d="M3 7h12a3 3 0 1 0-3-3M3 12h17M3 17h9a3 3 0 1 1-3 3" />
        )}
      </svg>
    </span>
  );
}
