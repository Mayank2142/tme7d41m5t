# Record and publish the required demonstration

The user will record their own voice. No video or YouTube URL exists yet. The assignment requires a playable unlisted video before submission; the script and screenshots do not replace it.

## Prepare once

1. Use a clean browser window at roughly 1440 × 1000 and readable zoom. Hide personal bookmarks/notifications. Record only this window; exclude account administration, secrets, private terminals and unrelated applications.
2. Open [Decision at January 31, 09:00](https://tme7d41m5t.vercel.app/decision?decision_date=2026-01-31&cutoff_local=09%3A00&release_id=f61cecb1c14d91cfc32f10c74a9945fd2cf7f1851abd8ca6b0eb3f3e8975b052&decision_from=2026-01-01&decision_to=2026-01-31). Let it load before recording. Keep the wind scene expanded initially.
3. Open the [public README](https://github.com/Mayank2142/tme7d41m5t), [architecture map](https://github.com/Mayank2142/tme7d41m5t/blob/main/docs/ARCHITECTURE.md), [selector](https://github.com/Mayank2142/tme7d41m5t/blob/main/backend/app/domain/sources.py), [analysis service](https://github.com/Mayank2142/tme7d41m5t/blob/main/backend/app/services/analysis.py), [domain tests](https://github.com/Mayank2142/tme7d41m5t/blob/main/backend/tests/test_domain_analysis.py) and [Actions](https://github.com/Mayank2142/tme7d41m5t/actions) in prepared tabs. Confirm the latest CI result before describing it as successful.
4. Make a short microphone test and listen to it. OBS Studio is already installed on this machine; use your preferred recorder. No webcam is required by the brief.
5. Keep [the spoken script](DEMO_SCRIPT.md) available outside the recorded window. Rehearse once against the live UI. Explain outcomes and the key integrity rules; avoid reading long hashes or every line of code.

## Nine-minute run of show

| Recording time | Screen/action | Evidence to state |
| --- | --- | --- |
| 0:00–0:35 | Decision opening | Two customer questions; January decisions include February 1 delivery |
| 0:35–1:35 | January 31, 09:00; open publication ledger | 24/24 targets; midnight forecast 10,099 MW; cutoff is illustrative |
| 1:35–2:25 | Edit cutoff to 09:45, apply, inspect chart | 09:30 issue becomes eligible; midnight 10,474 MW; age 15 minutes; next target 10,117 MW |
| 2:25–3:45 | Accuracy, full January; daily drill-down, return to full month | 744 pairs; MAE 1,995.6 MW; RMSE 2,498.8; bias +1,728.0; P90 4,183.9; historical errors are descriptive |
| 3:45–4:30 | Download CSV; Data & methodology; View references | Same release/selection; native hourly forecasts versus half-hour actuals; source provenance |
| **4:30** | **Say “I’ll now switch to the technical review.”** | **Clear boundary between the two required parts** |
| 4:30–5:20 | Architecture and README map | React/FastAPI/PostgreSQL, one origin, separate operator CLI and real frozen seed |
| 5:20–6:30 | `select_latest`, domain tests | Latest eligible key first, validate second; no fallback and no future actuals in Decision |
| 6:30–7:20 | Analysis service/context/export | Pin release/context; independently reproducible metrics; retain all actual half-hours in CSV |
| 7:20–8:20 | Actual successful Actions run; deployment record; Docker files | 107 backend/47 frontend tests; real browser/export/persistence checks; restricted reader/TLS and edge rules |
| 8:20–9:00 | README and limitations | Startup, AI disclosure, public links; operational reliability/capacity/recovery and client acceptance remain separate |

Keep each part below five minutes and total below ten minutes. The nine-minute target leaves a minute of safety margin. If rehearsal runs long, shorten transitions and code detail while preserving both customer workflows and the cutoff/comparison explanation.

For the figures above, **apply 09:45 and restore the full January accuracy range** before reading the monthly metrics. At 09:00 the MAE is 2,022.47 MW instead. A daily drill-down changes the denominator and metrics; return to the full range before quoting monthly values.

## Review and upload

- Watch the exported file from beginning to end with audio. Check text readability, both parts, absence of secrets, exact visible values and duration ≤10:00. Do not submit an unfinished/inaudible recording.
- Upload to your YouTube channel and choose **Unlisted** visibility. Suggested title: **Wind Desk — Customer Pilot and Technical Review**. No invented customer name, financial claim or real-time service claim is needed.
- Suggested description: “Historical GB wind forecast decision-support pilot using public Elexon WINDFOR and FUELHH WIND data. Part 1: customer demonstration. Part 2: architecture, correctness, testing and deployment. App: https://tme7d41m5t.vercel.app · Source: https://github.com/Mayank2142/tme7d41m5t”. Add chapter timestamps matching the final edit.
- Verify the final watch link in a logged-out/private window, including audio and the final seconds. Confirm it is unlisted rather than private.
- Add the **actual** video link and measured duration to README and the submission record. Keep the original file outside Git; generated recordings belong under ignored `output/` or another chosen private recording folder.
- Recheck the repository, app, video and final CI result, then submit through the company's actual requested channel. Do not submit before the video exists. No company submission URL/recipient has been supplied in this workspace.
