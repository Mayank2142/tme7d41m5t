// Standalone Playwright library smoke gate; no external data calls or test framework.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const base = new URL(process.env.GRID_BROWSER_BASE_URL ?? "http://127.0.0.1:8000");
const output = path.resolve(process.env.GRID_BROWSER_OUTPUT ?? "../output/playwright/phase-6");
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: process.env.GRID_BROWSER_CHANNEL || undefined });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  acceptDownloads: true,
});
// Headless Chromium may deny clipboard access by default. This journey tests
// successful copying with explicit, origin-scoped permission; denied copying
// and its manual fallback are covered by References.test.tsx.
await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: base.origin });
await context.tracing.start({ screenshots: true, snapshots: true });
const page = await context.newPage();
page.setDefaultTimeout(20_000);
const errors = [];
const requests = [];
const downloads = [];
let passed = false;
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});
await context.route("**/*", async (route) => {
  const url = new URL(route.request().url());
  if (url.origin === base.origin || ["data:", "blob:"].includes(url.protocol))
    await route.continue();
  else {
    errors.push(`Unexpected external request: ${url.origin}`);
    await route.abort();
  }
});
page.on("request", (request) => {
  const url = new URL(request.url());
  if (url.pathname.startsWith("/api/v1/")) requests.push(url.pathname);
});
const responseFor = (endpoint) =>
  page.waitForResponse(
    (response) => new URL(response.url()).pathname === `/api/v1/${endpoint}` && response.ok(),
  );
const shown = (text) => page.getByText(text, { exact: true }).first().waitFor({ state: "visible" });
const csvButton = () => page.getByRole("button", { name: "Download CSV" });
const metric = (label) =>
  page
    .locator("article.metric")
    .filter({ has: page.getByRole("heading", { name: label, exact: true }) });
const formatted = (value) =>
  new Intl.NumberFormat("en-GB", { minimumFractionDigits: 0, maximumFractionDigits: 1 }).format(
    value,
  );
