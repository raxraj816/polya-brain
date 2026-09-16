import { test, expect } from "@playwright/test";

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
    page.getByRole("link", { name: "Sign in", exact: true }),
  ).toBeVisible();
  expect(
    (await context.request.get("/api/backend/api/v1/sessions")).status(),
  ).toBe(401);
  await page.getByRole("link", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Test identity provider" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Alice", exact: true }).click();
  await expect(
    page.getByText("Private workspace", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Service connected")).toBeVisible();
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
    page.getByRole("link", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Sign in", exact: true }).click();
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
