# Customer and technical demonstration

Prepared on 30 October 2026, Asia/Calcutta, for the user's own voice recording. This is a recording script, not a submitted video. Use the verified [public app](https://tme7d41m5t.vercel.app) and [repository](https://github.com/Mayank2142/tme7d41m5t). Keep the full recording under ten minutes, with each part under five minutes. Aim for about nine minutes including pauses and transitions. The [recording checklist](RECORDING_CHECKLIST.md) gives exact start links, code tabs, a timing budget and upload checks.

Use a clean browser, 1440-pixel window and readable zoom. Start with January 31, the 09:00 cutoff and the accepted real release. Avoid showing private account pages, terminals containing credentials or Docker's unrelated workloads. Verify the spoken numbers against the displayed selection before recording.

## Part 1 Customer pilot, 0:00–4:30

**0:00–0:35 · Decision outlook.**

“Wind Desk helps your procurement team answer two questions: what wind forecast was available before a day-ahead decision, and how large were the errors in comparable historical decisions? This pilot uses Elexon's national Great Britain wind data. January refers to purchase decisions, so our final delivery day is February 1.”

**0:35–1:35 · January 31 at 09:00. Show delivery bounds, coverage and the publication ledger.**

“For this decision, all 24 native forecast targets are available. The midnight February 1 forecast is 10,099 megawatts. Each target is selected independently from source publications at or before the desk cutoff. Publication age and source records make the replay inspectable. This view stays focused on the forecast; subsequent actual generation belongs in the retrospective review.”

“The 09:00 cutoff is an illustrative desk assumption. We would agree your venue, actual submission time and operating buffer before operational use. This replay models source publication time; it does not claim that we recorded your team's historical receipt times.”

**1:35–2:25 · Change the cutoff to 09:45, show the draft warning, apply and inspect the chart with the keyboard.**

“The screen and download remain tied to the applied selection while I edit. At 09:45, the 09:30 issue is eligible. The midnight forecast becomes 10,474 megawatts, and its age is 15 minutes. The next native target is 10,117 megawatts. The publication ledger provides exact values behind the chart.”

**2:25–3:45 · Open Forecast accuracy for the full month. Show metrics, signed errors and daily drill-down.**

“At this cutoff, all 744 native comparison targets have valid pairs. Mean absolute error is approximately 1,995.6 megawatts. Root mean square error is 2,498.8. Signed bias is positive 1,728.0, meaning the forecast overestimated wind on average. P90 absolute error is 4,183.9 megawatts.”

“The signed plot distinguishes overforecast from underforecast. Selecting a day narrows the analysis without changing its release or cutoff. Coverage remains explicit; a missing observation would remain a gap, rather than becoming zero or disappearing from the denominator.”

“These are descriptive historical statistics. P90 is not a calibrated procurement buffer or a guaranteed future interval. National wind alone does not establish your portfolio's entitlement or the amount to buy; that would also require demand and existing positions.”

**3:45–4:30 · Show CSV and Data & methodology.**

“The export follows the exact release and analysis context on screen. Forecasts are hourly source targets, while actuals are half-hourly. We compare matching source timestamps, and retain the other actual half-hours in the export without inventing intermediate forecasts. The methodology view includes original source links and response hashes. This pilot gives the desk a reproducible basis for discussing wind uncertainty, with the assumptions and limits visible.”

## Part 2 Technical handoff, 4:30–9:00

**4:30–5:20 · Show the architecture and repository map.**

“React and TypeScript provide the workbench. FastAPI serves the compiled frontend and typed read APIs from one origin. PostgreSQL stores source revisions, raw responses and immutable accepted releases. The operator CLI performs ingestion and migrations separately from user requests. The bundled January archive makes startup and ordinary CI independent of live Elexon availability.”

**5:20–6:30 · Open the domain selector, comparison policy and tests.**

“The important temporal rule is to select the latest eligible source key, then validate that selected key. We do not silently fall back to an older valid forecast when the latest issue is null or conflicting. Actuals use the latest publication within the frozen release for retrospective analysis. Decision responses and exports exclude actuals entirely.”

“The default policy compares equal source timestamps. The forecast cadence is 60 minutes and actual cadence is 30 minutes; we neither forward-fill forecasts nor assume a full-hour energy profile. Positive error means forecast minus actual. Unit tests cover cutoff equality, post-cutoff exclusion, invalid latest keys, revised actuals, missing data, zeros and the January-to-February boundary.”

**6:30–7:20 · Show API context and CSV handling.**

“The release, parser, calculation policies, dates, cutoff and build identifier form a canonical analysis context. Exports are pinned to that context; a stale context is rejected. The browser validates response and download identity. CSV preserves all 1,488 actual half-hours and marks the 744 native comparison targets and valid metric contributions explicitly. Numeric nulls remain blank, and text formula prefixes are neutralized without altering negative numeric errors.”

**7:20–8:20 · Show verification evidence and local startup.**

“The latest verification record includes 107 backend tests with no skips against PostgreSQL, and 47 frontend tests. A separate service gate independently recalculates metrics from the CSV. The public app passed a fresh logged-out Chrome journey, cutoff changes, keyboard inspection, daily review, exact downloads, reload and mobile layouts. A replacement Vercel deployment retained the same release and analysis fingerprints.”

“The local container runs as a non-root user with a read-only root filesystem, temporary scratch space and dropped capabilities. The one-off initializer imports the real seed. The public Vercel function builds from source and uses a separate restricted PostgreSQL reader over verified TLS. Two free edge rules reject write requests and private-file probes. The CI workflow uses pinned Actions and image inputs, minimal repository permissions and retained failure evidence. Its published Actions run makes the complete workflow reviewable.”

Before recording the preceding CI sentence, confirm a successful run for the latest public commit in the repository's Actions tab. If it is pending or failed, resolve it first and use the final evidence record.

**8:20–9:00 · Explain review boundaries and next steps.**

“The README provides the live application link, startup commands, directory map, source attribution and explicit AI disclosure. Verification scripts and methodology explain how to reproduce the result. The public repository preserves the reviewed history, and the deployment record identifies the exact source and dataset used by the hosted app.”

“Operational launch still needs client cutoff and domain approval, a distributed request quota and trusted proxy identity, client-approved access controls, scheduled ingestion, measured hosted recovery and sustained capacity, and support ownership. Those are recorded as later work. This public historical pilot demonstrates traceable forecasts and reproducible errors; operational acceptance is a separate decision.”

## Before submission

- Record and review the full video, including audio, at no more than ten minutes.
- Upload it as unlisted and test playback in a logged-out browser.
- Add the actual application, repository and video URLs to README and the submission checklist.
- Recheck the final committed version, public app, source attribution and all links before submitting.
