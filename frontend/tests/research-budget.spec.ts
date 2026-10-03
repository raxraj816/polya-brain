import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";

for (const scenario of [
  {
    name: "budget limit",
    session: process.env.POLYABRAIN_RESEARCH_STOP_SESSION,
    guidance: "could not fit the remaining run budget",
    retry: "No automatic retry or budget increase",
    summary: "Public research stopped",
  },
  {
    name: "unavailable route",
    session: process.env.POLYABRAIN_RESEARCH_UNAVAILABLE_SESSION,
    guidance: "no safe research route is currently available",
    retry: "No automatic retry was performed",
    summary: "Public evidence remains unresolved",
  },
]) {
  test(`public research ${scenario.name} explains the stop without requesting private input`, async ({
    page,
  }) => {
    test.skip(
      !scenario.session,
      "requires isolated persisted research-stop fixture",
    );
    let mutations = 0;
    page.on("request", (request) => {
      if (request.method() === "POST") mutations++;
    });
    await page.goto(`/?session=${scenario.session}`);
    await expect(page.locator(".conclusion")).toContainText(
      "without a verified conclusion",
    );
    await expect(page.locator(".verification-line strong")).toHaveText(
      "not verified",
    );
    await expect(page.locator(".detail-meta .verified")).toHaveCount(0);
    await expect(page.locator(".clarification")).toHaveCount(0);
    await expect(page.locator(".next-action")).toContainText(scenario.guidance);
    await expect(page.locator(".next-action")).toContainText(scenario.retry);
    await expect(
      page.getByText(
        "A relevant observation was retained, but coverage is incomplete.",
      ),
    ).toBeVisible();
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export report" }).click();
    const download = await downloadPromise;
    const markdown = readFileSync((await download.path())!, "utf8");
    expect(markdown).toContain("Verification: not_verified");
    expect(markdown).toContain(scenario.summary);
    expect(markdown).toContain("Which public observations support");
    await page.reload();
    await expect(page.locator(".next-action")).toContainText(scenario.summary);
    await expect(page.locator(".clarification")).toHaveCount(0);
    expect(mutations).toBe(0);
  });
}
