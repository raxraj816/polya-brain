import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect } from "vitest";
import { VerificationCard } from "../components/verification-card";
import type { TraceEvent } from "../lib/api";

let sequence = 0;
const event = (
  event_type: string,
  metadata: Record<string, unknown> = {},
  summary = event_type,
): TraceEvent => ({
  id: String(++sequence),
  sequence_number: sequence,
  engine_name: "verified_coding",
  event_type,
  reasoning_mode: "verify",
  summary,
  metadata,
  created_at: "2026-10-02T00:00:00Z",
});
const render = (events: TraceEvent[]) =>
  renderToStaticMarkup(createElement(VerificationCard, { events }));

describe("independent verification card", () => {
  it("is absent for ordinary investigations", () => {
    expect(render([event("cognitive_action_decision")])).toBe("");
  });
  it("shows live progress before a certificate exists", () => {
    const html = render([
      event("verified_coding_routed"),
      event("verified_coding_solved"),
      event(
        "verified_coding_differential",
        {},
        "Compared candidate with the independent reference on 3000 generated inputs; 1 disagreements.",
      ),
    ]);
    expect(html).toContain("Verifying");
    expect(html).toContain('class="done"');
    expect(html).toContain("3000 generated inputs");
  });
  it("shows the caught defect with the quoted requirement", () => {
    const html = render([
      event("verified_coding_routed"),
      event("verified_coding_solved"),
      event("verified_coding_differential"),
      event("verified_coding_ruling"),
      event("verified_coding_certificate", {
        certificate: {
          status: "repaired_and_verified",
          cases_compared: 3000,
          examples_sourced: 4,
          scale_seconds: [0.12],
          findings: [
            {
              round: 1,
              source: "differential",
              args: "([(1, 2), (2, 3)], 0)",
              candidate_output: "2",
              reference_output: "1",
              verdict: "candidate_wrong",
              expected: "1",
              governing_requirement:
                "must start at a time strictly greater than e + gap",
              resolved: true,
            },
          ],
        },
      }),
    ]);
    expect(html).toContain("Repaired and verified");
    expect(html).toContain("Caught before delivery");
    expect(html).toContain("([(1, 2), (2, 3)], 0)");
    expect(html).toContain("strictly greater than e + gap");
    expect(html).toContain("3,000");
  });
  it("never presents a disputed result as verified", () => {
    const html = render([
      event("verified_coding_routed"),
      event("verified_coding_certificate", {
        certificate: {
          status: "disputed",
          findings: [
            {
              round: 1,
              source: "differential",
              args: "(3,)",
              candidate_output: "1",
              reference_output: "2",
              verdict: "no_ruling",
              resolved: false,
            },
          ],
        },
      }),
    ]);
    expect(html).toContain("Not verified");
    expect(html).toContain("Unresolved");
    expect(html).not.toContain("Caught before delivery");
  });
});

describe("verifier self-corrections", () => {
  it("labels a corrected reference without blaming the draft", () => {
    const html = render([
      event("verified_coding_routed"),
      event("verified_coding_certificate", {
        certificate: {
          status: "verified",
          cases_compared: 3000,
          findings: [
            {
              round: 1,
              source: "stated_example",
              args: "csv_fields('a,b')",
              candidate_output: "['a', 'b']",
              reference_output: "['a', 'b', '']",
              verdict: "reference_wrong",
              expected: "['a', 'b']",
              governing_requirement: "csv_fields('a,b')==['a','b']",
              resolved: true,
            },
          ],
        },
      }),
    ]);
    expect(html).toContain("Verifier corrected its own reference");
    expect(html).not.toContain("Caught before delivery");
    expect(html).not.toContain("First draft returned");
  });
});
