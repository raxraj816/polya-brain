import { cpSync } from "node:fs";
// Next standalone output intentionally leaves static files for the deployer.
cpSync(
  new URL("../.next/static", import.meta.url),
  new URL("../.next/standalone/.next/static", import.meta.url),
  { recursive: true },
);
process.env.HOSTNAME = "127.0.0.1";
process.env.PORT ||= "3010";
await import("../.next/standalone/server.js");
