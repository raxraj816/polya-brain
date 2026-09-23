"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
type Feedback = {
  id: string;
  feedback_type: string;
  correction: string | null;
  created_at: string;
};
export function FeedbackPanel({ sessionId }: { sessionId: string }) {
  const cache = useQueryClient();
  const [kind, setKind] = useState("useful");
  const [correction, setCorrection] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const feedback = useQuery({
    queryKey: ["feedback", sessionId],
    queryFn: () => api<Feedback[]>(`api/v1/sessions/${sessionId}/feedback`),
  });
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api(`api/v1/sessions/${sessionId}/feedback`, {
        feedback_type: kind,
        correction: correction.trim() || null,
      });
      setCorrection("");
      setSaved(true);
      await cache.invalidateQueries({ queryKey: ["feedback", sessionId] });
      await cache.invalidateQueries({ queryKey: ["history"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Feedback could not be saved.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="feedback">
      <div className="panel-heading">
        <h2>
          <MessageSquare size={16} /> Did this investigation help?
        </h2>
      </div>
      <form onSubmit={submit}>
        <fieldset>
          <legend className="sr-only">Feedback type</legend>
          {["useful", "wrong", "incomplete", "unsafe"].map((value) => (
            <label key={value}>
              <input
                type="radio"
                name="feedback-kind"
                value={value}
                checked={kind === value}
                onChange={() => {
                  setKind(value);
                  setSaved(false);
                }}
              />
              {value}
            </label>
          ))}
        </fieldset>
        <label htmlFor="correction">
          What should we keep or correct?{" "}
          <span className="muted">(optional)</span>
        </label>
        <textarea
          id="correction"
          rows={3}
          maxLength={10000}
          value={correction}
          onChange={(e) => {
            setCorrection(e.target.value);
            setSaved(false);
          }}
          placeholder="Add missing evidence, a correction, or what made this useful."
        />
        <div className="feedback-actions">
          <Button variant="outline" size="sm" disabled={busy} type="submit">
            {busy ? "Saving…" : "Save feedback"}
          </Button>
          {saved && (
            <span role="status">
              <Check size={14} /> Saved for manual review
            </span>
          )}
        </div>
        {error && <p role="alert">{error}</p>}
      </form>
      <p className="muted feedback-note">
        Feedback is saved with this investigation. Corrections require review
        and do not become verified knowledge automatically.
      </p>
      {feedback.isError && (
        <p role="alert">Saved feedback could not be loaded.</p>
      )}
      {feedback.data?.length ? (
        <details>
          <summary>
            Previous feedback ({feedback.data.length}
            {feedback.data.length === 100 ? "+" : ""})
          </summary>
          {feedback.data.map((f) => (
            <article key={f.id}>
              <strong>{f.feedback_type}</strong>
              <time>{new Date(f.created_at).toLocaleString()}</time>
              {f.correction && <p>{f.correction}</p>}
            </article>
          ))}
        </details>
      ) : null}
    </section>
  );
}
