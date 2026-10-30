# Phase 8 publication and submission status

Prepared 30 October 2026. **In progress: public source published; remote CI verification running; own-voice video and final submission pending.** This record does not mark the whole assignment complete.

| Deliverable | Actual status |
| --- | --- |
| Public application | [Wind Desk](https://tme7d41m5t.vercel.app), verified in Phase 7 |
| Anonymous-name public repository | [Mayank2142/tme7d41m5t](https://github.com/Mayank2142/tme7d41m5t), published on `main` |
| CI | [Verify Wind Desk](https://github.com/Mayank2142/tme7d41m5t/actions/workflows/ci.yml), verification in progress |
| README | Startup, directory map, real app/source links, methodology and explicit AI disclosure included |
| Technical review | [Architecture/code map](ARCHITECTURE.md) and existing API/methodology/security/deployment evidence |
| Recording materials | Updated [spoken script](DEMO_SCRIPT.md) and [nine-minute recording checklist](RECORDING_CHECKLIST.md) |
| Required video | User chose their own voice; recording, unlisted upload and logged-out playback remain pending |
| Company submission | Pending video and final link checks; no submission destination or confirmation has been supplied |

## Publication review

The existing official GitHub CLI login was verified for the user's account. The new repository is public, with the requested anonymous name, a real application homepage and the reviewed source/history. The local development branch remains unchanged; its commits are pushed to remote `main` without rewriting history. No repository secret or hosted database credential was added to Actions.

Before the initial push, the publication check passed for the working tree and a separate review scanned all **7 reachable commits**, **220 unique blobs** and **216 text blobs**. No private-path or recognized credential findings were reported. The public Elexon archive, attributed fixture archive, illustrative WebP assets and dependency locks were the largest inputs. The assignment DOCX, secrets, generated output, local environments, tools and caches are ignored and absent from the published history. Commit identity uses the user's GitHub noreply email. Pattern scans and review do not prove that arbitrary unknown secrets cannot exist.

Workflow syntax validation passed. CI uses read-only permissions and no persisted checkout credentials; its jobs use an ephemeral local PostgreSQL service and the bundled public seed. Hosting credentials are unnecessary. Artifacts retain test, audit, browser and persistence evidence for seven days.

## Clean-runner isolation correction

The [first remote run](https://github.com/Mayank2142/tme7d41m5t/actions/runs/41093545827) exposed two PostgreSQL API tests that changed `app.state.database` but retained the application's original cached `DatasetReader`. A seeded local default database had masked this mistake. On the clean runner the reader reached an empty default schema and returned `SCHEMA_NOT_INITIALIZED`.

The corrected fixture binds both the health/metadata database and the analysis/provenance reader to the same isolated test engine. Its unused default engine points to an unreachable port, so accidental fallback fails even on a seeded developer machine. Local regression verification uses a newly created database with zero public tables and removes only that temporary database after testing. Runtime application code and the verified hosted deployment are unchanged by this test correction.

The [machine evidence](phase-8-evidence.json) records publication review, regression and actual remote results as they become available. A pending workflow is not a successful CI gate.

The corrected run's quality job passed all 107 backend and 47 frontend tests, lint, builds, dependency audits and wheel verification. Its container browser journey exposed a second test-environment assumption: headless Chromium denied clipboard access by default, while the application correctly offered manual copying. The browser gate now grants clipboard read/write permission only to its isolated test origin and verifies the actual copied analysis ID. The denied-permission/manual-copy behavior remains covered by the existing component test. This changes test setup, not the public site's permissions or application code; the complete container gate is being rerun.

## Final handoff and submission gate

Use the recording checklist to demonstrate the customer workflow for about 4½ minutes, then architecture, code and verification for about 4½ minutes. Keep each part below five minutes and the whole video at or below ten. The figures in the script require the applied 09:45 cutoff and full January range; daily drill-down changes the metrics.

After the user records their own voice, upload the finished file as **Unlisted** on YouTube and verify playback/audio/duration in a logged-out browser. Add the actual watch URL to README and this record. No placeholder URL, script or screenshot counts as the required video. Then recheck all public links and the latest CI result before submitting through the company's specified channel. Do not submit without the video.

Cumulative assignment effort has not been reconciled against the sixteen-hour limit. Client operational reliance remains subject to Phases 9–11, separately from this assignment's submission gate.
