import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";

test("persisted citation rejections stay unverified in report, trace, export and reload", async ({
  page,
}) => {
  test.skip(
    !process.env.POLYABRAIN_CITATION_CASES,
    "requires isolated persisted citation fixtures",
  );
  const cases: {
    id: string;
    name: string;
    passed: boolean;
    candidate: string;
  }[] = JSON.parse(
    readFileSync(process.env.POLYABRAIN_CITATION_CASES!, "utf8"),
  ).cases;
  for (const fixture of cases) {
    await page.goto(`/?session=${fixture.id}`);
    await expect(page.locator(".verification-line strong")).toHaveText(
      fixture.passed ? "passed" : "failed",
    );
    if (!fixture.passed) {
      await expect(page.locator(".conclusion")).toContainText(
        "No verified conclusion is available.",
      );
      await expect(page.locator(".conclusion")).not.toContainText("37 ticks");
      await expect(page.locator(".detail-meta .badge")).toHaveText(
        "run finished",
      );
      await expect(page.locator(".detail-meta .verified")).toHaveCount(0);
      await expect(
        page
          .getByText(
            fixture.name === "unadmitted_source"
              ? /Citation has no admitted source/
              : /Citation section is absent/,
          )
          .first(),
      ).toBeVisible();
      await expect(page.locator(".next-action")).toContainText(
        "acquire the missing source passage",
      );
      const downloading = page.waitForEvent("download");
      await page.getByRole("button", { name: "Export report" }).click();
      const download = await downloading;
      const markdown = readFileSync((await download.path())!, "utf8");
      expect(markdown).toContain("Verification: failed");
      expect(markdown).toContain("No verified conclusion is available.");
      expect(markdown).toContain("then independently verify again");
      expect(markdown).not.toContain(fixture.candidate);
      await page.getByRole("tab", { name: /Trace/ }).click();
      await expect(page.locator(".trace-list")).toContainText(
        "Citation provenance failed.",
      );
      await page.reload();
      await page.getByRole("tab", { name: "Report", exact: true }).click();
      await expect(page.locator(".conclusion")).toContainText(
        "No verified conclusion is available.",
      );
      await page.setViewportSize({ width: 390, height: 844 });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      await page.screenshot({
        path: `../runs/workbench/citation-${fixture.name}-mobile.png`,
        fullPage: true,
      });
      await page.setViewportSize({ width: 1440, height: 1000 });
    } else {
      await expect(page.locator(".conclusion")).toContainText("37 ticks");
      await expect(page.locator(".conclusion a")).toHaveAttribute(
        "href",
        /#section-6\.4\.1$/,
      );
      await expect(page.locator(".detail-meta .verified")).toBeVisible();
    }
  }
});
