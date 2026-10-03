import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "../app/api/backend/[...path]/route";
import { api } from "../lib/api";

const session = "11111111-1111-4111-8111-111111111111";
const context = (path: string) => ({
  params: Promise.resolve({ path: path.split("/") }),
});
const request = (path: string, options: RequestInit = {}) =>
  new NextRequest(`http://localhost:3010/api/backend/${path}`, {
    ...options,
    signal: options.signal ?? undefined,
    headers: {
      host: "localhost:3010",
      "content-type": "application/json",
      ...options.headers,
    },
  });

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubEnv("POLYABRAIN_PUBLIC_ORIGIN", "");
  vi.stubEnv("POLYABRAIN_API_URL", "http://127.0.0.1:8000");
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

function stalledFetch() {
  return vi.fn(
    (_url: unknown, options?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        options?.signal?.addEventListener(
          "abort",
          () => reject(options.signal!.reason),
          { once: true },
        );
      }),
  );
}

it("bounds a stalled read and does not retry it in the proxy", async () => {
  const fetcher = stalledFetch();
  vi.stubGlobal("fetch", fetcher);
  let result: Response | undefined;
  void GET(request("health"), context("health")).then((value) => {
    result = value;
  });
  await vi.advanceTimersByTimeAsync(30_001);
  expect(result?.status).toBe(504);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(await result!.json()).toMatchObject({
    detail: expect.stringContaining("Refresh"),
  });
});

it.each(["run", "respond"])(
  "allows long %s work but never replays an ambiguous mutation",
  async (action) => {
    const path = `api/v1/sessions/${session}/${action}`;
    const fetcher = stalledFetch();
    vi.stubGlobal("fetch", fetcher);
    let result: Response | undefined;
    void POST(
      request(path, { method: "POST", body: "{}" }),
      context(path),
    ).then((value) => {
      result = value;
    });
    await vi.advanceTimersByTimeAsync(30_001);
    expect(result).toBeUndefined();
    await vi.advanceTimersByTimeAsync(300_000);
    expect(result?.status).toBe(504);
    expect(await result!.json()).toMatchObject({
      detail: expect.stringContaining("Work may still be running or saved"),
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  },
);

function partialBody(initial = '{"status":') {
  let controller: ReadableStreamDefaultController<Uint8Array>;
  const cancel = vi.fn();
  const body = new ReadableStream<Uint8Array>({
    start(value) {
      controller = value;
      value.enqueue(new TextEncoder().encode(initial));
    },
    cancel,
  });
  return {
    body,
    cancel,
    send: (value: string) =>
      controller.enqueue(new TextEncoder().encode(value)),
  };
}

it("keeps the total deadline across headers and trickling body bytes", async () => {
  const partial = partialBody();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(partial.body)),
  );
  let result: Response | undefined;
  void GET(request("health"), context("health")).then((value) => {
    result = value;
  });
  await vi.advanceTimersByTimeAsync(20_000);
  expect(result).toBeUndefined();
  partial.send('"ok"');
  await vi.advanceTimersByTimeAsync(10_001);
  expect(result?.status).toBe(504);
  expect(partial.cancel).toHaveBeenCalledOnce();
  expect(vi.getTimerCount()).toBe(0);
});

it.each(["headers", "body"])(
  "auth preflight times out at %s without dispatching the action",
  async (stage) => {
    vi.stubEnv("POLYABRAIN_PUBLIC_ORIGIN", "http://localhost:3010");
    const fetcher =
      stage === "headers"
        ? stalledFetch()
        : vi.fn(async () => new Response(partialBody().body));
    vi.stubGlobal("fetch", fetcher);
    let result: Response | undefined;
    const path = `api/v1/sessions/${session}/run`;
    void POST(
      request(path, {
        method: "POST",
        body: "{}",
        headers: { origin: "http://localhost:3010" },
      }),
      context(path),
    ).then((value) => {
      result = value;
    });
    await vi.advanceTimersByTimeAsync(10_001);
    expect(result?.status).toBe(504);
    expect(fetcher).toHaveBeenCalledOnce();
    expect(String(fetcher.mock.calls[0][0])).toContain("auth/session");
    expect(vi.getTimerCount()).toBe(0);
  },
);

it("does not forward a stalled upload and cancels its reader", async () => {
  const partial = partialBody();
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  let result: Response | undefined;
  const path = "api/v1/sessions";
  void POST(
    request(path, {
      method: "POST",
      body: partial.body,
      duplex: "half",
    } as RequestInit),
    context(path),
  ).then((value) => {
    result = value;
  });
  await vi.advanceTimersByTimeAsync(10_001);
  expect(result?.status).toBe(504);
  expect(fetcher).not.toHaveBeenCalled();
  expect(partial.cancel).toHaveBeenCalledOnce();
});

it.each([true, false])(
  "propagates disconnect without retry (already aborted: %s)",
  async (alreadyAborted) => {
    const controller = new AbortController();
    const fetcher = stalledFetch();
    vi.stubGlobal("fetch", fetcher);
    const path = `api/v1/sessions/${session}/run`;
    if (alreadyAborted) controller.abort();
    const pending = POST(
      request(path, { method: "POST", body: "{}", signal: controller.signal }),
      context(path),
    );
    await vi.advanceTimersByTimeAsync(1);
    controller.abort();
    expect((await pending).status).toBe(499);
    expect(fetcher).toHaveBeenCalledTimes(alreadyAborted ? 0 : 1);
    expect(vi.getTimerCount()).toBe(0);
  },
);

