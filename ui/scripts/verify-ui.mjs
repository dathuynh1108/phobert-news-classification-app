import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { chromium } from "playwright";

const baseUrl = process.env.UI_BASE_URL ?? "http://127.0.0.1:5173";
const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api";
const outDir = path.resolve(process.cwd(), "..", "tmp", "verify");

const summary = {
  baseUrl,
  pages: [],
  checks: [],
  consoleErrors: [],
  pageErrors: [],
};

async function screenshot(page, name) {
  const filePath = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: filePath });
  summary.pages.push(filePath);
}

function recordCheck(label, passed, detail) {
  summary.checks.push({ label, passed, detail });
}

async function setRange(locator, value) {
  await locator.evaluate((node, nextValue) => {
    const element = /** @type {HTMLInputElement} */ (node);
    element.value = String(nextValue);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
}

async function expectText(page, text) {
  await page.getByText(text, { exact: false }).first().waitFor();
}

async function login(page, role) {
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await expectText(page, "Login");
  if (role === "data-scientist") {
    await page.getByRole("button", { name: /Data Scientist/i }).click();
  } else {
    await page.getByRole("button", { name: /Editor \/ Admin/i }).click();
  }
  await page.getByRole("button", { name: /^Enter workspace$/ }).click();
  const expectedPath = role === "editor-admin" ? "/editor/dashboard" : "/scientist/monitoring";
  await page.waitForURL(`**${expectedPath}`);
  recordCheck(`login:${role}`, true, expectedPath);
}

async function main() {
  await mkdir(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1024 },
    colorScheme: "light",
  });
  const page = await context.newPage();

  page.on("console", (message) => {
    if (message.type() === "error") {
      summary.consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    summary.pageErrors.push(error.message);
  });

  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await screenshot(page, "01-login");

    await login(page, "editor-admin");
    await expectText(page, "Editorial queue");
    await screenshot(page, "02-editor-dashboard");

    await page.getByRole("link", { name: /^Open story$/ }).first().click();
    await page.waitForURL("**/editor/review/**");
    await expectText(page, "Prediction summary");
    await screenshot(page, "03-article-review");

    const inferenceResponse = page.waitForResponse((response) => response.url().includes("/infer") && response.ok());
    await page.getByRole("button", { name: /Run inference/i }).click();
    await inferenceResponse;
    await expectText(page, "Inference");
    recordCheck("article-review:run-inference", true, "Inference request completed");

    await page.getByRole("link", { name: /Admin Ops/i }).click();
    await page.waitForURL("**/editor/admin");
    await expectText(page, "Users & permissions");
    await screenshot(page, "04-admin-ops");

    await page.getByRole("button", { name: /Sign out/i }).click();
    await page.waitForURL(`${baseUrl}/`);

    await login(page, "data-scientist");
    await expectText(page, "Macro F1 over time");
    await screenshot(page, "05-model-monitoring");

    await page.getByRole("link", { name: /Model Versions/i }).click();
    await page.waitForURL("**/scientist/versions");
    await expectText(page, "Uploaded runs");
    await screenshot(page, "06-model-versions");

    await page.getByRole("link", { name: /Dataset Lab/i }).click();
    await page.waitForURL("**/scientist/dataset");
    await expectText(page, "Active learning loop");
    await screenshot(page, "07-dataset-lab");

    await page.getByRole("link", { name: /Model Versions/i }).click();
    await page.waitForURL("**/scientist/versions");
    const thresholdResponse = await fetch(`${apiBaseUrl}/admin/ops/thresholds`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_approve: 0.77, review_floor: 0.69 }),
    });
    assert.equal(thresholdResponse.ok, true, "Threshold update API failed");
    const thresholds = await (await fetch(`${apiBaseUrl}/admin/ops`)).json();
    assert.equal(thresholds.thresholds.auto_approve, 0.77, "Threshold auto_approve did not persist");
    assert.equal(thresholds.thresholds.review_floor, 0.69, "Threshold review_floor did not persist");
    recordCheck("admin-ops:threshold-persistence", true, "0.77 / 0.69 persisted in Postgres");

    const thresholdResetResponse = await fetch(`${apiBaseUrl}/admin/ops/thresholds`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_approve: 0.75, review_floor: 0.68 }),
    });
    assert.equal(thresholdResetResponse.ok, true, "Threshold reset API failed");
    recordCheck("admin-ops:threshold-reset", true, "Thresholds restored to seed defaults");

    const activateResponse = await fetch(`${apiBaseUrl}/scientist/model-versions/run_024/activate`, {
      method: "POST",
    });
    assert.equal(activateResponse.ok, true, "Activate model API failed");
    const versions = await (await fetch(`${apiBaseUrl}/scientist/model-versions`)).json();
    assert.equal(versions.chips[1].label, "PhoBERT package run_024", "Active model chip did not persist");
    recordCheck("model-versions:activation-persistence", true, "Active model persisted after API activation");

    assert.equal(summary.consoleErrors.length, 0, `Console errors detected: ${summary.consoleErrors.join(" | ")}`);
    assert.equal(summary.pageErrors.length, 0, `Page errors detected: ${summary.pageErrors.join(" | ")}`);
  } finally {
    await writeFile(path.join(outDir, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
