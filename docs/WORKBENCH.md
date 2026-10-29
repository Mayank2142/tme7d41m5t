# Analyst Workbench Guide

The Phase 5 React interface runs at [the local workbench](http://127.0.0.1:8000/). It uses the real frozen Elexon release through the Phase 4 read APIs. Public deployment is a later phase.

## Decision outlook

The default selection is the last January purchase decision, 31 January 2026, with the illustrative 09:00 Europe/London cutoff. Its delivery day is 1 February. Select another January decision date or local cutoff and choose **Apply selection**.

The view shows native forecast coverage, mean and peak reported target values, publication range, and the oldest selected issue's age at cutoff. The chart plots hourly source targets. Move the pointer or use the target slider with Home/End and arrow keys to inspect the exact target, generation, publication, age, and quality. The publication ledger provides all twenty-four expected targets and source-record identities.

Missing and invalid source values remain gaps. A valid zero remains a numeric zero. The Decision route loads forecasts only; actual observations and retrospective scores belong to Accuracy. Lines connect reported source points without establishing a forecast energy profile.

## Forecast accuracy

Choose an inclusive range of January purchase decisions and the same desk cutoff. The service supplies MAE, RMSE, signed bias, P90 absolute error, daily results, and a coverage ledger. Cards display MW and round only for presentation; downloads retain original numeric precision.

The generation chart shows selected hourly forecasts and original half-hour actual observations. The signed-error chart shows forecast minus equal-timestamp actual. Positive means wind was overforecast; negative means underforecast. Both charts support pointer and keyboard inspection.

The daily table includes a relative MAE bar, signed bias, and pair count. Select a day to narrow the complete analysis to that decision. The largest-miss table links each delivery target back to its original Decision view. A paginated comparison ledger exposes exact values, publication times, reasons, and source-version IDs.

Every expected native target enters exactly one of five coverage categories. Separate actual-source coverage counts all half-hours. P90 is a descriptive historical percentile, not a calibrated future confidence interval or a purchase buffer. See [methodology](METHODOLOGY.md) for the calculation and interval assumptions.

## Data and methodology

This view shows source-version counts, actual-source coverage, project download time, original request URLs and response digests, the per-decision ingestion-validation ledger, and versioned calculation rules. Receipt time describes the project's download. Source publication time determines historical forecast eligibility.

The original source quality checks cover 09:00 and 09:45. Decision and Accuracy calculate coverage for their actual selected cutoff. Source-time comparison, different native resolutions, estimated outturn, national scope, and the lack of utility demand/price/position inputs remain visible limits.

## Selection, sharing, and refresh

- The address stores the decision date, accuracy range, cutoff, and explicit release. Tab navigation preserves all saved dates, cutoff, and release; API requests send only fields relevant to their endpoint.
- **Copy view link** copies that address. Browser Back/Forward and reloading a shared address restore the applied selection. If clipboard access fails, the interface explains how to copy the address manually.
- Input edits are drafts. Until applied, a notice identifies them and the previous applied result remains labeled with its original context. Downloads and refresh actions are disabled during unapplied edits. Leaving a view discards its unapplied draft.
- Applying new filters creates a separate request keyed by the effective mode/date/cutoff/release. An uncached request shows a loading state, rather than reusing another selection's cards under new labels. Obsolete requests receive an abort signal.
- **Refresh analysis** reloads the same pinned selection. A failed refresh is explicit; the last successful result remains identified and its download is disabled until a successful reload.
- **Use current source release** explicitly checks configuration and selects the current accepted release. Loading a newer configuration does not silently replace a shared link's pinned release. Source refresh here reads stored metadata; it does not initiate ingestion or a source download.

Unsupported or repeated address parameters produce an explained invalid-selection state with a reset action. Missing configuration, no accepted dataset, failed analysis, partial coverage, and no valid data have separate displays.

## Downloads

Use **Download CSV** on a loaded Decision or Accuracy view. The client follows the server-provided, release-pinned export URL and verifies the response's media type, release header, and analysis-context header before creating a download. A 409 or mismatched response produces a visible explanation and reload action.

Decision CSV contains twenty-four expected native targets and forecast data only. Full-month Accuracy CSV contains 1,488 half-hour target rows; 744 are native comparison targets. Only rows with `used_in_metrics=true` contribute to metrics. Actual-only half-hours retain empty forecast/error cells. Missing numeric values stay empty and valid zero stays `0`.

See [API and CSV contract](API.md) for exact columns and independent recomputation. Each view's expandable analysis reference exposes its full context and release identifiers.

## Accessibility and layout

Navigation uses real links with current-page labels, browser history, a skip link, and focus movement to the view heading. Controls have explicit labels and visible focus. Chart values are available through a keyboard slider and exact-value tables, with text explaining direction and missing values. Tables use captions and scoped headers; wide tables scroll within named keyboard-focusable sections.

The layout adapts across desktop, tablet, and narrow screens. Reduced-motion preferences disable animated loading indicators. Local Chrome verification exercised 1440-pixel desktop, 390-pixel mobile, and a 320-pixel minimum check. These checks do not substitute for a comprehensive assistive-technology audit or the later integrated browser/CI gate.
