"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  Download,
  FileSearch,
  FlaskConical,
  History as HistoryIcon,
  LoaderCircle,
  Plus,
  Search,
  ShieldCheck,
  Waypoints,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  SourceCheckInput,
  CandidatePanel,
  type SourceInput,
} from "@/components/source-check";
import { RunOverview } from "@/components/run-overview";
import { FeedbackPanel } from "@/components/feedback";
import {
  api,
  trace,
  reportMarkdown,
  sourceLink,
  words,
  type Session,
  type History,
  type Report,
  type Artifacts,
  type Evidence,
} from "@/lib/api";

const tabs = ["Report", "Evidence", "Hypotheses", "Trace"] as const;
type Tab = (typeof tabs)[number];
function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}
function Items({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="report-section">
      <h3>{title}</h3>
      {items.length ? (
        <ul>
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">None recorded.</p>
      )}
    </section>
  );
}
function Source({ item }: { item: Evidence }) {
  const href = sourceLink(item.source_uri);
  return (
    <article className="evidence-card">
      <div className="eyebrow">{words(item.source_type)}</div>
      <p>{item.claim}</p>
      {item.source_uri && (
        <div className="source">
          {href ? (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {item.source_uri} <ArrowUpRight size={13} />
            </a>
          ) : (
            <code>{item.source_uri}</code>
          )}
        </div>
      )}
      <div className="score-row">
        <span>
          Reliability{" "}
          {item.reliability_score === null
            ? "unscored"
            : `${Math.round(item.reliability_score * 100)}%`}
        </span>
        <span>
          Relevance{" "}
          {item.relevance_score === null
            ? "unscored"
            : `${Math.round(item.relevance_score * 100)}%`}
        </span>
      </div>
      {item.raw_excerpt && (
        <details>
          <summary>Inspect source excerpt</summary>
          <pre>{item.raw_excerpt}</pre>
        </details>
      )}
    </article>
  );
}
function ReportPanel({ report }: { report: Report }) {
  return (
    <>
      <section className="conclusion">
        <div className="eyebrow">Conclusion</div>
        <p>{report.final_conclusion || "No conclusion recorded yet."}</p>
      </section>
      <div className="report-grid">
        <Items title="Checks performed" items={report.checks_performed} />
        <Items title="Failed checks" items={report.failed_checks} />
        <Items title="Open questions" items={report.open_questions} />
        <Items title="Contradictions" items={report.contradictions} />
      </div>
      <section className="report-section">
        <h3>Evidence used</h3>
        {report.evidence_used.length ? (
          report.evidence_used.map((e, i) => <Source item={e} key={i} />)
        ) : (
          <p className="muted">No supporting evidence recorded.</p>
        )}
      </section>
      <section className="report-section">
        <h3>Evidence against</h3>
        {report.evidence_against.length ? (
          report.evidence_against.map((e, i) => <Source item={e} key={i} />)
        ) : (
          <p className="muted">
            No contrary evidence recorded. This does not establish that none
            exists.
          </p>
        )}
      </section>
      <section className="next-action">
        <ArrowRight size={19} />
        <div>
          <h3>Recommended next action</h3>
          <p>{report.recommended_next_action}</p>
        </div>
      </section>
    </>
  );
}

