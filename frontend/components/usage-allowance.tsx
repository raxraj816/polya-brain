"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Allowance = {
  enforced: boolean;
  daily_remaining?: number;
  daily_limit?: number;
  active_runs?: number;
  concurrent_limit?: number;
  resets_at?: string;
  per_invocation_limits?: {
    model_calls: number;
    input_tokens: number;
    output_tokens: number;
    external_calls: number;
  };
};
export function UsageAllowance() {
  const usage = useQuery({
    queryKey: ["usage"],
    queryFn: () => api<Allowance>("api/v1/usage"),
    refetchInterval: 5000,
    retry: false,
  });
  if (usage.isError)
    return (
      <p className="usage-allowance">
        Usage allowance is unavailable. Limits are still enforced when you start
        work.
      </p>
    );
  if (!usage.data?.enforced) return null;
  const u = usage.data;
  return (
    <div className="usage-allowance" role="status">
      <strong>
        {u.daily_remaining} of {u.daily_limit} runs available today
      </strong>
      <span>
        {u.active_runs} of {u.concurrent_limit} active
      </span>
      <details>
        <summary>How the allowance works</summary>
        <p>
          A start or clarification resume uses one allowance, including failed
          attempts that reached execution. Each invocation has its own resource
          limits. This is a usage allowance, not a billing estimate. Resets at{" "}
          {new Date(u.resets_at!).toLocaleString()} (00:00 UTC). Global service
          limits may also apply.
        </p>
        {u.per_invocation_limits && (
          <p>
            Per invocation: up to {u.per_invocation_limits.model_calls} model
            calls, {u.per_invocation_limits.input_tokens.toLocaleString()} input
            tokens, {u.per_invocation_limits.output_tokens.toLocaleString()}{" "}
            output tokens, and {u.per_invocation_limits.external_calls} external
            calls. Recorded consumption remains visible in each investigation
            trace.
          </p>
        )}
      </details>
      {u.daily_remaining === 0 && (
        <span>
          Daily limit reached. You can still read and export your
          investigations.
        </span>
      )}
    </div>
  );
}
