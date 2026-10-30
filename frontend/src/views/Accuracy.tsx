import { useState } from "react";
import type { AccuracyResponse } from "../api/types";
import { Chart } from "../components/Chart";
import {
  AnalysisReference,
  CoverageNotice,
  Metric,
  RouteLink,
  ScrollRegion,
  SourceIds,
  Status,
} from "../components/common";
import { dateLabel, number, reasonLabel, signed, timeLabel } from "../format";
import { type Filters, hrefFor } from "../state";

export function AccuracyView({
  result,
  filters,
  navigate,
}: {
  result: AccuracyResponse;
  filters: Filters;
  navigate: (href: string) => void;
}) {
  const { analysis } = result;
  const { metrics, coverage, days } = analysis;
  const [page, setPage] = useState(0);
  const points = days.flatMap((day) =>
    day.points.map((point) => ({ ...point, decision_date: day.window.decision_date })),
  );
  const actuals = days.flatMap((day) => day.actual_half_hours);
  const misses = points
    .filter((point) => point.error_mw !== null)
    .sort(
      (a, b) =>
        Math.abs(b.error_mw ?? 0) - Math.abs(a.error_mw ?? 0) ||
        a.target_start_utc.localeCompare(b.target_start_utc),
    )
    .slice(0, 5);
  const dailyMax = Math.max(1, ...days.map((day) => day.metrics.mae_mw ?? 0));
  const inspect = (index: number) => {
    const point = points[index];
    return {
      title: timeLabel(point.target_start_utc, true),
      items: [
        { label: "Forecast", value: `${number(point.forecast.generation_mw)} MW` },
        { label: "Reported actual", value: `${number(point.actual.generation_mw)} MW` },
        { label: "Signed error", value: `${signed(point.error_mw)} MW` },
        {
          label: "Forecast published",
          value: point.forecast.publication_utc
            ? `${timeLabel(point.forecast.publication_utc, true)} GMT`
            : reasonLabel(point.forecast.reason),
        },
      ],
    };
  };
  const perPage = 24;
  const pages = Math.ceil(points.length / perPage);
  const visible = points.slice(page * perPage, (page + 1) * perPage);
  return (
    <>
      <div className="selection-summary">
        <span className="badge amber">Retrospective review</span>
        <span>
          Decisions{" "}
          <strong>
            {dateLabel(result.context.decision_from)}–{dateLabel(result.context.decision_to, true)}
          </strong>{" "}
          · <strong>{result.context.cutoff_local} GMT</strong>
        </span>
        <span className="coverage-pill">
          {number(coverage.paired)} / {number(coverage.expected)} paired targets
        </span>
      </div>
      <CoverageNotice
        expected={coverage.expected}
        valid={coverage.paired}
        label="valid forecast/actual comparison pairs"
      />
      <div className="metrics-grid">
        <Metric
          label="Mean absolute error"
          value={number(metrics.mae_mw, 1)}
          unit="MW"
          detail="Average size of a source-time miss"
        />
        <Metric
          label="Root mean square error"
          value={number(metrics.rmse_mw, 1)}
          unit="MW"
          detail="Gives larger misses more weight"
        />
        <Metric
          label="Signed bias"
          value={signed(metrics.bias_mw, 1)}
          unit="MW"
          tone={metrics.bias_mw !== null && metrics.bias_mw > 0 ? "warm" : undefined}
          detail={
            metrics.bias_mw === null
              ? "No valid comparison pairs"
              : metrics.bias_mw > 0
                ? "Wind overforecast on average"
                : metrics.bias_mw < 0
                  ? "Wind underforecast on average"
                  : "No net signed bias"
          }
        />
        <Metric
          label="P90 absolute error"
          value={number(metrics.p90_absolute_error_mw, 1)}
          unit="MW"
          detail="Descriptive historical tail of errors"
        />
      </div>
      <section className="panel plot-panel" aria-labelledby="comparison-title">
        <div className="panel-heading">
          <div>
            <h2 id="comparison-title">Forecast and reported wind</h2>
          </div>
          <span className="badge neutral">Hourly forecast · half-hour actual</span>
        </div>
        <Chart
          title="Wind forecast and reported generation"
          description="Forecasts selected at each original cutoff, with original half-hour actuals from the frozen release. Metrics use equal-timestamp pairs only."
          targets={points.map((point) => point.target_start_utc)}
          series={[
            {
              label: "Selected forecast",
              color: "#176d68",
              points: points.map((point) => ({
                time: point.target_start_utc,
                value: point.forecast.generation_mw,
              })),
            },
            {
              label: "Reported actual",
              color: "#b48145",
              points: actuals.map((point) => ({
                time: point.target_start_utc,
                value: point.actual.generation_mw,
              })),
              dashed: true,
            },
          ]}
          inspect={inspect}
        />
        <p className="panel-footnote">
          Metrics compare identical source timestamps. The source fields have different native
          resolutions; matching timestamps does not establish identical averaging intervals.
        </p>
      </section>
      <section className="panel plot-panel error-plot" aria-labelledby="error-title">
        <div className="panel-heading">
          <div>
            <h2 id="error-title">Signed forecast errors</h2>
          </div>
          <span className="direction-key">
            <i className="over" />
            Overforecast <i className="under" />
            Underforecast
          </span>
        </div>
        <Chart
          title="Signed forecast error"
          signed
          description="Forecast minus equal-timestamp actual. Positive bars mean wind was overestimated; negative bars mean it was underestimated. Missing pairs remain gaps."
          series={[
            {
              label: "Forecast minus actual",
              color: "#b85f43",
              points: points.map((point) => ({
                time: point.target_start_utc,
                value: point.error_mw,
              })),
            },
          ]}
          targets={points.map((point) => point.target_start_utc)}
          inspect={inspect}
        />
      </section>
      <div className="review-grid">
        <section className="panel" aria-labelledby="daily-title">
          <div className="panel-heading">
            <div>
              <h2 id="daily-title">Accuracy by decision day</h2>
            </div>
          </div>
          <ScrollRegion label="Daily accuracy" className="daily-table">
            <table>
              <caption>
                Purchase decisions; select a date to inspect that day. Values in MW.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Decision</th>
                  <th scope="col">Pairs</th>
                  <th scope="col">MAE</th>
                  <th scope="col">Bias</th>
                </tr>
              </thead>
              <tbody>
                {days.map((day) => (
                  <tr key={day.window.decision_date}>
                    <th scope="row">
                      <RouteLink
                        href={hrefFor("accuracy", {
                          ...filters,
                          date: day.window.decision_date,
                          from: day.window.decision_date,
                          to: day.window.decision_date,
                        })}
                        navigate={navigate}
                      >
                        {dateLabel(day.window.decision_date)} ↗
                      </RouteLink>
                    </th>
                    <td>
                      {day.coverage.paired}/{day.coverage.expected}
                    </td>
                    <td className="numeric">
                      <span
                        className="mini-bar"
                        style={{ width: `${((day.metrics.mae_mw ?? 0) / dailyMax) * 100}%` }}
                      />
                      {number(day.metrics.mae_mw)}
                    </td>
                    <td
                      className={`numeric ${day.metrics.bias_mw !== null && day.metrics.bias_mw > 0 ? "over-text" : ""}`}
                    >
                      {signed(day.metrics.bias_mw)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollRegion>
        </section>
        <section className="panel" aria-labelledby="misses-title">
          <div className="panel-heading">
            <div>
              <h2 id="misses-title">Largest forecast errors</h2>
            </div>
          </div>
          {misses.length ? (
            <ScrollRegion label="Largest forecast misses">
              <table>
                <caption>Native delivery targets, ranked by absolute error. Values in MW.</caption>
                <thead>
                  <tr>
                    <th scope="col">Delivery target</th>
                    <th scope="col">Forecast</th>
                    <th scope="col">Actual</th>
                    <th scope="col">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {misses.map((point) => (
                    <tr key={point.target_start_utc}>
                      <th scope="row">
                        <RouteLink
                          href={hrefFor("decision", { ...filters, date: point.decision_date })}
                          navigate={navigate}
                        >
                          {timeLabel(point.target_start_utc, true)} ↗
                        </RouteLink>
                      </th>
                      <td className="numeric">{number(point.forecast.generation_mw)}</td>
                      <td className="numeric">{number(point.actual.generation_mw)}</td>
                      <td
                        className={`numeric ${(point.error_mw ?? 0) > 0 ? "over-text" : "under-text"}`}
                      >
                        {signed(point.error_mw)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollRegion>
          ) : (
            <p className="empty-copy">No valid comparison pairs in this selection.</p>
          )}
          <p className="panel-footnote">
            Positive = wind overforecast. Select a delivery target to inspect its original decision.
          </p>
        </section>
      </div>
      <section className="panel coverage-panel" aria-labelledby="coverage-title">
        <div>
          <h2 id="coverage-title">Coverage ledger</h2>
          <p>
            Categories follow forecast-first precedence and sum to {number(coverage.expected)}{" "}
            expected native targets.
          </p>
        </div>
        <dl>
          {[
            ["Paired", coverage.paired],
            ["Forecast missing", coverage.forecast_missing],
            ["Forecast invalid", coverage.forecast_invalid],
            ["Actual missing", coverage.actual_missing],
            ["Actual invalid", coverage.actual_invalid],
          ].map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{number(Number(value))}</dd>
            </div>
          ))}
        </dl>
        <p className="coverage-note">
          Separate actual-source coverage: {number(analysis.actual_source_coverage.valid)} /{" "}
          {number(analysis.actual_source_coverage.expected)} half-hours. Historical P90 describes
          this sample; it is not a calibrated future confidence interval.
        </p>
      </section>
      <details className="panel ledger-panel">
        <summary>
          <span>Comparison data & source records</span>
          <span className="muted">{number(points.length)} expected targets · paginated</span>
        </summary>
        <ScrollRegion label="Comparison data">
          <table>
            <caption>Equal source timestamps. Times in Europe/London, GMT. Values in MW.</caption>
            <thead>
              <tr>
                <th scope="col">Delivery target</th>
                <th scope="col">Forecast</th>
                <th scope="col">Actual</th>
                <th scope="col">Error</th>
                <th scope="col">Status</th>
                <th scope="col">Sources</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((point) => (
                <tr key={point.target_start_utc}>
                  <th scope="row">{timeLabel(point.target_start_utc, true)}</th>
                  <td className="numeric">{number(point.forecast.generation_mw)}</td>
                  <td className="numeric">{number(point.actual.generation_mw)}</td>
                  <td className="numeric">{signed(point.error_mw)}</td>
                  <td>
                    <Status state={point.state} reason={point.reason} />
                  </td>
                  <td>
                    <details className="source-ids">
                      <summary>Publications & records</summary>
                      <p>Forecast: {timeLabel(point.forecast.publication_utc, true)} GMT</p>
                      <SourceIds ids={point.forecast.source_version_ids} />
                      <p>Actual: {timeLabel(point.actual.publication_utc, true)} GMT</p>
                      <SourceIds ids={point.actual.source_version_ids} />
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollRegion>
        <nav className="pagination" aria-label="Comparison table pages">
          <span>
            {page * perPage + 1}–{Math.min((page + 1) * perPage, points.length)} of {points.length}
          </span>
          <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>
            Previous page
          </button>
          <button type="button" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>
            Next page
          </button>
        </nav>
      </details>
      <AnalysisReference result={result} />
    </>
  );
}
