import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createInterface } from "node:readline";
import { test, expect } from "@playwright/test";

test("browser reconnects after backend death without replaying the investigation", async ({
  page,
  request,
}, testInfo) => {
  test.skip(
    process.env.POLYABRAIN_PROCESS_LOSS_BROWSER !== "1",
    "requires disposable PostgreSQL and dedicated backend/proxy ports",
  );
  test.setTimeout(90000);
  const root = resolve("..");
  const output = testInfo.outputPath("processes");
  mkdirSync(output, { recursive: true });
  const children: ChildProcessWithoutNullStreams[] = [];
  const env = {
    ...process.env,
    PYTHONPATH: resolve(root, "backend"),
    OPENROUTER_API_KEY: "",
    OPENROUTER_MODEL: "",
    SEARCH_API_KEY: "",
    SEARCH_PROVIDER: "",
  };
  async function start(kind: string, ...args: string[]) {
    const process = spawn(
      resolve(root, ".venv/bin/python"),
      [
        resolve(root, "backend/tests/fixtures/remote_completion_worker.py"),
        kind,
        output,
        ...args,
      ],
      { cwd: root, env },
    );
    children.push(process);
    const label = `${kind}-${children.length}`;
    let stderr = "";
    process.stderr.on("data", (chunk) => {
      stderr += String(chunk);
      writeFileSync(resolve(output, `${label}.stderr`), stderr);
    });
    const messages: Record<string, string>[] = [];
    let waiting: ((value: Record<string, string>) => void) | undefined;
    createInterface({ input: process.stdout }).on("line", (line) => {
      const value = JSON.parse(line);
      if (waiting) {
        const deliver = waiting;
        waiting = undefined;
        deliver(value);
      } else messages.push(value);
    });
    const next = () =>
      messages.length
        ? Promise.resolve(messages.shift()!)
        : new Promise<Record<string, string>>((done, fail) => {
            const timer = setTimeout(
              () => fail(new Error(`No ${label} event: ${stderr}`)),
              12000,
            );
            waiting = (value) => {
              clearTimeout(timer);
              done(value);
            };
          });
    return { process, next, ready: await next() };
  }
  async function stop(process: ChildProcessWithoutNullStreams) {
    if (process.exitCode !== null || process.signalCode !== null) return;
    const exit = new Promise<void>((done) =>
      process.once("exit", () => done()),
    );
    process.kill("SIGKILL");
    await exit;
  }
  const owner = randomUUID();
  const port = process.env.POLYABRAIN_PROCESS_LOSS_PORT!;
  let runRequests = 0;
  page.on("request", (req) => {
    if (req.method() === "POST" && req.url().endsWith("/run")) runRequests++;
  });
  try {
    const provider = await start("provider");
    const backend = await start("http", provider.ready.url, owner, port);
    await expect
      .poll(async () => {
        try {
          return (await request.get("/api/backend/health")).status();
        } catch {
          return 0;
        }
      })
      .toBe(200);
    await page.goto("/");
    await expect(page.getByText("Service connected")).toBeVisible();
    await page
      .getByLabel("What are you trying to solve?")
      .fill("What is 17 * 6?");
    await page
      .getByRole("button", { name: "Start investigation", exact: true })
      .click();
    expect(await provider.next()).toEqual({ event: "accepted" });
    await stop(backend.process);
    await expect(
      page.getByRole("alert").filter({ hasText: "could not be confirmed" }),
    ).toBeVisible();
    const sessionUrl = page.url();
    expect(sessionUrl).toContain("?session=");
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Cannot connect to the workbench" }),
    ).toBeVisible({ timeout: 20000 });
    await page.screenshot({
      path: testInfo.outputPath("backend-unavailable.png"),
      fullPage: true,
    });
    await start("http", provider.ready.url, owner, port);
    await expect
      .poll(async () => {
        try {
          return (await request.get("/api/backend/health")).status();
        } catch {
          return 0;
        }
      })
      .toBe(200);
    await page.getByRole("button", { name: "Retry connection" }).click();
    await expect(page.locator(".live-banner")).toContainText(
      "Awaiting a recorded outcome",
    );
    await expect(page.locator(".conclusion")).toContainText(
      "No verified conclusion",
    );
    await expect(page.locator(".detail-meta .verified")).toHaveCount(0);
    await expect(page.locator(".next-action")).toContainText(
      "refresh status before retrying",
    );
    await expect(page.locator(".detail-meta")).toContainText("outcome pending");
    writeFileSync(resolve(output, "release-provider"), "");
    expect(await provider.next()).toEqual({ event: "completed" });
    await page.reload();
    await expect(page).toHaveURL(sessionUrl);
    await expect(page.locator(".live-banner")).toBeVisible();
    await expect(page.locator(".conclusion")).toContainText(
      "No verified conclusion",
    );
    await page.screenshot({
      path: testInfo.outputPath("uncertain-after-restart.png"),
      fullPage: true,
    });
    const release = await start("release", owner);
    expect(release.ready.released).toBe(true);
    await expect(page.locator(".live-banner")).toHaveCount(0, {
      timeout: 10000,
    });
    await expect(page.locator(".verification-line")).toContainText(
      "operator stopped",
    );
    await expect(page.locator(".detail-meta .verified")).toHaveCount(0);
    await expect(page.locator(".next-action")).toContainText(
      "any provider activity",
    );
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export report" }).click();
    const download = await downloadPromise;
    expect(readFileSync((await download.path())!, "utf8")).toContain(
      "Verification: operator_stopped",
    );
    expect(readFileSync((await download.path())!, "utf8")).toContain(
      "does not establish external completion or cost",
    );
    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await expect(page.locator(".verification-line")).toContainText(
      "operator stopped",
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await page.screenshot({
      path: testInfo.outputPath("operator-stopped-mobile.png"),
      fullPage: true,
    });
    expect(runRequests).toBe(1);
    expect(
      readFileSync(resolve(output, "provider-dispatches.txt"), "utf8").trim(),
    ).toBe("accepted");
    expect(
      readFileSync(resolve(output, "provider-completions.txt"), "utf8").trim(),
    ).toBe("completed-after-worker-death");
  } finally {
    for (const process of children.reverse()) await stop(process);
  }
});
