import type { DecisionResponse } from "../api/types";
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
import { ageLabel, dateLabel, number, reasonLabel, timeLabel } from "../format";
import { type Filters, hrefFor } from "../state";

export function DecisionView({
  result,
  filters,
  navigate,
}: {
  result: DecisionResponse;
  filters: Filters;
  navigate: (href: string) => void;
}) {
  const { analysis } = result;
  const { window, summary, coverage, points } = analysis;
  const oldest = summary.earliest_publication_utc
    ? (Date.parse(window.cutoff_utc) - Date.parse(summary.earliest_publication_utc)) / 1000
    : null;
  const peak = points.find((point) => point.forecast.generation_mw === summary.maximum_reported_mw);
  return (
    <>
      <div className="selection-summary">
        <span className="badge good">Historical replay</span>
        <span>
          Decision <strong>{dateLabel(window.decision_date)}</strong> at{" "}
          <strong>{window.cutoff_local} GMT</strong>
        </span>
        <span className="summary-arrow">→</span>
        <span>
          Delivery <strong>{dateLabel(window.delivery_date, true)}</strong> · 00:00–24:00 GMT
        </span>
      </div>
      <CoverageNotice
        expected={coverage.expected}
        valid={coverage.valid}
        label="native forecast targets available"
      />
      <div className="metrics-grid">
        <Metric
          label="Available targets"
          value={`${coverage.valid} / ${coverage.expected}`}
          detail={
            <>
              <span
                className={`inline-dot ${coverage.valid === coverage.expected ? "good" : "warning"}`}
              />
              {coverage.valid === coverage.expected
                ? "Complete forecast coverage"
                : `${coverage.missing} missing · ${coverage.invalid} invalid`}
            </>
          }
        />
        <Metric
          label="Mean reported wind"
          value={number(summary.mean_reported_mw)}
          unit="MW"
          detail="Mean of valid native forecast targets"
        />
        <Metric
          label="Peak reported wind"
          value={number(summary.maximum_reported_mw)}
          unit="MW"
          detail={
            peak && summary.maximum_reported_mw !== null
              ? `Target ${timeLabel(peak.target_start_utc)} GMT`
              : "No valid forecast target"
          }
        />
        <Metric
          label="Oldest issue at cutoff"
          value={ageLabel(oldest)}
          detail={
            summary.earliest_publication_utc
              ? `Published ${timeLabel(summary.earliest_publication_utc, true)} GMT`
              : "No eligible publication"
          }
        />
      </div>
      <div className="decision-grid">
        <section className="panel plot-panel" aria-labelledby="wind-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">NEXT-DAY WIND OUTLOOK</p>
              <h2 id="wind-title">The forecast available to your desk</h2>
            </div>
            <span className="badge neutral">{dateLabel(window.delivery_date)}</span>
          </div>
          <Chart
            key={result.analysis_context_id}
            title="Day-ahead wind forecast"
            description="Native hourly forecast targets. Missing or invalid values break the line. Connecting targets does not establish an hourly energy profile."
            series={[
              {
                label: "Eligible wind forecast",
                color: "#176d68",
                points: points.map((point) => ({
                  time: point.target_start_utc,
                  value: point.forecast.generation_mw,
                })),
              },
            ]}
            targets={points.map((point) => point.target_start_utc)}
            inspect={(index) => {
              const point = points[index];
              return {
                title: timeLabel(point.target_start_utc, true),
                items: [
                  { label: "Forecast", value: `${number(point.forecast.generation_mw)} MW` },
                  {
                    label: "Published",
                    value: point.forecast.publication_utc
                      ? `${timeLabel(point.forecast.publication_utc, true)} GMT`
                      : "No eligible issue",
                  },
                  { label: "Age at cutoff", value: ageLabel(point.age_at_cutoff_seconds) },
                  { label: "Quality", value: reasonLabel(point.forecast.reason) },
                ],
              };
            }}
          />
          <p className="panel-footnote">
            Hourly source targets · Selected independently by publication time · Lines connect
            reported points; they do not define an energy profile.
          </p>
        </section>
        <aside className="desk-note panel">
          <span className="note-symbol" aria-hidden="true">
            ↗
          </span>
          <p className="eyebrow">DECISION CONTEXT</p>
          <h2>Know what was available.</h2>
          <p>
            Each target uses its latest source publication at or before{" "}
            <strong>{window.cutoff_local} GMT</strong>.
          </p>
          <dl>
            <div>
              <dt>Lowest reported target</dt>
              <dd>{number(summary.minimum_reported_mw)} MW</dd>
            </div>
            <div>
              <dt>Selected issue range</dt>
              <dd>
                {timeLabel(summary.earliest_publication_utc, true)}–
                {timeLabel(summary.latest_publication_utc, true)} GMT
              </dd>
            </div>
            <div>
              <dt>Coverage</dt>
              <dd>
                {coverage.valid} valid · {coverage.missing + coverage.invalid} gaps
              </dd>
            </div>
          </dl>
          <p>
            The desk cutoff is an illustrative assumption. Agree the auction and submission buffer
            before operational use.
          </p>
          <RouteLink className="text-link" href={hrefFor("accuracy", filters)} navigate={navigate}>
            Review January forecast error <span aria-hidden="true">→</span>
          </RouteLink>
        </aside>
      </div>
      <details className="panel ledger-panel">
        <summary>
          <span>Forecast publication ledger</span>
          <span className="muted">
            {points.length} native targets · exact values & source records
          </span>
        </summary>
        <ScrollRegion label="Forecast publication ledger">
          <table>
            <caption>
              Delivery {dateLabel(window.delivery_date, true)}. All times Europe/London, GMT.
            </caption>
            <thead>
              <tr>
                <th scope="col">Target</th>
                <th scope="col">Forecast MW</th>
                <th scope="col">Published GMT</th>
                <th scope="col">Age at cutoff</th>
                <th scope="col">Quality</th>
                <th scope="col">Provenance</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.target_start_utc}>
                  <th scope="row">{timeLabel(point.target_start_utc)}</th>
                  <td className="numeric">{number(point.forecast.generation_mw)}</td>
                  <td>{timeLabel(point.forecast.publication_utc, true)}</td>
                  <td>{ageLabel(point.age_at_cutoff_seconds)}</td>
                  <td>
                    <Status state={point.forecast.state} reason={point.forecast.reason} />
                  </td>
                  <td>
                    <SourceIds ids={point.forecast.source_version_ids} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollRegion>
      </details>
      <AnalysisReference result={result} />
    </>
  );
}
