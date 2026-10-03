import type { TraceEvent } from "../lib/api";

type Finding = {
  round: number;
  source: string;
  args: string;
  candidate_output: string;
  reference_output: string;
  verdict: string;
  expected?: string;
  governing_requirement?: string;
  explanation?: string;
  resolved?: boolean;
};

type Certificate = {
  status: string;
  entrypoint?: string;
  own_tests_passed?: boolean;
  own_test_count?: number;
  examples_sourced?: number;
  cases_compared?: number;
  sizes_covered?: number[];
  scale_seconds?: number[];
  scale_timeouts?: number;
  findings?: Finding[];
  assumptions?: string[];
  open_question?: string;
};

const STATUS: Record<string, { label: string; tone: string; note: string }> = {
  verified: {
    label: "Verified",
    tone: "ok",
    note: "The first draft agreed with an independent reference everywhere it was tested.",
  },
  repaired_and_verified: {
    label: "Repaired and verified",
    tone: "ok",
    note: "Independent checking caught a defect in the first draft before delivery. The repaired code was re-verified from scratch.",
  },
  disputed: {
    label: "Not verified: disputed",
    tone: "warn",
    note: "An unresolved disagreement remains. Treat the delivered code as unverified.",
  },
  ambiguous_specification: {
    label: "Not verified: ambiguous requirement",
    tone: "warn",
    note: "Your problem statement does not determine the answer for a concrete input.",
  },
  unverified: {
    label: "Not verified",
    tone: "warn",
    note: "No independent check could be established; only the solver's own assertions ran.",
  },
  no_candidate: {
    label: "No implementation",
    tone: "warn",
    note: "The solver produced no implementation within its budget.",
  },
};

const STEPS: [string, (types: Set<string>) => boolean][] = [
  [
    "Solve",
    (t) =>
      t.has("verified_coding_solved") ||
      t.has("verified_coding_solve_incomplete"),
  ],
  [
    "Independent oracle",
    (t) =>
      t.has("verified_coding_differential") ||
      t.has("verified_coding_oracle_rejected"),
  ],
  ["Differential test", (t) => t.has("verified_coding_differential")],
  [
    "Adjudicate",
    (t) =>
      t.has("verified_coding_ruling") ||
      t.has("verified_coding_ruling_rejected"),
  ],
  ["Certify", (t) => t.has("verified_coding_certificate")],
];

function draftDefect(f: Finding) {
  return (
    ["candidate_wrong", "both_wrong", "performance_repair"].includes(
      f.verdict,
    ) ||
    (f.source === "mutation" && !!f.resolved && f.verdict !== "both_acceptable")
  );
}

function sourceLabel(source: string) {
  if (source === "stated_example") return "Example stated in your problem";
  if (source === "differential") return "Generated input";
  if (source === "regression") return "Previously found input";
  if (source === "scale") return "Input at your stated limits";
  if (source === "mutation") return "Input mutation";
  return source;
}

export function VerificationCard({ events }: { events: TraceEvent[] }) {
  if (!events.some((e) => e.event_type === "verified_coding_routed"))
    return null;
  const types = new Set(events.map((e) => e.event_type));
  const final = events.findLast(
    (e) => e.event_type === "verified_coding_certificate",
  );
  const certificate = final?.metadata.certificate as Certificate | undefined;
  const status = certificate ? STATUS[certificate.status] : undefined;
  const latestCompare = events.findLast(
    (e) => e.event_type === "verified_coding_differential",
  );
  return (
    <section
      className="verification-card"
      aria-label="Independent verification"
    >
      <header>
        <div>
          <div className="eyebrow">Lean-first independent verification</div>
          <h2 className={status ? `verdict ${status.tone}` : "verdict"}>
            {status ? status.label : "Verifying…"}
          </h2>
          <p>
            {status
              ? status.note
              : "PolyaBrain solves once, then tests the result against an independently written reference before delivering it."}
          </p>
        </div>
        <ol className="verify-steps">
          {STEPS.map(([label, done]) => (
            <li key={label} className={done(types) ? "done" : ""}>
              <i />
              {label}
            </li>
          ))}
        </ol>
      </header>
      {certificate ? (
        <>
          <div className="verify-metrics">
            <span>
              <strong>
                {(certificate.cases_compared ?? 0).toLocaleString()}
              </strong>
              generated inputs compared
            </span>
            <span>
              <strong>{certificate.examples_sourced ?? 0}</strong>
              examples from your problem
            </span>
            <span>
              <strong>{certificate.findings?.length ?? 0}</strong>
              {certificate.findings?.length === 1 ? "finding" : "findings"}
            </span>
            {certificate.scale_seconds?.length ? (
              <span>
                <strong>
                  {Math.max(...certificate.scale_seconds).toFixed(2)}s
                </strong>
                slowest run at stated limits
              </span>
            ) : null}
          </div>
          {certificate.findings?.map((f, i) => (
            <article
              key={i}
              className={
                !f.resolved
                  ? "finding open"
                  : draftDefect(f)
                    ? "finding resolved"
                    : "finding corrected"
              }
            >
              <div className="finding-head">
                <span>
                  {!f.resolved
                    ? "Unresolved"
                    : draftDefect(f)
                      ? "Caught before delivery"
                      : "Verifier corrected its own reference"}
                </span>
                <span>{sourceLabel(f.source)}</span>
              </div>
              {f.source !== "scale" && (
                <dl>
                  <dt>Input</dt>
                  <dd>
                    <code>{f.args}</code>
                  </dd>
                  <dt>
                    {draftDefect(f) ? "First draft returned" : "Draft returned"}
                  </dt>
                  <dd>
                    <code>{f.candidate_output}</code>
                  </dd>
                  {f.expected ? (
                    <>
                      <dt>Correct result</dt>
                      <dd>
                        <code>{f.expected}</code>
                      </dd>
                    </>
                  ) : (
                    <>
                      <dt>Independent reference returned</dt>
                      <dd>
                        <code>{f.reference_output}</code>
                      </dd>
                    </>
                  )}
                </dl>
              )}
              {f.governing_requirement ? (
                <blockquote>
                  <span>Your requirement</span>“{f.governing_requirement}”
                </blockquote>
              ) : null}
              {f.explanation ? <p>{f.explanation}</p> : null}
            </article>
          ))}
          {certificate.open_question ? (
            <p className="verify-question">
              <strong>Question for you:</strong> {certificate.open_question}
            </p>
          ) : null}
          {certificate.assumptions?.length ? (
            <details>
              <summary>Interpretations the verifier assumed</summary>
              <ul>
                {certificate.assumptions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </>
      ) : latestCompare ? (
        <p className="muted">{latestCompare.summary}</p>
      ) : null}
    </section>
  );
}
