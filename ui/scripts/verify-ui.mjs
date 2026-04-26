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
  const credentials = {
    admin: { label: /Admin/i, email: "admin@vnn-lab.edu.vn", path: "/admin/ops" },
    editor: { label: /^Editor/i, email: "editor@vnn-lab.edu.vn", path: "/editor/dashboard" },
    "data-scientist": { label: /Data Scientist/i, email: "scientist@vnn-lab.edu.vn", path: "/scientist/monitoring" },
  }[role];
  await page.getByRole("button", { name: credentials.label }).click();
  await page.getByLabel(/Work email/i).fill(credentials.email);
  await page.getByLabel(/Password/i).fill("vnn-password");
  await page.getByRole("button", { name: /^Enter workspace$/ }).click();
  const expectedPath = credentials.path;
  await page.waitForURL(`**${expectedPath}`);
  recordCheck(`login:${role}`, true, expectedPath);
}

async function signOut(page) {
  await page.getByRole("button", { name: /Account menu/i }).click();
  await page.getByRole("menuitem", { name: /Sign out/i }).click();
  await page.waitForURL(`${baseUrl}/`);
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

    await login(page, "editor");
    await expectText(page, "Import article");
    await expectText(page, "Editorial queue");
    await screenshot(page, "02-editor-dashboard");
    assert.equal(await page.getByRole("link", { name: /Admin Ops/i }).count(), 0, "Editor sidebar should not expose Admin Ops");

    if (await page.getByRole("link", { name: /^Open story$/ }).count()) {
      await page.getByRole("link", { name: /^Open story$/ }).first().click();
      await page.waitForURL("**/editor/review/**");
      await expectText(page, "Prediction summary");
      await screenshot(page, "03-article-review");
    } else {
      recordCheck("article-review:empty-queue", true, "No article review attempted because the queue is empty");
    }

    await page.getByRole("link", { name: /Review Queue/i }).click();
    await page.waitForURL("**/editor/review");
    await expectText(page, "Open review stories");
    await screenshot(page, "04-review-queue");

    await page.getByRole("link", { name: /Label Review/i }).click();
    await page.waitForURL("**/editor/classifier");
    await expectText(page, "Classified stories");
    await screenshot(page, "05-label-review");
    if (await page.getByRole("link", { name: /^Inspect$/ }).count()) {
      await page.getByRole("link", { name: /^Inspect$/ }).first().click();
      await page.waitForURL("**/editor/review/**");
      await expectText(page, "Source URL");
      await expectText(page, "Run inference");
      await expectText(page, "Flag to DS");
      await screenshot(page, "05b-article-review-from-labels");
    }

    await signOut(page);

    await login(page, "admin");
    await page.getByRole("link", { name: /Admin Ops/i }).click();
    await page.waitForURL("**/admin/ops");
    await expectText(page, "Users & permissions");
    await expectText(page, "Create user");
    await expectText(page, "Preview impact");
    assert.ok(await page.getByRole("button", { name: /^Edit$/ }).count(), "Admin users table should expose row edit actions");
    await page.getByRole("button", { name: /Preview impact/i }).click();
    await expectText(page, "Auto-ready");
    await expectText(page, "Page 1 of");
    assert.equal(await page.getByRole("link", { name: /Review Queue/i }).count(), 0, "Admin sidebar should not expose editor review queue");
    await screenshot(page, "06-admin-ops");

    await signOut(page);

    await login(page, "data-scientist");
    await expectText(page, "Macro F1 over time");
    await expectText(page, "Per-label F1");
    await expectText(page, "Overall confusion matrix");
    await expectText(page, "Per-class metrics");
    await page.getByRole("button", { name: /^Recompute$/ }).click();
    await page.getByText(/(Completed|Skipped|Failed) monitoring_recompute job/i).first().waitFor({ timeout: 15000 });
    await screenshot(page, "07-model-monitoring");

    await page.getByRole("link", { name: /Model Versions/i }).click();
    await page.waitForURL("**/scientist/versions");
    await expectText(page, "Uploaded runs");
    await expectText(page, "Upload artifacts");
    await expectText(page, "Required upload package");
    await expectText(page, "config.json");
    await expectText(page, "label_config.json");
    await expectText(page, "Set as active");
    await expectText(page, "Page 1 of");
    await screenshot(page, "08-model-versions");

    await page.getByRole("link", { name: /Dataset Lab/i }).click();
    await page.waitForURL("**/scientist/dataset");
    await expectText(page, "Hard samples");
    await expectText(page, "Page 1 of");
    await expectText(page, "Active learning loop");
    await screenshot(page, "09-dataset-lab");

    await page.getByRole("link", { name: /Model Versions/i }).click();
    await page.waitForURL("**/scientist/versions");
    await expectText(page, "Uploaded runs");
    recordCheck("model-versions:page-loaded", true, "Model Versions page loaded without assuming a seeded run");

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
