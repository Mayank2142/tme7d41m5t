import type { QualityResponse } from "../api/types";
import { ScrollRegion } from "../components/common";
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
          <h2>Forecast versions</h2>
          <div className="metric-value">{number(quality.forecast_versions)}</div>
          <p>WINDFOR source publications</p>
        </article>
        <article className="metric">
          <h2>Reported actuals</h2>
          <div className="metric-value">{number(quality.actual_versions)}</div>
          <p>FUELHH records with fuelType WIND</p>
        </article>
        <article className="metric">
          <h2>Actual source coverage</h2>
          <div className="metric-value">
            {number(quality.valid_actual_half_hours)}
            <span>/ {number(quality.expected_actual_half_hours)}</span>
          </div>
          <p>Expected half-hour observations</p>
        </article>
        <article className="metric">
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
      <div className="method-grid">
        <section className="panel method-card">
          <span className="method-number">01</span>
          <h2>A decision calendar, in London time</h2>
          <p>
            Purchase decisions run from 1–31 January 2026. Each concerns the following UK civil day,
            so the final decision covers 1 February delivery.
          </p>
          <p>
            The default 09:00 desk cutoff is illustrative. The client must agree its auction,
            internal cutoff, and submission buffer before operational use.
          </p>
        </section>
        <section className="panel method-card">
          <span className="method-number">02</span>
          <h2>The latest eligible key, then its quality</h2>
          <p>
            For every native forecast target, select the greatest source publication at or before
            the cutoff. Targets may use different issue times.
          </p>
          <p>
            A null or conflicting latest key remains an explicit gap. It never silently falls back
            to an older valid forecast. Publication time establishes historical source availability;
            October download time does not prove January receipt by a desk.
          </p>
        </section>
        <section className="panel method-card">
          <span className="method-number">03</span>
          <h2>Matching timestamps, explicit limits</h2>
          <p>
            WINDFOR targets are hourly. FUELHH WIND actuals are half-hour averages. The primary
            comparison uses identical source startTime values: 744 expected pairs across the month.
          </p>
          <p>
            The intervening 744 actual half-hours stay visible and are retained in CSV. No extra
            forecasts are manufactured. Equal timestamps do not establish identical averaging
            intervals or a forecast energy profile.
          </p>
        </section>
        <section className="panel method-card">
          <span className="method-number">04</span>
          <h2>Retrospective error with a frozen vintage</h2>
          <p>
            Accuracy uses the latest actual publication within the selected release, validated after
            key selection. Reported outturn may include estimates and is not certified final
            settlement truth.
          </p>
          <p>
            Decision replay contains eligible forecasts. Retrospective actuals and errors belong to
            the Accuracy view. A refreshed release cannot rewrite a previously pinned chart or
            download.
          </p>
        </section>
      </div>
      <section className="panel formula-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">METRICS V1 · ALL VALUES IN MW</p>
            <h2>One sign convention, four descriptive measures</h2>
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
        <h2>What this pilot can support</h2>
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
            <p className="eyebrow">SOURCE PROVENANCE</p>
            <h2 id="provenance-title">Original responses, retained and fingerprinted</h2>
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
                <th scope="col">SHA-256 & batch reference</th>
              </tr>
            </thead>
            <tbody>
              {raw_batches.map((batch) => (
                <tr key={batch.id}>
                  <th scope="row">{batch.dataset}</th>
                  <td>{timeLabel(batch.received_at, true)}</td>
                  <td>
                    <a href={batch.source_url} target="_blank" rel="noreferrer">
                      Open Elexon response ↗
                    </a>
                  </td>
                  <td>
                    <details className="source-ids">
                      <summary>{batch.payload_sha256.slice(0, 12)}…</summary>
                      <span>Response digest</span>
                      <code>{batch.payload_sha256}</code>
                      <span>Batch ID</span>
                      <code>{batch.id}</code>
                    </details>
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
      <details className="analysis-reference">
        <summary>Release and calculation policies</summary>
        <dl>
          <div>
            <dt>Release</dt>
            <dd>
              <code>{data.release_id}</code>
            </dd>
          </div>
          <div>
            <dt>Parser</dt>
            <dd>{quality.parser_version}</dd>
          </div>
          <div>
            <dt>Validation</dt>
            <dd>{quality.validation_version}</dd>
          </div>
          <div>
            <dt>Acceptance</dt>
            <dd>{quality.acceptance_policy}</dd>
          </div>
          <div>
            <dt>Comparison</dt>
            <dd>source_timestamp_v1</dd>
          </div>
          <div>
            <dt>Selection</dt>
            <dd>latest_source_key_v1</dd>
          </div>
          <div>
            <dt>Actual vintage</dt>
            <dd>latest_publication_in_release_v1</dd>
          </div>
          <div>
            <dt>Normalized versions fingerprint</dt>
            <dd>
              <code>
                {quality.normalized_versions_sha256 ?? "Not recorded in this legacy release"}
              </code>
            </dd>
          </div>
        </dl>
      </details>
    </>
  );
}
