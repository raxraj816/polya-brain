"use client";
import { useState, useRef, type Dispatch, type SetStateAction } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FlaskConical } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
export type SourceInput = {
  source_code: string;
  check_code: string;
  execution_approved: boolean;
  provider_approved: boolean;
};
export function SourceCheckInput({
  value,
  onChange,
}: {
  value: SourceInput;
  onChange: Dispatch<SetStateAction<SourceInput>>;
}) {
  const [error, setError] = useState<string | null>(null);
  const reads = useRef({ source_code: 0, check_code: 0 });
  const availability = useQuery({
    queryKey: ["source-check-availability"],
    queryFn: () =>
      api<{ available: boolean; reason: string }>("api/v1/source-check"),
  });
  async function read(
    file: File | undefined,
    key: "source_code" | "check_code",
  ) {
    setError(null);
    const version = ++reads.current[key];
    onChange((previous) => ({
      ...previous,
      [key]: "",
      execution_approved: false,
      provider_approved: false,
    }));
    if (!file) return;
    try {
      if (!file.name.toLowerCase().endsWith(".py") || file.size > 18000)
        throw new Error("Select a UTF-8 Python file of at most 18 KB.");
      const text = new TextDecoder("utf-8", {
        fatal: true,
        ignoreBOM: true,
      }).decode(await file.arrayBuffer());
      if (!text.trim()) throw new Error("The selected file is empty.");
      if (reads.current[key] !== version) return;
      onChange((previous) => ({
        ...previous,
        [key]: text,
        execution_approved: false,
        provider_approved: false,
      }));
    } catch (e) {
      if (reads.current[key] !== version) return;
      setError(
        e instanceof Error ? e.message : "Could not read the selected file.",
      );
    }
  }
  return (
    <section className="source-input">
      <div className="eyebrow">
        Experimental · one source file and one check
      </div>
      <p>
        The check must define <code>verify(implementation)</code> and use
        assertions to test the supplied Python module. Only the Python standard
        library is available.
      </p>
      <div className="source-files">
        <label>
          Python source
          <input
            type="file"
            accept=".py"
            onChange={(e) => void read(e.target.files?.[0], "source_code")}
          />
        </label>
        <label>
          Regression check
          <input
            type="file"
            accept=".py"
            onChange={(e) => void read(e.target.files?.[0], "check_code")}
          />
        </label>
      </div>
      {error && (
        <p role="alert" className="source-error">
          {error}
        </p>
      )}
      {availability.isPending ? (
        <p>Checking local sandbox availability…</p>
      ) : availability.isError ? (
        <p role="alert">
          Cannot check the backend’s source/check configuration.
        </p>
      ) : !availability.data?.available ? (
        <p className="source-error">{availability.data?.reason}</p>
      ) : (
        <p>{availability.data.reason}</p>
      )}
      <label className="source-consent">
        <input
          type="checkbox"
          checked={value.execution_approved && value.provider_approved}
          disabled={
            !availability.data?.available ||
            !value.source_code ||
            !value.check_code
          }
          onChange={(e) =>
            onChange({
              ...value,
              execution_approved: e.target.checked,
              provider_approved: e.target.checked,
            })
          }
        />
        <span>
          Send these selected files to the configured model provider and run
          their check in the isolated sandbox. I have removed credentials and
          private data I do not want to submit.
        </span>
      </label>
      <p className="muted">
        Snapshots are retained in this local workspace database. PolyaBrain
        proposes a diff; it does not edit your original files. A passing
        supplied check does not prove general correctness or safety against
        adversarial code.
      </p>
    </section>
  );
}
type Candidate = {
  patch: string;
  verification_status: string;
  source_sha256: string;
  check_sha256: string;
  scope: string;
};
export function CandidatePanel({
  sessionId,
  running,
}: {
  sessionId: string;
  running: boolean;
}) {
  const review = useQuery({
    queryKey: ["candidate", sessionId],
    queryFn: () =>
      api<{
        source_check: boolean;
        candidate: Candidate | null;
        questions: string[];
      }>(`api/v1/sessions/${sessionId}/candidate`),
    refetchInterval: running ? 1500 : false,
  });
  if (review.isError)
    return (
      <p role="alert" className="muted">
        Candidate review unavailable: {review.error.message}
      </p>
    );
  if (!review.data?.source_check) return null;
  const candidate = review.data.candidate;
  function download() {
    if (!candidate) return;
    const url = URL.createObjectURL(
      new Blob([candidate.patch], { type: "text/plain;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `polyabrain-${sessionId}.patch`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <section className="candidate-panel">
      <div className="panel-heading">
        <h2>
          <FlaskConical size={17} /> Candidate edit
        </h2>
        {candidate && (
          <Button variant="outline" size="sm" onClick={download}>
            <Download size={14} /> Download diff
          </Button>
        )}
      </div>
      {candidate ? (
        <>
          <p className="candidate-verdict">
            {candidate.verification_status === "passed"
              ? "The original failed and this candidate passed the supplied check."
              : "This candidate has not passed verification. Do not treat it as a confirmed fix."}
          </p>
          <pre>{candidate.patch}</pre>
          <p className="muted">{candidate.scope}</p>
          <details>
            <summary>Inspect snapshot hashes</summary>
            <p>
              Source: <code>{candidate.source_sha256}</code>
            </p>
            <p>
              Check: <code>{candidate.check_sha256}</code>
            </p>
          </details>
        </>
      ) : (
        <p className="muted">{review.data.questions.join(" ")}</p>
      )}
    </section>
  );
}
