import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { expect, it } from "vitest";
import { deadline, readBody } from "../lib/proxy-transfer";

it.each(["headers", "body"])(
  "native fetch closes the real upstream socket on a %s deadline",
  async (stage) => {
    let calls = 0;
    let closed = false;
    const server = createServer((_request, response) => {
      calls++;
      response.on("close", () => {
        closed = true;
      });
      if (stage === "body") {
        response.writeHead(200, { "content-type": "application/json" });
        response.write('{"status":');
      }
    });
    await new Promise<void>((resolve) =>
      server.listen(0, "127.0.0.1", resolve),
    );
    const transfer = deadline(100, new AbortController().signal);
    try {
      const operation = async () => {
        const response = await fetch(
          `http://127.0.0.1:${(server.address() as AddressInfo).port}`,
          { signal: transfer.signal },
        );
        await readBody(response.body, transfer.signal, 1024);
      };
      await expect(operation()).rejects.toMatchObject({ name: "TimeoutError" });
      await expect.poll(() => closed).toBe(true);
      expect(calls).toBe(1);
    } finally {
      transfer.abort();
      transfer.dispose();
      server.closeAllConnections();
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
  },
);
