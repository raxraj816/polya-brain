/** Transport ownership only: aborting a fetch does not cancel a backend run. */
export function deadline(milliseconds: number, parent: AbortSignal) {
  const controller = new AbortController();
  const abort = () => controller.abort(parent.reason);
  const timer = setTimeout(
    () =>
      controller.abort(
        new DOMException("Proxy deadline exceeded", "TimeoutError"),
      ),
    milliseconds,
  );
  parent.addEventListener("abort", abort, { once: true });
  if (parent.aborted) abort();
  return {
    signal: controller.signal,
    abort: (reason?: unknown) => controller.abort(reason),
    dispose: () => {
      clearTimeout(timer);
      parent.removeEventListener("abort", abort);
    },
  };
}

export class BodyLimitError extends Error {}

export async function readBody(
  body: ReadableStream<Uint8Array> | null,
  signal: AbortSignal,
  limit: number,
): Promise<Buffer<ArrayBuffer>> {
  signal.throwIfAborted();
  if (!body) return Buffer.alloc(0);
  const reader = body.getReader();
  const cancel = () => {
    void reader.cancel(signal.reason).catch(() => {});
  };
  signal.addEventListener("abort", cancel, { once: true });
  const parts: Uint8Array[] = [];
  let bytes = 0;
  try {
    for (;;) {
      signal.throwIfAborted();
      const { done, value } = await reader.read();
      signal.throwIfAborted();
      if (done) return Buffer.concat(parts);
      bytes += value.byteLength;
      if (bytes > limit) {
        void reader.cancel().catch(() => {});
        throw new BodyLimitError("Proxy body limit exceeded");
      }
      parts.push(value);
    }
  } finally {
    signal.removeEventListener("abort", cancel);
    reader.releaseLock();
  }
}
