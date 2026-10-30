import type { QualityResponse } from "../api/types";
import { ScrollRegion } from "../components/common";
import { ReferenceDialog, ReferencePanel } from "../components/References";
import { MetricIcon, WindStory } from "../components/WindScene";
import { dateLabel, number, timeLabel } from "../format";

export function MethodologyView({ data }: { data: QualityResponse }) {
  const { quality, raw_batches } = data;
  const latestReceipt = raw_batches
    .map((batch) => batch.received_at)
    .sort()
    .at(-1);
  return (
    <>
      <div className="selection-summary">
        <span className={`badge ${quality.status === "complete" ? "good" : "warning"}`}>
          {quality.status === "complete" ? "Validated source release" : "Partial source release"}
        </span>
        <span>National wind data from Elexon · frozen historical vintage</span>
      </div>
      <div className="metrics-grid">
        <article className="metric">
          <MetricIcon label="Forecast versions" />
          <h2>Forecast versions</h2>
          <div className="metric-value">{number(quality.forecast_versions)}</div>
          <p>WINDFOR source publications</p>
        </article>
        <article className="metric">
          <MetricIcon label="Reported actuals" />
          <h2>Reported actuals</h2>
          <div className="metric-value">{number(quality.actual_versions)}</div>
          <p>FUELHH records with fuelType WIND</p>
        </article>
        <article className="metric">
          <MetricIcon label="Actual source coverage" />
          <h2>Actual source coverage</h2>
          <div className="metric-value">
            {number(quality.valid_actual_half_hours)}
            <span>/ {number(quality.expected_actual_half_hours)}</span>
          </div>
          <p>Expected half-hour observations</p>
        </article>
        <article className="metric">
          <MetricIcon label="Last source retrieval" />
          <h2>Last source retrieval</h2>
          <div className="metric-value small-value">
            {latestReceipt ? dateLabel(latestReceipt.slice(0, 10), true) : "—"}
          </div>
          <p>
            {latestReceipt
              ? `${timeLabel(latestReceipt)} GMT · project download time`
              : "No source receipt recorded"}
          </p>
        </article>
      </div>
      <WindStory />
      <div className="method-grid">
        <section className="panel method-card">
          <h2>Decision dates and cutoff</h2>
          <p>
            January purchase decisions cover next-day delivery, from 2 January to 1 February. All
            times use Europe/London.
          </p>
          <p>
            The 09:00 default is illustrative. Agree the actual cutoff and submission buffer before
            operational use.
          </p>
        </section>
        <section className="panel method-card">
          <h2>Forecast selection</h2>
          <p>
            Each target uses its latest publication at or before the cutoff. A missing or
            conflicting latest value stays a gap; an older value is never substituted.
          </p>
          <p>
            Publication time determines eligibility. The project's download time does not prove
            January receipt by a desk.
          </p>
        </section>
        <section className="panel method-card">
          <h2>Matching timestamps, explicit limits</h2>
          <p>
            Hourly WINDFOR targets are paired with FUELHH WIND actuals at matching timestamps: 744
            expected pairs across January.
          </p>
          <p>
            All 1,488 actual half-hours remain in CSV. Forecasts are not filled between targets.
            Matching timestamps do not establish identical averaging intervals or an energy profile.
          </p>
        </section>
        <section className="panel method-card">
          <h2>Historical actuals</h2>
          <p>
            Accuracy uses the latest actual publication in the selected data version. Reported
            outturn may include estimates rather than final settlement values.
          </p>
          <p>
            Actuals appear only in Accuracy. Saved views and downloads keep their selected data
            version when a newer release becomes available.
          </p>
        </section>
      </div>
      <section className="panel formula-panel">
        <div className="panel-heading">
          <div>
            <h2>Accuracy measures · MW</h2>
          </div>
        </div>
        <p className="equation">
          Signed error = forecast − actual <span>Positive means wind was overforecast.</span>
        </p>
        <div className="formula-grid">
          <article>
            <h3>MAE</h3>
            <p>Mean absolute error. The average size of the miss.</p>
          </article>
          <article>
            <h3>RMSE</h3>
            <p>Square root of mean squared error. Larger misses carry more weight.</p>
          </article>
          <article>
            <h3>Signed bias</h3>
            <p>Mean signed error. Opposite directions can cancel.</p>
          </article>
          <article>
            <h3>P90 absolute error</h3>
            <p>Linear interpolation at sorted index (n − 1) × 0.9. Descriptive historical tail.</p>
          </article>
        </div>
        <p className="panel-footnote">
          Range metrics pool valid target errors. No-pair metrics are null; missing data never
          becomes zero. Hourly errors can be correlated. P90 is not a calibrated future confidence
          interval or procurement buffer.
        </p>
      </section>
      <section className="panel method-card limitation">
        <h2>Scope</h2>
        <p>
          Inspect the wind outlook available to the desk and quantify historical forecast error. The
          source covers national wind visible to the system operator. Utility demand, existing
          positions, renewable entitlement, and prices are outside this assignment, so a
          purchase-volume or financial recommendation cannot be inferred.
        </p>
      </section>
      <section className="panel" aria-labelledby="provenance-title">
        <div className="panel-heading">
          <div>
            <h2 id="provenance-title">Source responses</h2>
          </div>
          <span className="badge neutral">{raw_batches.length} request windows</span>
        </div>
        <div className="quality-counts">
          <span>{quality.exact_duplicate_rows} exact duplicate rows</span>
          <span>{quality.conflicting_source_keys} conflicting keys</span>
          <span>{quality.invalid_source_versions} invalid source versions</span>
        </div>
        <ScrollRegion label="Source response provenance">
          <table>
            <caption>
              Receipt is the project's source-download time. Source publications determine forecast
              eligibility.
            </caption>
            <thead>
              <tr>
                <th scope="col">Dataset</th>
                <th scope="col">Received GMT</th>
                <th scope="col">Original source query</th>
                <th scope="col">Reference</th>
              </tr>
            </thead>
            <tbody>
              {raw_batches.map((batch, index) => (
                <tr key={batch.id}>
                  <th scope="row">{batch.dataset}</th>
                  <td>{timeLabel(batch.received_at, true)}</td>
                  <td>
                    <a href={batch.source_url} target="_blank" rel="noreferrer">
                      Open Elexon response ↗
                    </a>
                  </td>
                  <td>
                    <div className="source-reference">
                      <span>Response {String(index + 1).padStart(2, "0")}</span>
                      <ReferenceDialog
                        title={`${batch.dataset} response ${String(index + 1).padStart(2, "0")}`}
                        description={`Elexon source response · retrieved ${timeLabel(batch.received_at, true)} GMT`}
                        triggerLabel="View details"
                        triggerName={`View references for ${batch.dataset} response ${index + 1}`}
                        fields={[
                          {
                            label: "Response checksum",
                            value: batch.payload_sha256,
                            description: "SHA-256 fingerprint of the original downloaded response.",
                          },
                          {
                            label: "Batch reference",
                            value: batch.id,
                            description:
                              "Identifies this source response in the stored data release.",
                          },
                        ]}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollRegion>
      </section>
      <details className="panel ledger-panel">
        <summary>
          <span>January source-validation ledger</span>
          <span className="muted">31 decisions · two checked cutoffs</span>
        </summary>
        <p className="inside-copy">
          Ingestion validation checks 09:00 and 09:45 GMT. The analysis views calculate coverage for
          the cutoff you actually select.
        </p>
        <ScrollRegion label="Source validation coverage">
          <table>
            <caption>
              Expected native forecasts at each checked cutoff and all actual half-hours.
            </caption>
            <thead>
              <tr>
                <th scope="col">Decision</th>
                <th scope="col">Delivery</th>
                <th scope="col">09:00 forecasts</th>
                <th scope="col">09:45 forecasts</th>
                <th scope="col">Actual half-hours</th>
              </tr>
            </thead>
            <tbody>
              {quality.decisions.map((day) => (
                <tr key={day.decision_date}>
                  <th scope="row">{dateLabel(day.decision_date)}</th>
                  <td>{dateLabel(day.delivery_date)}</td>
                  <td>
                    {day.forecast_cutoffs["09:00"]?.valid ?? "—"} /{" "}
                    {day.forecast_cutoffs["09:00"]?.expected ?? "—"}
                  </td>
                  <td>
                    {day.forecast_cutoffs["09:45"]?.valid ?? "—"} /{" "}
                    {day.forecast_cutoffs["09:45"]?.expected ?? "—"}
                  </td>
                  <td>
                    {day.actual_valid} / {day.actual_expected}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollRegion>
      </details>
      <ReferencePanel
        title="Data and calculation references"
        description="Source version, validation checks and calculation rules for this release."
        fields={[
          { label: "Data version", value: data.release_id },
          { label: "Source parser", value: quality.parser_version, identifier: false },
          { label: "Validation", value: quality.validation_version, identifier: false },
          { label: "Acceptance", value: quality.acceptance_policy, identifier: false },
          { label: "Comparison", value: "source_timestamp_v1", identifier: false },
          { label: "Selection", value: "latest_source_key_v1", identifier: false },
          { label: "Actual vintage", value: "latest_publication_in_release_v1", identifier: false },
          {
            label: "Normalized data fingerprint",
            value: quality.normalized_versions_sha256 ?? "Not recorded in this legacy release",
          },
        ]}
      />
    </>
  );
}