it("aborts an unfinished response body on browser disconnect", async () => {
  const controller = new AbortController();
  const partial = partialBody();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(partial.body)),
  );
  const pending = GET(
    request("health", { signal: controller.signal }),
    context("health"),
  );
  await vi.advanceTimersByTimeAsync(1);
  controller.abort();
  expect((await pending).status).toBe(499);
  expect(partial.cancel).toHaveBeenCalledOnce();
});

it("streams incrementally and closes the upstream on consumer cancellation", async () => {
  const partial = partialBody("data: first\n\n");
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(partial.body, {
          headers: { "content-type": "text/event-stream" },
        }),
    ),
  );
  const path = `api/v1/sessions/${session}/events/stream`;
  const response = await GET(request(path), context(path));
  const reader = response.body!.getReader();
  expect(new TextDecoder().decode((await reader.read()).value)).toBe(
    "data: first\n\n",
  );
  await reader.cancel();
  await vi.advanceTimersByTimeAsync(1);
  expect(partial.cancel).toHaveBeenCalledOnce();
  expect(vi.getTimerCount()).toBe(0);
});

it("a stalled stream fails its reader at the total deadline", async () => {
  const partial = partialBody("data: first\n\n");
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(partial.body)),
  );
  const path = `api/v1/sessions/${session}/events/stream`;
  const response = await GET(request(path), context(path));
  const reader = response.body!.getReader();
  await reader.read();
  const failed = expect(reader.read()).rejects.toMatchObject({
    name: "TimeoutError",
  });
  await vi.advanceTimersByTimeAsync(330_001);
  await failed;
  expect(partial.cancel).toHaveBeenCalledOnce();
  expect(vi.getTimerCount()).toBe(0);
});

it("cancels a stream even when the consumer never reads", async () => {
  const partial = partialBody("data: first\n\n");
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(partial.body)),
  );
  const path = `api/v1/sessions/${session}/events/stream`;
  const response = await GET(request(path), context(path));
  await vi.advanceTimersByTimeAsync(330_001);
  expect(partial.cancel).toHaveBeenCalledOnce();
  await expect(response.text()).rejects.toMatchObject({ name: "TimeoutError" });
});

it("preserves cookies, redirects, status and retry-after and filters request cookies", async () => {
  const fetcher = vi.fn(
    async (_url: unknown, _options?: RequestInit) =>
      new Response(null, {
        status: 302,
        headers: {
          location: "https://identity.example/authorize",
          "set-cookie": "polya_oidc=opaque; HttpOnly",
          "retry-after": "7",
        },
      }),
  );
  vi.stubGlobal("fetch", fetcher);
  const path = "api/v1/auth/login";
  const response = await GET(
    request(path, {
      headers: {
        cookie: "polya_session=test; unrelated=hidden; __Host-polya_oidc=nonce",
      },
    }),
    context(path),
  );
  expect(response.status).toBe(302);
  expect(response.headers.get("location")).toBe(
    "https://identity.example/authorize",
  );
  expect(response.headers.getSetCookie()).toEqual([
    "polya_oidc=opaque; HttpOnly",
  ]);
  expect(response.headers.get("retry-after")).toBe("7");
  expect(response.headers.get("cache-control")).toBe("no-store");
  expect(new Headers(fetcher.mock.calls[0][1]?.headers).get("cookie")).toBe(
    "polya_session=test; __Host-polya_oidc=nonce",
  );
  expect(vi.getTimerCount()).toBe(0);
});

it.each([401, 429, 503])("preserves backend error %s", async (status) => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      Response.json(
        { detail: "Backend error" },
        { status, headers: { "retry-after": "30" } },
      ),
    ),
  );
  const response = await GET(request("health"), context("health"));
  expect(response.status).toBe(status);
  expect(await response.json()).toEqual({ detail: "Backend error" });
  expect(response.headers.get("retry-after")).toBe("30");
});

it("fails closed on a public backend that disables authentication", async () => {
  vi.stubEnv("POLYABRAIN_PUBLIC_ORIGIN", "http://localhost:3010");
  const fetcher = vi.fn(async () => Response.json({ required: false }));
  vi.stubGlobal("fetch", fetcher);
  expect((await GET(request("health"), context("health"))).status).toBe(503);
  expect(fetcher).toHaveBeenCalledOnce();
  expect(vi.getTimerCount()).toBe(0);
});

it("retains input limits and does not dispatch oversized actions", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const path = "api/v1/sessions";
  expect(
    (
      await POST(
        request(path, { method: "POST", body: "x".repeat(120_001) }),
        context(path),
      )
    ).status,
  ).toBe(413);
  expect(fetcher).not.toHaveBeenCalled();
  expect(vi.getTimerCount()).toBe(0);
});

it("rejects oversized responses and broken bodies without a successful partial response", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(new Uint8Array(16 * 1024 * 1024 + 1))),
  );
  expect((await GET(request("health"), context("health"))).status).toBe(502);
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          new ReadableStream({
            start(c) {
              c.error(new Error("broken connection"));
            },
          }),
        ),
    ),
  );
  expect((await GET(request("health"), context("health"))).status).toBe(502);
  expect(vi.getTimerCount()).toBe(0);
});

it.each(["network", "body"])(
  "client explains ambiguous %s failure without retry",
  async (stage) => {
    const fetcher = vi.fn(async () => {
      if (stage === "network") throw new TypeError("Failed to fetch");
      return new Response('{"status":');
    });
    vi.stubGlobal("fetch", fetcher);
    await expect(api(`api/v1/sessions/${session}/run`, {})).rejects.toThrow(
      "Refresh the session or history before retrying",
    );
    expect(fetcher).toHaveBeenCalledOnce();
  },
);
