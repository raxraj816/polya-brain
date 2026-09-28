import { describe, it, expect } from "vitest";
import {
  sourceLink,
  reportMarkdown,
  problemTitle,
  type Session,
  type Report,
} from "../lib/api";
describe("inspectable exports", () => {
  it("keeps short questions intact and bounds long Unicode headings", () => {
    expect(problemTitle("What is 17 * 6?")).toBe("What is 17 * 6?");
    expect(problemTitle("Explain\n  the error.")).toBe("Explain the error.");
    const title = problemTitle("🧠".repeat(200));
    expect(Array.from(title)).toHaveLength(140);
    expect(title).toBe("🧠".repeat(139) + "…");
  });
  it("only links web sources and never executes source-supplied schemes", () => {
    expect(sourceLink("javascript:alert(1)")).toBeUndefined();
    expect(sourceLink("file:///private/input.py")).toBeUndefined();
    expect(sourceLink("https://example.com/evidence")).toBe(
      "https://example.com/evidence",
    );
  });
  it("exports contrary evidence, failed checks, uncertainty, and audit handle", () => {
    const original =
      "Why did the check fail?\n\n" + "Keep every constraint. ".repeat(30);
    expect(problemTitle(original).length).toBeLessThan(original.length);
    const result = reportMarkdown(
      { id: "example", raw_input: original } as Session,
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
    expect(result).toContain(original);
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
