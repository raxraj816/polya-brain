import { type TraceEvent } from "@/lib/api";
const stages = [
  ["Understand", ["interpret"]],
  ["Constraints", ["discover_constraints"]],
  ["Gaps", ["detect_gaps"]],
  ["Evidence", ["calculate", "research", "retrieve", "inspect"]],
  ["Hypotheses", ["hypothesize", "plan"]],
  ["Execute", ["execute"]],
  ["Verify", ["verify"]],
  ["Reflect", ["reflect"]],
] as const;
export function RunOverview({ events }: { events: TraceEvent[] }) {
  const usage = events.filter(
    (e) => e.event_type === "cognitive_resource_usage",
  );
  const actions = new Set(usage.map((e) => e.metadata.action_type));
  const sum = (key: string) =>
    usage.reduce(
      (n, e) =>
        n +
        (typeof e.metadata[key] === "number" ? (e.metadata[key] as number) : 0),
      0,
    );
  const hasMeasurements = usage.some(
    (e) => typeof e.metadata.model_calls === "number",
  );
  const reflected = events.some((e) =>
    ["reflection_recorded", "verified_reflection_recorded"].includes(
      e.event_type,
    ),
  );
  return (
    <section
      className="run-overview"
      aria-label="Recorded investigation activity"
    >
      <div className="stage-strip">
        {stages.map(([label, types]) => {
          const recorded =
            types.some((t) => actions.has(t)) ||
            (label === "Reflect" && reflected);
          return (
            <span
              key={label}
              className={recorded ? "recorded" : ""}
              title={
                recorded
                  ? "Activity recorded; inspect trace for its outcome."
                  : "No separate action recorded."
              }
            >
              <i />
              {label}
            </span>
          );
        })}
      </div>
      <div className="resource-strip">
        {hasMeasurements ? (
          <>
            <span>
              <strong>{sum("model_calls")}</strong> model calls
            </span>
            <span>
              <strong>
                {(sum("input_tokens") + sum("output_tokens")).toLocaleString()}
              </strong>{" "}
              tokens recorded
            </span>
            <span>
              <strong>{(sum("duration_ms") / 1000).toFixed(2)}s</strong> active
              time
            </span>
            <span>
              <strong>{sum("external_calls")}</strong> external calls
            </span>
          </>
        ) : (
          <span>Resource measurements appear as capabilities finish.</span>
        )}
        <details>
          <summary>About these measurements</summary>
          <p>
            Stage markers indicate recorded activity, not successful completion.
            Some capabilities combine stages. Totals sum resource events in this
            session; they exclude time spent waiting for your input. Provider
            billing may differ from recorded token usage.
          </p>
        </details>
      </div>
    </section>
  );
}