async function screenshot(filename) {
  // Keep off-screen fixed skip links outside a full-page capture after auto-scrolling.
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(output, filename), fullPage: true });
}
async function download(result) {
  const pending = page.waitForEvent("download");
  await csvButton().click();
  const file = await pending;
  assert.equal(await file.failure(), null);
  const destination = path.join(output, file.suggestedFilename());
  await file.saveAs(destination);
  const bytes = await readFile(destination);
  const response = await fetch(new URL(result.export_url, base));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("x-analysis-context-id"), result.analysis_context_id);
  assert.equal(response.headers.get("x-dataset-release"), result.context.release_id);
  assert.ok(response.headers.get("content-type").startsWith("text/csv"));
  assert.deepEqual(bytes, Buffer.from(await response.arrayBuffer()));
  downloads.push({
    filename: file.suggestedFilename(),
    bytes: bytes.length,
    sha256: createHash("sha256").update(bytes).digest("hex"),
    context_id: result.analysis_context_id,
  });
}
try {
  let pending = responseFor("decision-view");
  await page.goto(base.href);
  const first = await (await pending).json();
  await shown("24 / 24");
  await page.waitForFunction(() => {
    const image = document.querySelector(".wind-scene-image");
    return image instanceof HTMLImageElement && image.complete && image.naturalWidth > 0;
  });
  const compactHeader = page.getByRole("button", { name: "Compact header" });
  const initialUrl = page.url();
  const initialRequests = requests.length;
  await compactHeader.click();
  assert.equal(await compactHeader.getAttribute("aria-pressed"), "true");
  assert.equal(page.url(), initialUrl);
  assert.equal(requests.length, initialRequests);
  await compactHeader.click();
  assert.equal(await compactHeader.getAttribute("aria-pressed"), "false");
  assert.equal(first.context.decision_from, "2026-01-31");
  assert.equal(first.analysis.window.delivery_date, "2026-02-01");
  assert.equal(first.analysis.points[0].forecast.generation_mw, 10099);
  await page.waitForURL((url) => url.searchParams.get("release_id") === first.context.release_id);
  assert.ok(!requests.includes("/api/v1/accuracy"), "Decision fetched retrospective actuals");
  const analysisReferences = page.getByRole("region", { name: "About this analysis" });
  assert.equal(await analysisReferences.locator("code").count(), 0);
  const analysisReferenceButton = analysisReferences.getByRole("button", {
    name: "View references",
  });
  await analysisReferenceButton.click();
  let referenceDialog = page.getByRole("dialog", { name: "About this analysis" });
  await referenceDialog.waitFor({ state: "visible" });
  assert.equal(
    await referenceDialog.getByText(first.analysis_context_id, { exact: true }).count(),
    1,
  );
  await referenceDialog.getByRole("button", { name: "Copy analysis id" }).click();
  await referenceDialog.getByText("Analysis ID copied", { exact: true }).waitFor();
  assert.equal(
    await page.evaluate(() => navigator.clipboard.readText()),
    first.analysis_context_id,
  );
  await referenceDialog.getByRole("button", { name: "Close references" }).focus();
  await page.keyboard.press("Shift+Tab");
  assert.equal(
    await referenceDialog.evaluate((dialog) => dialog.contains(document.activeElement)),
    true,
  );
  await page.screenshot({ path: path.join(output, "analysis-references-desktop.png") });
  await page.keyboard.press("Escape");
  await referenceDialog.waitFor({ state: "detached" });
  assert.equal(
    await analysisReferenceButton.evaluate((button) => document.activeElement === button),
    true,
  );
  await page.getByLabel("Desk cutoff · GMT").fill("09:45");
  await shown("Unapplied changes");
  assert.equal(await csvButton().isDisabled(), true);
  assert.equal(new URL(page.url()).searchParams.get("cutoff_local"), "09:00");
  pending = responseFor("decision-view");
  await page.getByRole("button", { name: "Apply selection" }).click();
  const later = await (await pending).json();
  await page.waitForURL((url) => url.searchParams.get("cutoff_local") === "09:45");
  await shown("15m");
  assert.equal(later.analysis.points[0].forecast.generation_mw, 10474);
  assert.equal(later.analysis.points[0].forecast.publication_utc, "2026-01-31T09:30:00Z");
  const slider = page.getByRole("slider").first();
  await slider.focus();
  await slider.press("Home");
  assert.match(await slider.getAttribute("aria-valuetext"), /10,474 MW/);
  await slider.press("ArrowRight");
  await page.waitForFunction(() => document.querySelector('input[type="range"]').value === "1");
  assert.match(await slider.getAttribute("aria-valuetext"), /10,117 MW/);
  await download(later);
  await screenshot("decision-desktop.png");

  pending = responseFor("accuracy");
  await page
    .getByRole("navigation", { name: "Workspace views" })
    .getByRole("link", { name: "Forecast accuracy" })
    .click();
  const accuracy = await (await pending).json();
  await shown("744 / 744 paired targets");
  const values = accuracy.analysis.metrics;
  for (const [label, value] of [
    ["Mean absolute error", values.mae_mw],
    ["Root mean square error", values.rmse_mw],
    ["P90 absolute error", values.p90_absolute_error_mw],
  ]) {
    assert.ok((await metric(label).textContent()).includes(formatted(value)));
  }
  assert.ok((await metric("Signed bias").textContent()).includes(`+${formatted(values.bias_mw)}`));
  await download(accuracy);
  await screenshot("accuracy-desktop.png");
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await page.waitForFunction(() => document.documentElement.scrollWidth <= window.innerWidth);
    assert.equal(
      await page
        .locator(".metric-value")
        .evaluateAll((elements) =>
          elements.every((element) => element.scrollWidth <= element.clientWidth),
        ),
      true,
    );
  }
  await screenshot("accuracy-mobile.png");
  const table = page.getByRole("region", { name: "Daily accuracy", exact: true });
  await table.focus();
  await table.press("ArrowRight");
  await page.waitForFunction(
    () => document.querySelector('section[aria-label="Daily accuracy"]').scrollLeft > 0,
  );
  assert.equal(await table.evaluate((element) => document.activeElement === element), true);

  pending = responseFor("accuracy");
  await table.getByRole("link", { name: "1 Jan ↗", exact: true }).click();
  const daily = await (await pending).json();
  await shown("24 / 24 paired targets");
  assert.equal(daily.context.decision_from, "2026-01-01");
  assert.equal(daily.context.decision_to, "2026-01-01");
  pending = responseFor("data-quality");
  await page
    .getByRole("navigation", { name: "Workspace views" })
    .getByRole("link", { name: "Data & methodology" })
    .click();
  const quality = await (await pending).json();
  await page.getByRole("link", { name: "Open Elexon response ↗" }).first().waitFor();
  assert.equal(await page.getByRole("link", { name: "Open Elexon response ↗" }).count(), 10);
  assert.equal(quality.release_id, first.context.release_id);
  await page
    .getByRole("img", { name: "Wind turbines on green coastal hills" })
    .scrollIntoViewIfNeeded();
  await page.waitForFunction(() => {
    const image = document.querySelector(".wind-story img");
    return image instanceof HTMLImageElement && image.complete && image.naturalWidth > 0;
  });
  const sourceReferences = page.getByRole("button", { name: /^View references for/ });
  assert.equal(await sourceReferences.count(), 10);
  await sourceReferences.first().click();
  referenceDialog = page.getByRole("dialog");
  await referenceDialog.waitFor({ state: "visible" });
  assert.equal(
    await referenceDialog.getByText(quality.raw_batches[0].payload_sha256, { exact: true }).count(),
    1,
  );
  await referenceDialog.getByRole("button", { name: "Copy response checksum" }).click();
  await referenceDialog.getByText("Response checksum copied", { exact: true }).waitFor();
  await page.screenshot({ path: path.join(output, "source-references-desktop.png") });
  await page.getByRole("button", { name: "Close references" }).click();
  await referenceDialog.waitFor({ state: "detached" });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 860 });
    await sourceReferences.first().click();
    referenceDialog = page.getByRole("dialog");
    await referenceDialog.waitFor({ state: "visible" });
    assert.equal(
      await referenceDialog.evaluate((dialog) => dialog.scrollWidth <= dialog.clientWidth + 1),
      true,
    );
    const bounds = await referenceDialog.boundingBox();
    assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= width + 1);
    await page.screenshot({ path: path.join(output, `source-references-${width}.png`) });
    await page.keyboard.press("Escape");
    await referenceDialog.waitFor({ state: "detached" });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await screenshot("methodology-desktop.png");
  await page
    .getByRole("navigation", { name: "Workspace views" })
    .getByRole("link", { name: "Forecast accuracy" })
    .click();
  await shown("24 / 24 paired targets");
  assert.equal(new URL(page.url()).searchParams.get("decision_from"), "2026-01-01");
  await page.reload();
  await shown("24 / 24 paired targets");
  await page.emulateMedia({ reducedMotion: "reduce" });
  assert.equal(
    await page
      .locator(".wind-scene-image")
      .evaluate((image) => getComputedStyle(image).animationName),
    "none",
  );
  assert.equal(
    await page.locator(".scroll-progress").evaluate((bar) => getComputedStyle(bar).display),
    "none",
  );
  await page.emulateMedia({ reducedMotion: "no-preference" });
  assert.deepEqual(errors, []);
  passed = true;
  const report = {
    passed,
    base_url: base.href,
    release_id: first.context.release_id,
    downloads,
    console_errors: errors,
    viewports: [1440, 390, 320],
    checks: [
      "cutoff draft/apply and source eligibility",
      "forecast-only decision requests",
      "self-hosted wind imagery loads and compact header preserves the analysis",
      "keyboard chart inspection",
      "exact browser CSV bytes",
      "four API-derived metrics",
      "daily drill-down",
      "pinned provenance and reload",
      "compact reference dialogs, exact IDs, copy controls, modal focus and Escape",
      "reference dialogs fit 390/320-pixel screens",
      "reduced motion disables photographic reveal and scroll decoration",
      "narrow layout and keyboard table focus",
    ],
  };
  await writeFile(path.join(output, "browser-report.json"), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
} finally {
  if (!passed)
    await page
      .screenshot({ path: path.join(output, "failure.png"), fullPage: true })
      .catch(() => {});
  await context.tracing.stop(passed ? {} : { path: path.join(output, "failure-trace.zip") });
  await context.close();
  await browser.close();
}
