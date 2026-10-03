import { test, expect } from "@playwright/test";

const signInLabel =
  process.env.OIDC_REGISTRATION_MODE === "self_service"
    ? "Sign in or create account"
    : "Sign in";

test("OIDC browser login, private history, logout and account switching", async ({
  browser,
}) => {
  test.skip(
    process.env.POLYABRAIN_TEST_AUTH !== "1",
    "requires loopback OIDC integration fixture",
  );
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
  });
  const page = await context.newPage();
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: signInLabel, exact: true }),
  ).toBeVisible();
  expect(
    (await context.request.get("/api/backend/api/v1/sessions")).status(),
  ).toBe(401);
  await page.getByRole("link", { name: signInLabel, exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Test identity provider" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Alice", exact: true }).click();
  await expect(
    page.getByText("Private workspace", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Service connected")).toBeVisible();
  await expect(page.locator(".usage-allowance")).toContainText(
    "runs available today",
  );
  await page
    .getByLabel("What are you trying to solve?")
    .fill("What is 19 * 7?");
  await page
    .getByRole("button", { name: "Start investigation", exact: true })
    .click();
  await expect(page.locator(".conclusion")).toContainText("133", {
    timeout: 30000,
  });
  const privateUrl = page.url();
  const sessionId = new URL(privateUrl).searchParams.get("session");
  const cookies = await context.cookies();
  const sessionCookie = cookies.find((c) => c.name === "polya_session")!;
  expect(sessionCookie.httpOnly).toBe(true);
  expect(sessionCookie.sameSite).toBe("Lax");
  await page.reload();
  await expect(page.locator(".conclusion")).toContainText("133");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("link", { name: signInLabel, exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: signInLabel, exact: true }).click();
  await page.getByRole("button", { name: "Bob", exact: true }).click();
  await expect(
    page.getByText("Private workspace", { exact: true }),
  ).toBeVisible();
  expect(
    (
      await context.request.get(
        `/api/backend/api/v1/sessions/${sessionId}/report`,
      )
    ).status(),
  ).toBe(404);
  const history = await (
    await context.request.get("/api/backend/api/v1/sessions")
  ).json();
  expect(history.sessions.some((s: { id: string }) => s.id === sessionId)).toBe(
    false,
  );
  await page.goto(privateUrl);
  await expect(page.locator(".conclusion")).toHaveCount(0);
  await expect(
    page.getByText("Problem session not found.", { exact: false }).first(),
  ).toBeVisible();
  await context.close();
});

test("OIDC browser write limits preserve unsaved input and existing reports", async ({
  browser,
}) => {
  test.skip(
    process.env.POLYABRAIN_TEST_AUTH !== "1" ||
      process.env.POLYABRAIN_TEST_WRITE_LIMITS !== "1",
    "requires fresh OIDC fixture with user session/feedback limits of one",
  );
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
  });
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("link", { name: signInLabel, exact: true }).click();
  await page.getByRole("button", { name: "Bob", exact: true }).click();
  await page
    .getByLabel("What are you trying to solve?")
    .fill("What is 17 * 6?");
  await page
    .getByRole("button", { name: "Start investigation", exact: true })
    .click();
  await expect(page.locator(".conclusion")).toContainText("102");
  const savedUrl = page.url();
  await page.getByRole("button", { name: "Save feedback" }).click();
  await expect(page.getByText("Saved for manual review")).toBeVisible();
  const correction = page.getByLabel(/What should we keep or correct/);
  await correction.fill("Keep this unsaved correction.");
  const deniedFeedback = page.waitForResponse(
    (r) => r.url().endsWith("/feedback") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Save feedback" }).click();
  const feedbackResponse = await deniedFeedback;
  expect(feedbackResponse.status()).toBe(429);
  expect(Number(feedbackResponse.headers()["retry-after"])).toBeGreaterThan(0);
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "daily feedback creation allowance" }),
  ).toBeVisible();
  await expect(correction).toHaveValue("Keep this unsaved correction.");
  await expect(page.locator(".conclusion")).toContainText("102");
  await page.getByRole("button", { name: "New investigation" }).click();
  const draft = page.getByLabel("What are you trying to solve?");
  await draft.fill("Keep this unsubmitted investigation.");
  const deniedCreate = page.waitForResponse(
    (r) => r.url().endsWith("/sessions") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Start investigation", exact: true })
    .click();
  expect((await deniedCreate).status()).toBe(429);
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "daily session creation allowance" }),
  ).toBeVisible();
  await expect(draft).toHaveValue("Keep this unsubmitted investigation.");
  const history = await (
    await context.request.get("/api/backend/api/v1/sessions")
  ).json();
  expect(history.sessions).toHaveLength(1);
  await page.goto(savedUrl);
  await expect(page.locator(".conclusion")).toContainText("102");
  await context.close();
});
