import { describe, it, expect } from "vitest";
import {
  sourceLink,
  reportMarkdown,
  type Session,
  type Report,
} from "../lib/api";
describe("inspectable exports", () => {
  it("only links web sources and never executes source-supplied schemes", () => {
    expect(sourceLink("javascript:alert(1)")).toBeUndefined();
    expect(sourceLink("file:///private/input.py")).toBeUndefined();
    expect(sourceLink("https://example.com/evidence")).toBe(
      "https://example.com/evidence",
    );
  });
  it("exports contrary evidence, failed checks, uncertainty, and audit handle", () => {
    const result = reportMarkdown(
      { id: "example", raw_input: "Why did the check fail?" } as Session,
      {
        session_id: "example",
        reflection: null,
        final_conclusion: "Insufficient evidence.",
        confidence_level: "low",
        verification_status: "failed",
        evidence_used: [],
        evidence_against: [
          {
            claim: "Counterexample",
            source_uri: "https://example.com/check",
            source_type: "test",
            reliability_score: null,
            relevance_score: null,
          },
        ],
        checks_performed: ["Reproduction"],
        failed_checks: ["No reproduction"],
        contradictions: ["Conflicting logs"],
        open_questions: ["Which version?"],
        recommended_next_action: "Collect the version.",
        audit_trace_path: "/api/v1/sessions/example/events",
      } as Report,
    );
    for (const text of [
      "Counterexample",
      "No reproduction",
      "Conflicting logs",
      "Which version?",
      "/api/v1/sessions/example/events",
    ])
      expect(result).toContain(text);
  });
});
