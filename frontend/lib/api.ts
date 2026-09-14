export type Session = {
  id: string;
  raw_input: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  confidence: number | null;
  verification_status: string | null;
  mode: string;
};
export type Evidence = {
  id?: string;
  source_type: string;
  source_uri: string | null;
  claim: string;
  raw_excerpt?: string | null;
  reliability_score: number | null;
  relevance_score: number | null;
  supports_hypothesis_ids?: string[];
  contradicts_hypothesis_ids?: string[];
};
export type Report = {
  session_id: string;
  final_conclusion: string | null;
  confidence_level: string;
  verification_status: string;
  evidence_used: Evidence[];
  evidence_against: Evidence[];
  checks_performed: string[];
  failed_checks: string[];
  contradictions: string[];
  open_questions: string[];
  recommended_next_action: string;
  audit_trace_path: string;
  reflection: Record<string, unknown> | null;
};
export type Hypothesis = {
  id: string;
  statement: string;
  mechanism: string | null;
  confidence: number | null;
  status: string;
  expected_signals: string[];
  verification_checks: string[];
  falsification_criteria: string[];
  selection_rationale: string | null;
};
export type Artifacts = {
  evidence: Evidence[];
  hypotheses: Hypothesis[];
  gaps: { description: string; filled: boolean }[];
  structured_problem: Record<string, unknown> | null;
};
export type TraceEvent = {
  id: string;
  sequence_number: number;
  engine_name: string;
  event_type: string;
  reasoning_mode: string;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};
export type History = {
  sessions: Session[];
  has_more: boolean;
  next_offset: number | null;
};
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const payload = await response.json();
  if (!response.ok)
    throw new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : `Request failed (${response.status}). Check the input and refresh the session.`,
    );
  return payload as T;
}
export async function trace(id: string): Promise<TraceEvent[]> {
  const events: TraceEvent[] = [];
  let cursor: number | undefined;
  for (;;) {
    const page = await api<{
      events: TraceEvent[];
      has_more: boolean;
      next_after_sequence: number | null;
    }>(
      `api/v1/sessions/${id}/events?limit=500${cursor === undefined ? "" : `&after_sequence=${cursor}`}`,
    );
    events.push(...page.events);
    if (!page.has_more || page.next_after_sequence === null) return events;
    if (cursor !== undefined && page.next_after_sequence <= cursor)
      throw new Error("Trace pagination did not advance. Refresh to retry.");
    cursor = page.next_after_sequence;
  }
}
export function sourceLink(
  value: string | null | undefined,
): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
export function reportMarkdown(session: Session, report: Report): string {
  const list = (title: string, items: string[]) =>
    `\n## ${title}\n\n${items.length ? items.map((item) => `- ${item}`).join("\n") : "None recorded."}\n`;
  const evidence = (items: Evidence[]) =>
    items.map((e) => `${e.claim}\n  Source: ${e.source_uri || e.source_type}`);
  return (
    `# PolyaBrain investigation\n\n${session.raw_input}\n\nSession: ${session.id}\n\nVerification: ${report.verification_status}\nConfidence: ${report.confidence_level}\n\n## Conclusion\n\n${report.final_conclusion || "No conclusion recorded."}\n` +
    list("Evidence used", evidence(report.evidence_used)) +
    list("Evidence against", evidence(report.evidence_against)) +
    list("Checks performed", report.checks_performed) +
    list("Failed checks", report.failed_checks) +
    list("Contradictions", report.contradictions) +
    list("Open questions", report.open_questions) +
    `\n## Next action\n\n${report.recommended_next_action}\n\nAudit trace: ${report.audit_trace_path}\n`
  );
}
export const words = (value: string) => value.replaceAll("_", " ");