export default function Workbench() {
  const cache = useQueryClient();
  const [id, setId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("Report");
  const [problem, setProblem] = useState("");
  const [mode, setMode] = useState("investigate");
  const [context, setContext] = useState({ time: "", metric: "", entity: "" });
  const [sourceEnabled, setSourceEnabled] = useState(false);
  const [sourceInput, setSourceInput] = useState<SourceInput>({
    source_code: "",
    check_code: "",
    execution_approved: false,
    provider_approved: false,
  });
  const sourceReady =
    !sourceEnabled ||
    (sourceInput.source_code &&
      sourceInput.check_code &&
      sourceInput.execution_approved &&
      sourceInput.provider_approved);
  const [answer, setAnswer] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [feedbackFilter, setFeedbackFilter] = useState("");
  const [activeRun, setActiveRun] = useState<string | null>(null);

  const [sourceFilter, setSourceFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const busyHere = busy && id === activeRun;
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const sync = () => {
      setId(new URLSearchParams(window.location.search).get("session"));
      setTab("Report");
      setError(null);
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  function select(next: string | null) {
    setId(next);
    if (!next) {
      setMode("investigate");
      setContext({ time: "", metric: "", entity: "" });
      setSourceEnabled(false);
      setSourceInput({
        source_code: "",
        check_code: "",
        execution_approved: false,
        provider_approved: false,
      });
    }
    setTab("Report");
    setAnswer("");
    setError(null);
    setSourceFilter("");
    window.history.pushState(null, "", next ? `?session=${next}` : "/");
  }
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ status: string }>("health"),
    refetchInterval: 15000,
  });
  const history = useQuery({
    queryKey: ["history", search, filter, feedbackFilter, offset],
    queryFn: () =>
      api<History>(
        `api/v1/sessions?limit=25&offset=${offset}&q=${encodeURIComponent(search)}${filter ? `&status=${filter}` : ""}${feedbackFilter ? `&feedback_type=${feedbackFilter}` : ""}`,
      ),
    refetchInterval: busy ? 1500 : 10000,
  });
  const session = useQuery({
    queryKey: ["session", id],
    enabled: !!id,
    queryFn: () => api<Session>(`api/v1/sessions/${id}`),
    refetchInterval: (q) =>
      q.state.data?.status === "running" || busyHere ? 1000 : false,
  });
  const running = session.data?.status === "running";
  const report = useQuery({
    queryKey: ["report", id],
    enabled: !!id,
    queryFn: () => api<Report>(`api/v1/sessions/${id}/report`),
    refetchInterval: running || busyHere ? 1500 : false,
  });
  const artifacts = useQuery({
    queryKey: ["artifacts", id],
    enabled: !!id,
    queryFn: () => api<Artifacts>(`api/v1/sessions/${id}/artifacts`),
    refetchInterval: running || busyHere ? 2000 : false,
  });
  const events = useQuery({
    queryKey: ["trace", id],
    enabled: !!id,
    queryFn: () => trace(id!),
    refetchInterval: running || busyHere ? 1000 : false,
  });
  const pending = session.data?.status === "awaiting_user_input";
  useEffect(() => {
    if (id && session.data?.status && session.data.status !== "running") {
      for (const key of ["report", "artifacts", "trace", "candidate"])
        void cache.invalidateQueries({ queryKey: [key, id] });
    }
  }, [cache, id, session.data?.status]);
  async function execute(target: string, response?: string) {
    await api(
      `api/v1/sessions/${target}/${response === undefined ? "run" : "respond"}`,
      response === undefined ? {} : { answer: response },
    );
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!problem.trim() || busy || !sourceReady) return;
    setBusy(true);
    setError(null);
    try {
      const extras = [
        ["Time window", context.time],
        ["Metric / success criterion", context.metric],
        ["Affected entity", context.entity],
      ].filter(([, value]) => value.trim());
      const rawInput =
        problem.trim() +
        (extras.length
          ? "\n\nUser-provided context:\n" +
            extras
              .map(([label, value]) => `${label}: ${value.trim()}`)
              .join("\n")
          : "");
      const created = await api<Session>(
        sourceEnabled ? "api/v1/source-check" : "api/v1/sessions",
        sourceEnabled
          ? { raw_input: rawInput, ...sourceInput }
          : { raw_input: rawInput, mode },
      );
      cache.setQueryData(["session", created.id], created);
      setActiveRun(created.id);
      select(created.id);
      await execute(created.id);
      setProblem("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Investigation failed.");
    } finally {
      setBusy(false);
      void cache.invalidateQueries();
    }
  }
  async function resume(e: React.FormEvent) {
    e.preventDefault();
    if (!id || !answer.trim() || busy) return;
    setBusy(true);
    setActiveRun(id);
    setError(null);
    try {
      await execute(id, answer.trim());
      setAnswer("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not resume.");
    } finally {
      setBusy(false);
      void cache.invalidateQueries();
    }
  }
  async function startCreated() {
    if (!id || busy) return;
    setBusy(true);
    setActiveRun(id);
    setError(null);
    try {
      await execute(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start.");
    } finally {
      setBusy(false);
      void cache.invalidateQueries();
    }
  }
  function download() {
    if (!session.data || !report.data) return;
    const url = URL.createObjectURL(
      new Blob([reportMarkdown(session.data, report.data)], {
        type: "text/markdown;charset=utf-8",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `polyabrain-${id}.md`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const latest = events.data?.at(-1);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to investigation
      </a>
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="PolyaBrain home">
          <span className="brand-mark">
            <Waypoints size={22} />
          </span>
          <span>
            polya<span className="brand-light">brain</span>
            <small>INVESTIGATOR</small>
          </span>
        </a>
        <Button className="new-button" onClick={() => select(null)}>
          <Plus size={16} /> New investigation
        </Button>
        <div className="sidebar-heading">
          <HistoryIcon size={14} /> Your investigations
        </div>
        <label className="search-box">
          <Search size={15} />
          <input
            aria-label="Search investigations"
            placeholder="Search history…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <select
          aria-label="Filter by status"
          className="status-filter"
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="awaiting_user_input">Needs your input</option>
          <option value="running">Running</option>
          <option value="failed">Failed</option>
          <option value="created">Ready to run</option>
        </select>
        <select
          aria-label="Filter feedback for review"
          className="status-filter"
          value={feedbackFilter}
          onChange={(e) => {
            setFeedbackFilter(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">All feedback</option>
          <option value="wrong">Review: wrong</option>
          <option value="incomplete">Review: incomplete</option>
          <option value="unsafe">Review: unsafe</option>
          <option value="useful">Review: useful</option>
        </select>
        <nav className="history" aria-label="Investigation history">
          {history.isPending ? (
            <p className="sidebar-note">Loading history…</p>
          ) : history.isError ? (
            <p role="alert" className="sidebar-note">
              History unavailable.{" "}
              <button onClick={() => void history.refetch()}>Retry</button>
            </p>
          ) : !history.data?.sessions.length ? (
            <p className="sidebar-note">
              {search || filter || feedbackFilter
                ? "No matching investigations."
                : "Your investigations will appear here."}
            </p>
          ) : (
            history.data.sessions.map((s) => (
              <button
                key={s.id}
                aria-current={id === s.id ? "page" : undefined}
                className={`history-item ${id === s.id ? "selected" : ""}`}
                onClick={() => select(s.id)}
              >
                <span>{s.raw_input}</span>
                <small>
                  <i className={`status-dot ${s.status}`} />
                  {words(s.status)} ·{" "}
                  {new Date(s.created_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                </small>
              </button>
            ))
          )}
        </nav>
        {(offset > 0 || history.data?.has_more) && (
          <div className="pagination">
            <Button
              variant="ghost"
              size="sm"
              disabled={!offset}
              onClick={() => setOffset(Math.max(0, offset - 25))}
            >
              Previous
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={!history.data?.has_more}
              onClick={() => setOffset(history.data!.next_offset!)}
            >
              Next
            </Button>
          </div>
        )}
        <div className="sidebar-footer">
          <span className={`connection ${health.isSuccess ? "online" : ""}`} />
          {health.isSuccess
            ? "Service connected"
            : health.isPending
              ? "Connecting…"
              : "Service unavailable"}
          <small>Local workbench · experimental</small>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>
            Workspace <span className="slash">/</span>{" "}
            <strong>Investigator</strong>
          </span>
          <span className="local-label">
            <ShieldCheck size={14} /> Evidence before confidence
          </span>
        </header>
        <main id="main">
          {error && (
            <div role="alert" className="error-banner">
              {error}
              <Button
                variant="outline"
                size="sm"
                onClick={() => void cache.invalidateQueries()}
              >
                Refresh status
              </Button>
            </div>
          )}
          {!id ? (
            <div className="welcome">
              <div className="eyebrow accent">
                <span className="tiny-line" /> A clearer path through difficult
                problems
              </div>
              <h1>
                Move from a question
                <br />
                to a checked conclusion.
              </h1>
              <p className="intro">
                Investigate what’s happening, inspect the evidence, and see what
                holds up. Every outcome comes with its checks and open
                questions.
              </p>
              <form className="problem-form" onSubmit={submit}>
                <div className="form-heading">
                  <FileSearch size={19} />
                  <label htmlFor="problem">What are you trying to solve?</label>
                  <select
                    aria-label="Investigation mode"
                    value={sourceEnabled ? "investigate" : mode}
                    disabled={sourceEnabled}
                    onChange={(e) => setMode(e.target.value)}
                  >
                    <option value="investigate">Investigate</option>
                    <option value="compare">Compare</option>
                    <option value="review">Review</option>
                  </select>
                </div>
                <textarea
                  id="problem"
                  required
                  maxLength={20000}
                  value={problem}
                  onChange={(e) => setProblem(e.target.value)}
                  placeholder="Describe the problem, what you’ve observed, and what a successful outcome looks like…"
                  rows={7}
                />
                <details className="input-context">
                  <summary>
                    Add context <span>(optional)</span>
                  </summary>
                  <div>
                    <label>
                      Time window
                      <input
                        maxLength={200}
                        value={context.time}
                        onChange={(e) =>
                          setContext({ ...context, time: e.target.value })
                        }
                        placeholder="e.g. since the latest deployment"
                      />
                    </label>
                    <label>
                      Metric or success criterion
                      <input
                        maxLength={200}
                        value={context.metric}
                        onChange={(e) =>
                          setContext({ ...context, metric: e.target.value })
                        }
                        placeholder="e.g. p95 latency below 300 ms"
                      />
                    </label>
                    <label>
                      Affected entity
                      <input
                        maxLength={200}
                        value={context.entity}
                        onChange={(e) =>
                          setContext({ ...context, entity: e.target.value })
                        }
                        placeholder="e.g. checkout API"
                      />
                    </label>
                  </div>
                </details>
                <div className="source-toggle">
                  <label>
                    <input
                      type="checkbox"
                      checked={sourceEnabled}
                      onChange={(e) => {
                        setSourceEnabled(e.target.checked);
                        setSourceInput({
                          source_code: "",
                          check_code: "",
                          execution_approved: false,
                          provider_approved: false,
                        });
                      }}
                    />{" "}
                    Investigate Python source with a regression check{" "}
                    <span>Experimental</span>
                  </label>
                </div>
                {sourceEnabled && (
                  <SourceCheckInput
                    value={sourceInput}
                    onChange={setSourceInput}
                  />
                )}
                <div className="form-footer">
                  <span>
                    Include constraints and evidence you already have.
                  </span>
                  <Button
                    type="submit"
                    disabled={!problem.trim() || busy || !sourceReady}
                  >
                    {busy ? (
                      <LoaderCircle className="spin" size={16} />
                    ) : (
                      <ArrowRight size={16} />
                    )}{" "}
                    Start investigation
                  </Button>
                </div>
              </form>
              <div className="start-points">
                <span>Try a small, verifiable problem</span>
                <button onClick={() => setProblem("What is 17 * 6?")}>
                  <span>Check a calculation</span>
                  <ArrowUpRight size={15} />
                </button>
                <button
                  onClick={() =>
                    setProblem(
                      "Our API p95 latency increased after a deployment. Help me identify what evidence is needed to isolate the cause before choosing a fix.",
                    )
                  }
                >
                  <span>Investigate a regression</span>
                  <ArrowUpRight size={15} />
                </button>
              </div>
              <div className="principles">
                <div>
                  <FileSearch />
                  <h3>Evidence you can inspect</h3>
                  <p>
                    Sources, claims, and their limitations stay attached to the
                    result.
                  </p>
                </div>
                <div>
                  <FlaskConical />
                  <h3>Conclusions with checks</h3>
                  <p>
                    See what was tested and where more evidence is still needed.
                  </p>
                </div>
                <div>
                  <Waypoints />
                  <h3>A visible investigation</h3>
                  <p>
                    Follow the decisions, tool results, and next steps in the
                    audit trace.
                  </p>
                </div>
              </div>
              <p className="local-note">
                This local preview shares investigation history with anyone who
                can access this workbench. Model-backed investigations use your
                backend’s configured provider.
              </p>
            </div>
          ) : session.isPending ? (
            <Empty>
              <LoaderCircle className="spin" /> Loading investigation…
            </Empty>
          ) : session.isError ? (
            <Empty>
              <p role="alert">{session.error.message}</p>
              <Button variant="outline" onClick={() => void session.refetch()}>
                Retry
              </Button>
            </Empty>
          ) : (
            session.data && (
              <div className="investigation">
                <div className="detail-kicker">
                  <span className="eyebrow">{words(session.data.mode)}</span>
                  <span className="session-id">{id.slice(0, 8)}</span>
                </div>
                <h1>{session.data.raw_input}</h1>
                <div className="detail-meta">
                  <span
                    className={`badge ${report.data?.verification_status === "passed" ? "verified" : ""}`}
                  >
                    {report.data?.verification_status === "passed" ? (
                      <Check size={13} />
                    ) : null}
                    {words(session.data.status)}
                  </span>
                  <span>
                    {new Date(session.data.created_at).toLocaleString()}
                  </span>
                  {report.data && (
                    <span>
                      Confidence: {words(report.data.confidence_level)}
                    </span>
                  )}
                </div>
                {session.data.status === "created" && !busy && (
                  <div className="notice">
                    <p>This investigation is saved and ready to run.</p>
                    <Button onClick={startCreated}>
                      Start saved investigation <ArrowRight size={15} />
                    </Button>
                  </div>
                )}
                {(running || busyHere) && (
                  <div className="live-banner" role="status">
                    <LoaderCircle className="spin" size={18} />
                    <div>
                      <strong>Investigation in progress</strong>
                      <p>
                        {latest?.summary ||
                          "Waiting for the next recorded action…"}
                      </p>
                      <small>
                        Trace refreshes every second. Closing this page does not
                        cancel the backend run.
                      </small>
                    </div>
                  </div>
                )}
                {pending && (
                  <form className="clarification" onSubmit={resume}>
                    <div className="eyebrow">Your input is needed</div>
                    <h2>Help close the information gap.</h2>
                    {report.data?.open_questions.map((q, i) => (
                      <p key={i}>{q}</p>
                    ))}
                    <label htmlFor="answer">
                      Add the missing details and describe the complete
                      objective
                    </label>
                    <textarea
                      id="answer"
                      required
                      maxLength={20000}
                      rows={4}
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                    />
                    <Button disabled={busy || !answer.trim()} type="submit">
                      Continue investigation <ArrowRight size={15} />
                    </Button>
                  </form>
                )}
                {events.data && <RunOverview events={events.data} />}
                <div className="tabs-bar">
                  <div role="tablist" aria-label="Investigation details">
                    {tabs.map((name, i) => (
                      <button
                        key={name}
                        role="tab"
                        id={`tab-${name}`}
                        aria-controls="detail-panel"
                        aria-selected={tab === name}
                        tabIndex={tab === name ? 0 : -1}
                        onClick={() => setTab(name)}
                        onKeyDown={(e) => {
                          if (
                            ["ArrowRight", "ArrowLeft", "Home", "End"].includes(
                              e.key,
                            )
                          ) {
                            e.preventDefault();
                            const next =
                              e.key === "Home"
                                ? 0
                                : e.key === "End"
                                  ? 3
                                  : (i + (e.key === "ArrowRight" ? 1 : 3)) % 4;
                            setTab(tabs[next]);
                            document
                              .getElementById(`tab-${tabs[next]}`)
                              ?.focus();
                          }
                        }}
                      >
                        {name}
                        {name === "Evidence" && artifacts.data ? (
                          <span>{artifacts.data.evidence.length}</span>
                        ) : name === "Trace" && events.data ? (
                          <span>{events.data.length}</span>
                        ) : null}
                      </button>
                    ))}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={download}
                    aria-label="Export report"
                    disabled={!report.data}
                  >
                    <Download size={15} />
                    <span>Export report</span>
                  </Button>
                </div>
                <div
                  id="detail-panel"
                  role="tabpanel"
                  aria-labelledby={`tab-${tab}`}
                  tabIndex={0}
                  className="detail-panel"
                >
                  {tab === "Report" &&
                    (report.isError ? (
                      <Empty>{report.error.message}</Empty>
                    ) : report.data ? (
                      <>
                        <div className="verification-line">
                          <ShieldCheck size={16} />
                          <strong>
                            {words(report.data.verification_status)}
                          </strong>
                          <span>
                            Confidence: {report.data.confidence_level}
                          </span>
                        </div>
                        <ReportPanel report={report.data} />
                        <CandidatePanel
                          sessionId={id}
                          running={running || busyHere}
                        />
                        {[
                          "completed",
                          "failed",
                          "awaiting_user_input",
                        ].includes(session.data.status) && (
                          <FeedbackPanel key={id} sessionId={id} />
                        )}
                      </>
                    ) : (
                      <Empty>Loading report…</Empty>
                    ))}
                  {tab === "Evidence" &&
                    (artifacts.isError ? (
                      <Empty>{artifacts.error.message}</Empty>
                    ) : artifacts.data?.evidence.length ? (
                      <>
                        <div className="panel-heading">
                          <h2>Evidence register</h2>
                          <select
                            aria-label="Filter evidence source"
                            value={sourceFilter}
                            onChange={(e) => setSourceFilter(e.target.value)}
                          >
                            <option value="">All source types</option>
                            {Array.from(
                              new Set(
                                artifacts.data.evidence.map(
                                  (e) => e.source_type,
                                ),
                              ),
                            ).map((t) => (
                              <option key={t} value={t}>
                                {words(t)}
                              </option>
                            ))}
                          </select>
                        </div>
                        {artifacts.data.evidence
                          .filter(
                            (e) =>
                              !sourceFilter || e.source_type === sourceFilter,
                          )
                          .map((e, i) => (
                            <Source key={i} item={e} />
                          ))}
                      </>
                    ) : (
                      <Empty>
                        {running
                          ? "Evidence will appear when the run saves its artifacts."
                          : "No evidence has been recorded for this investigation."}
                      </Empty>
                    ))}
                  {tab === "Hypotheses" &&
                    (artifacts.isError ? (
                      <Empty>{artifacts.error.message}</Empty>
                    ) : artifacts.data?.hypotheses.length ? (
                      artifacts.data.hypotheses.map((h, i) => (
                        <details className="hypothesis" key={i} open={i === 0}>
                          <summary>
                            <span className="rank">{i + 1}</span>
                            <span>
                              {h.statement}
                              <small>
                                {words(h.status)} ·{" "}
                                {h.confidence === null
                                  ? "Confidence unscored"
                                  : `${Math.round(h.confidence * 100)}% confidence`}
                              </small>
                            </span>
                            <ChevronDown size={16} />
                          </summary>
                          <div className="hypothesis-body">
                            {h.mechanism && <p>{h.mechanism}</p>}
                            {h.selection_rationale && (
                              <p>{h.selection_rationale}</p>
                            )}
                            <Items
                              title="Expected signals"
                              items={h.expected_signals}
                            />
                            <Items
                              title="Verification checks"
                              items={h.verification_checks}
                            />
                            <Items
                              title="Falsification criteria"
                              items={h.falsification_criteria}
                            />
                          </div>
                        </details>
                      ))
                    ) : (
                      <Empty>
                        No hypotheses recorded. Deterministic problems may not
                        require competing explanations.
                      </Empty>
                    ))}
                  {tab === "Trace" &&
                    (events.isError ? (
                      <Empty>{events.error.message}</Empty>
                    ) : events.data?.length ? (
                      <>
                        <div className="panel-heading">
                          <h2>Audit trace</h2>
                          <span className="muted">
                            {events.data.length} recorded events
                          </span>
                        </div>
                        <ol className="trace-list">
                          {events.data.map((event) => (
                            <li key={event.id}>
                              <span className="trace-marker" />
                              <details>
                                <summary>
                                  <div>
                                    <span className="eyebrow">
                                      {words(event.reasoning_mode)} ·{" "}
                                      {words(event.engine_name)}
                                    </span>
                                    <p>{event.summary}</p>
                                  </div>
                                  <time>
                                    {new Date(
                                      event.created_at,
                                    ).toLocaleTimeString()}
                                  </time>
                                </summary>
                                <pre>
                                  {JSON.stringify(
                                    {
                                      event_type: event.event_type,
                                      sequence: event.sequence_number,
                                      ...event.metadata,
                                    },
                                    null,
                                    2,
                                  )}
                                </pre>
                              </details>
                            </li>
                          ))}
                        </ol>
                      </>
                    ) : (
                      <Empty>No trace events recorded yet.</Empty>
                    ))}
                </div>
              </div>
            )
          )}
        </main>
        <footer className="page-footer">
          PolyaBrain Investigator{" "}
          <span>Understand. Investigate. Verify. Learn.</span>
        </footer>
      </div>
    </div>
  );
}
