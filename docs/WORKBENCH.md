# Analyst Workbench Guide

The React interface runs at [the local workbench](http://127.0.0.1:8000/). It uses the real frozen Elexon release through the read APIs. Public deployment is a later phase.

The interface keeps the analyst controls, charts and source coverage in view. Decorative labels, numbered headings, repeated source badges and the explanatory Decision sidebar have been removed. The forecast chart uses the full available width. A compact **Elexon wind data** label identifies the source; technical version and build identifiers are available through **View references** in the **About this analysis** card and the methodology view.

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

Source rows use compact response numbers and **View details** actions. Full response checksums and batch references open in a focused dialog, with labeled copy controls and a manual-copy explanation if clipboard access is blocked. **Data and calculation references** uses the same layout for the source release and calculation policies. Full hashes are kept out of the default page layout; the original values and source links are preserved.

The original source quality checks cover 09:00 and 09:45. Decision and Accuracy calculate coverage for their actual selected cutoff. Source-time comparison, different native resolutions, estimated outturn, national scope, and the lack of utility demand/price/position inputs remain visible limits.

## Selection, sharing, and refresh

- The address stores the decision date, accuracy range, cutoff, and explicit release. Tab navigation preserves all saved dates, cutoff, and release; API requests send only fields relevant to their endpoint.
- **Copy view link** copies that address. Browser Back/Forward and reloading a shared address restore the applied selection. If clipboard access fails, the interface explains how to copy the address manually.
- Input edits are drafts. Until applied, a notice identifies them and the previous applied result remains labeled with its original context. Downloads and refresh actions are disabled during unapplied edits. Leaving a view discards its unapplied draft.
- Applying new filters creates a separate request keyed by the effective mode/date/cutoff/release. An uncached request shows a loading state, rather than reusing another selection's cards under new labels. Obsolete requests receive an abort signal.
- **Refresh analysis** reloads the same pinned selection. A failed refresh is explicit; the last successful result remains identified and its download is disabled until a successful reload.
- **Use latest data** explicitly checks configuration and selects the current accepted dataset. A **Newer data available** notice identifies when the saved view uses an earlier release. Loading a newer configuration does not silently replace a shared link's selection. This action reads stored metadata; it does not initiate ingestion or a source download.

Unsupported or repeated address parameters produce an explained invalid-selection state with a reset action. Missing configuration, no accepted dataset, failed analysis, partial coverage, and no valid data have separate displays.

## Downloads

Use **Download CSV** on a loaded Decision or Accuracy view. The client follows the server-provided, release-pinned export URL and verifies the response's media type, release header, and analysis-context header before creating a download. A 409 or mismatched response produces a visible explanation and reload action.

Decision CSV contains twenty-four expected native targets and forecast data only. Full-month Accuracy CSV contains 1,488 half-hour target rows; 744 are native comparison targets. Only rows with `used_in_metrics=true` contribute to metrics. Actual-only half-hours retain empty forecast/error cells. Missing numeric values stay empty and valid zero stays `0`.

See [API and CSV contract](API.md) for exact columns and independent recomputation. Choose **View references** in **About this analysis** to see and copy the full analysis ID, data version, source parser and application build.

## Accessibility and layout

Navigation uses real links with current-page labels, browser history, a skip link, and focus movement to the view heading. Controls have explicit labels and visible focus. Chart values are available through a keyboard slider and exact-value tables, with text explaining direction and missing values. Tables use captions and scoped headers; wide tables scroll within named keyboard-focusable sections.

The layout adapts across desktop, tablet, and narrow screens. Reduced-motion preferences disable animated loading indicators. The frontend cleanup passed all 43 existing frontend tests, lint, TypeScript and the production build. Real Chrome checks covered the analyst journey, exact downloads, native version disclosure, and 1440/390/320-pixel layouts with zero console errors. These checks do not substitute for a comprehensive assistive-technology audit.

Reference dialogs use native modal behavior: the background becomes inert, keyboard focus stays in the dialog, Escape and the close button dismiss it, and focus returns to the opening action. Background scrolling is locked while details are open. Long values wrap on narrow screens; copy actions always use the complete original identifier. Opening animation respects reduced-motion preferences.

The reference redesign passed 46 frontend tests, lint and the production build. The updated Chrome journey verifies exact reference values, copy feedback, keyboard focus cycling and return focus, Escape/close actions, matching CSV downloads, and dialogs at 1440/390/320-pixel widths with zero console errors. Screenshots and the browser report are generated under ignored `output/playwright/reference-redesign/`.

## Motion and cursor

The workspace now includes a photographic offshore-wind header, forest/sage accents, icon navigation, and softly outlined metric cards. **Compact view** reduces the header height without changing the selected dates, cutoff, source release or downloaded values; **Expand scene** restores it. This preference stays in the current workspace across tab changes.

The methodology page includes a second coastal-wind landscape and a brief visual introduction to the analysis workflow. Both images are AI-generated illustrations; their provenance is documented in the README and asset guide. The interface uses neutral descriptions and no AI labels. These images do not represent observed January weather, named generating sites, or additional analytical data. Optimized WebP assets are served locally with the application (about 204 KiB combined). The header image loads with high priority, and the methodology image loads lazily. [Image provenance and generation prompts](../frontend/src/assets/README.md) document the assets.

The photographic update passed 47 frontend tests, lint, TypeScript and the production build. Chrome verified both self-hosted images, compact-header state without another analysis request, exact CSV downloads, the existing analyst journey, metric fit and reference dialogs at 1440/390/320-pixel widths, and dynamic reduced-motion settings, with zero console errors. Its screenshots, JUnit file and browser report are in ignored `output/playwright/wind-visuals/`. The running local Docker build uses marker `frontend-wind-visuals-local`.

Page headings transition when changing views; cards reveal once as they enter the viewport, charts draw in, and buttons, tabs and disclosure panels provide short interaction feedback. A thin progress line shows the current scroll position. Reported values and calculation results are not animated or interpolated.

Motion uses a slower, softer pace: headings enter over 900 ms, cards over 850 ms with a gentle stagger, and charts draw over 1.45 seconds. Cursor trailing uses elapsed time rather than a fixed per-frame step so it feels consistent on different refresh rates. Controls act immediately while their visual feedback eases into place.

On devices with a mouse and hover support, a decorative ring follows the pointer and expands over links and buttons. The system cursor remains visible. The overlay cannot intercept clicks and hides over form inputs, during keyboard use, when the pointer leaves the window, and on touch devices. Its animation loop stops when the pointer settles.

The operating system's **Reduce motion** preference disables decorative transitions, chart reveals, scroll progress and cursor effects, including when the preference changes while the page is open. If animation or intersection APIs are unavailable, the content remains visible. No animation library or extra runtime dependency is required.
