import { NextRequest, NextResponse } from "next/server";
export const dynamic = "force-dynamic";
export const maxDuration = 360;
const allowed =
  /^(health|api\/v1\/sessions(?:\/[0-9a-f-]{36}(?:\/(?:run|respond|report|artifacts|feedback|events(?:\/stream)?))?)?)$/;
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const host = request.headers.get("host") || "";
  if (!/^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(host))
    return NextResponse.json(
      { detail: "This workbench accepts localhost connections only." },
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
    if (origin && origin !== `${request.nextUrl.protocol}//${host}`)
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
    const body = request.method === "GET" ? undefined : await request.text();
    if (body && Buffer.byteLength(body) > 120000)
      return NextResponse.json(
        { detail: "Request exceeds the local input limit." },
        { status: 413 },
      );
    const response = await fetch(url, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
        Accept: request.headers.get("accept") || "application/json",
      },
      body,
      cache: "no-store",
      redirect: "error",
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
        "X-Accel-Buffering": "no",
      },
    });
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
