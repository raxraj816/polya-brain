import { NextRequest, NextResponse } from "next/server";
import {
  BodyLimitError,
  deadline,
  readBody,
} from "../../../../lib/proxy-transfer";
export const dynamic = "force-dynamic";
export const maxDuration = 360;
const allowed =
  /^(health|api\/v1\/source-check|api\/v1\/usage|api\/v1\/auth\/(?:session|login|callback|logout)|api\/v1\/sessions(?:\/[0-9a-f-]{36}(?:\/(?:run|respond|report|artifacts|feedback|candidate|events(?:\/stream)?))?)?)$/;
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const host = request.headers.get("host") || "";
  const publicOrigin = process.env.POLYABRAIN_PUBLIC_ORIGIN;
  const expectedOrigin = publicOrigin || `${request.nextUrl.protocol}//${host}`;
  if (
    publicOrigin
      ? new URL(publicOrigin).host !== host
      : !/^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(host)
  )
    return NextResponse.json(
      { detail: "This host is not configured for the workbench." },
      { status: 403 },
    );
  const { path } = await context.params;
  const route = path.join("/");
  if (!allowed.test(route))
    return NextResponse.json({ detail: "Unknown API route." }, { status: 404 });
  const base = process.env.POLYABRAIN_API_URL || "http://127.0.0.1:8000";
  const url = new URL(
    route + request.nextUrl.search,
    base.replace(/\/$/, "") + "/",
  );
  if (request.method === "POST") {
    const origin = request.headers.get("origin");
    if ((publicOrigin && !origin) || (origin && origin !== expectedOrigin))
      return NextResponse.json(
        { detail: "Cross-origin actions are not allowed." },
        { status: 403 },
      );
    if (
      !request.headers
        .get("content-type")
        ?.toLowerCase()
        .startsWith("application/json")
    )
      return NextResponse.json(
        { detail: "Actions require JSON." },
        { status: 415 },
      );
  }
  const transfer = deadline(
    /\/(run|respond|events\/stream)$/.test(route) ? 330_000 : 30_000,
    request.signal,
  );
  let streaming = false;
  try {
    transfer.signal.throwIfAborted();
    if (publicOrigin) {
      const auth = deadline(10_000, transfer.signal);
      try {
        const status = await fetch(
          new URL("api/v1/auth/session", base.replace(/\/$/, "") + "/"),
          { cache: "no-store", redirect: "error", signal: auth.signal },
        );
        const payload = await readBody(status.body, auth.signal, 120_000);
        if (!status.ok || JSON.parse(payload.toString()).required !== true)
          return NextResponse.json(
            {
              detail:
                "Public workbench requires authenticated backend configuration.",
            },
            { status: 503 },
          );
      } finally {
        auth.abort();
        auth.dispose();
      }
    }
    let body: Buffer<ArrayBuffer> | undefined;
    if (request.method !== "GET") {
      const upload = deadline(10_000, transfer.signal);
      try {
        body = await readBody(request.body, upload.signal, 120_000);
      } catch (error) {
        if (error instanceof BodyLimitError)
          return NextResponse.json(
            { detail: "Request exceeds the local input limit." },
            { status: 413 },
          );
        throw error;
      } finally {
        upload.dispose();
      }
    }
    transfer.signal.throwIfAborted();
    const response = await fetch(url, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
        Accept: request.headers.get("accept") || "application/json",
        Cookie: (request.headers.get("cookie") || "")
          .split(";")
          .map((s) => s.trim())
          .filter((s) => /^(?:__Host-)?(polya_session|polya_oidc)=/.test(s))
          .join("; "),
        ...(request.headers.get("origin")
          ? { Origin: request.headers.get("origin")! }
          : {}),
      },
      body,
      cache: "no-store",
      redirect: "manual",
      signal: transfer.signal,
    });
    const headers = new Headers({
      "Content-Type":
        response.headers.get("content-type") || "application/json",
      "Cache-Control": "no-store",
      "X-Accel-Buffering": "no",
      "Referrer-Policy": "no-referrer",
    });
    for (const cookie of response.headers.getSetCookie())
      headers.append("Set-Cookie", cookie);
    const retryAfter = response.headers.get("retry-after");
    if (retryAfter) headers.set("Retry-After", retryAfter);
    const location = response.headers.get("location");
    if (location) {
      if (!/^api\/v1\/auth\/(login|callback)$/.test(route))
        throw new Error("Unexpected redirect");
      headers.set("Location", location);
    }
    if (route.endsWith("/events/stream") && response.body && response.ok) {
      let output: TransformStreamDefaultController<Uint8Array>;
      const channel = new TransformStream<Uint8Array, Uint8Array>({
        start(controller) {
          output = controller;
        },
      });
      // Unblock a pending write even if the downstream has stopped reading.
      const stop = () => output.error(transfer.signal.reason);
      transfer.signal.addEventListener("abort", stop, { once: true });
      if (transfer.signal.aborted) stop();
      void response.body
        .pipeTo(channel.writable, { signal: transfer.signal })
        .catch(() => {})
        .finally(() => {
          transfer.signal.removeEventListener("abort", stop);
          transfer.abort();
          transfer.dispose();
        });
      streaming = true;
      return new Response(channel.readable, {
        status: response.status,
        headers,
      });
    }
    const payload = await readBody(
      response.body,
      transfer.signal,
      16 * 1024 * 1024,
    );
    return new Response(
      [204, 205, 304].includes(response.status) ? null : payload,
      {
        status: response.status,
        headers,
      },
    );
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    return NextResponse.json(
      {
        detail: timedOut
          ? "The investigation service took too long to respond. Work may still be running or saved. Refresh the session or history before retrying an action."
          : "The investigation service response could not be confirmed. Work may still be running or saved. Refresh the session or history before retrying an action.",
      },
      { status: request.signal.aborted ? 499 : timedOut ? 504 : 502 },
    );
  } finally {
    if (!streaming) {
      transfer.abort();
      transfer.dispose();
    }
  }
}
export const GET = proxy;
export const POST = proxy;
