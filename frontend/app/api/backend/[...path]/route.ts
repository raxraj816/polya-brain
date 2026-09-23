import { NextRequest, NextResponse } from "next/server";
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
  try {
    if (publicOrigin) {
      const status = await fetch(
        new URL("api/v1/auth/session", base.replace(/\/$/, "") + "/"),
        { cache: "no-store", redirect: "error" },
      );
      if (!status.ok || (await status.json()).required !== true)
        return NextResponse.json(
          {
            detail:
              "Public workbench requires authenticated backend configuration.",
          },
          { status: 503 },
        );
    }
    const parts: Uint8Array[] = [];
    let bytes = 0;
    if (request.method !== "GET" && request.body) {
      const reader = request.body.getReader();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > 120000) {
          await reader.cancel();
          break;
        }
        parts.push(value);
      }
    }
    const body = request.method === "GET" ? undefined : Buffer.concat(parts);
    if (bytes > 120000)
      return NextResponse.json(
        { detail: "Request exceeds the local input limit." },
        { status: 413 },
      );
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
    return new Response(response.body, { status: response.status, headers });
  } catch {
    return NextResponse.json(
      {
        detail:
          "The investigation service is unavailable. Check the backend connection, then refresh the session before retrying an action.",
      },
      { status: 502 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
