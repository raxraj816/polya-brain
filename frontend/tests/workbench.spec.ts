import { test, expect } from "@playwright/test";

test("three real sessions, persisted history, artifacts, export and mobile layout", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("Service connected")).toBeVisible();
  for (const [problem, result] of [
    ["What is 17 * 6?", "102"],
    ["What is 84 / 7?", "12"],
    ["What is 125 + 75?", "200"],
  ]) {
    await page.getByRole("button", { name: "New investigation" }).click();
    await page.getByLabel("What are you trying to solve?").fill(problem);
    await page
      .getByRole("button", { name: "Start investigation", exact: true })
      .click();
    await expect(page.locator(".conclusion")).toContainText(result, {
      timeout: 30000,
    });
    await expect(page.locator(".verification-line")).toContainText("passed");
    const url = page.url();
    await page.getByRole("tab", { name: /Evidence/ }).click();
    await expect(page.getByText("Evidence register")).toBeVisible();
    await expect(page.locator(".evidence-card").first()).toContainText(result);
    await page.getByRole("tab", { name: "Hypotheses", exact: true }).click();
    await expect(page.locator(".hypothesis").first()).toBeVisible();
    await page.getByRole("tab", { name: /Trace/ }).click();
    await expect(page.locator(".trace-list li").first()).toBeVisible();
    await page.reload();
    await expect(page.locator(".conclusion")).toContainText(result);
    await expect(page).toHaveURL(url);
  }
  await page.getByLabel("incomplete", { exact: true }).check();
  await page
    .getByLabel(/What should we keep or correct/)
    .fill("Add a boundary case before using this in production.");
  await page.getByRole("button", { name: "Save feedback" }).click();
  await expect(page.getByText("Saved for manual review")).toBeVisible();
  await page.reload();
  await page.getByText(/Previous feedback/).click();
  await expect(
    page.getByText("Add a boundary case before using this in production."),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Report", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: /Evidence/ })).toBeFocused();
  await page.keyboard.press("Home");
  await expect(
    page.getByRole("tab", { name: "Report", exact: true }),
  ).toBeFocused();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export report" }).click();
  expect((await download).suggestedFilename()).toMatch(/polyabrain-.*\.md/);
  await page.screenshot({
    path: "../runs/workbench/report-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "../runs/workbench/report-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "New investigation" }).click();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "../runs/workbench/home-desktop.png",
    fullPage: true,
  });
});

test("keyboard tabs and unavailable backend are understandable", async ({
  page,
}) => {
  await page.route("**/api/backend/api/v1/sessions*", (route) =>
    route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "The investigation service is unavailable.",
      }),
    }),
  );
  await page.goto("/");
  await expect(page.getByText("History unavailable.")).toBeVisible();
  await page
    .getByLabel("What are you trying to solve?")
    .fill("What is 17 * 6?");
  await page
    .getByRole("button", { name: "Start investigation", exact: true })
    .click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "The investigation service is unavailable." }),
  ).toBeVisible();
});

test("proxy rejects cross-origin mutations and non-JSON form submissions", async ({
  request,
}) => {
  const forbidden = await request.post("/api/backend/api/v1/sessions", {
    headers: { origin: "https://untrusted.example" },
    data: { raw_input: "What is 4 + 4?" },
  });
  expect(forbidden.status()).toBe(403);
  const form = await request.post("/api/backend/api/v1/sessions", {
    headers: { "content-type": "text/plain" },
    data: '{"raw_input":"What is 4 + 4?"}',
  });
  expect(form.status()).toBe(415);
});

test("a paused investigation restores questions and records clarification across reloads", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("What are you trying to solve?").fill("Fix it.");
  await page
    .getByRole("button", { name: "Start investigation", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Help close the information gap." }),
  ).toBeVisible();
  const url = page.url();
  await page.reload();
  await expect(page.locator(".clarification")).toContainText(
    "Which system, artifact, or decision should PolyaBrain investigate?",
  );
  await page
    .getByLabel("Add the missing details and describe the complete objective")
    .fill("The checkout API");
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await expect(page.locator(".clarification")).toContainText(
    "What target should change, and which measurable outcome or constraint defines success?",
  );
  await page.reload();
  await expect(page).toHaveURL(url);
  await expect(page.locator(".clarification")).toContainText(
    "which measurable outcome",
  );
  await page.getByRole("tab", { name: /Trace/ }).click();
  await expect(page.locator(".trace-list")).toContainText(
    "Received user clarification",
  );
});
