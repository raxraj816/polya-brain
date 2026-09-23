"use client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { UsageAllowance } from "@/components/usage-allowance";
import { Button } from "@/components/ui/button";

type Identity = {
  required: boolean;
  authenticated: boolean;
  workspace_id: string | null;
};
export function AuthGate({ children }: { children: React.ReactNode }) {
  const client = useQueryClient();
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");
  const auth = useQuery({
    queryKey: ["identity"],
    queryFn: () => api<Identity>("api/v1/auth/session"),
    refetchInterval: 30000,
    refetchOnWindowFocus: true,
    retry: false,
  });
  useEffect(() => {
    const expired = () => {
      client.setQueryData(["identity"], {
        required: true,
        authenticated: false,
        workspace_id: null,
      });
    };
    window.addEventListener("polya-auth-expired", expired);
    return () => window.removeEventListener("polya-auth-expired", expired);
  }, [client]);
  const signedOut = auth.data?.required && !auth.data.authenticated;
  useEffect(() => {
    if (signedOut || auth.isError) {
      void client.cancelQueries({
        predicate: (q) => q.queryKey[0] !== "identity",
      });
      client.removeQueries({ predicate: (q) => q.queryKey[0] !== "identity" });
    }
  }, [signedOut, auth.isError, client]);
  if (auth.isPending)
    return (
      <main className="auth-screen">
        <p>Connecting to your workbench…</p>
      </main>
    );
  if (auth.isError)
    return (
      <main className="auth-screen">
        <h1>Cannot connect to the workbench</h1>
        <p>Check the service connection, then try again.</p>
        <Button onClick={() => auth.refetch()}>Retry connection</Button>
      </main>
    );
  if (signedOut)
    return (
      <main className="auth-screen">
        <span className="eyebrow">POLYABRAIN INVESTIGATOR</span>
        <h1>Your work. Your evidence.</h1>
        <p>
          Sign in to investigate, verify outcomes, and return to your private
          workspace.
        </p>
        <a className="auth-link" href="/api/backend/api/v1/auth/login">
          Sign in
        </a>
      </main>
    );
  async function logout() {
    setSigningOut(true);
    setError("");
    try {
      await api("api/v1/auth/logout", {});
      await client.cancelQueries();
      client.clear();
      window.location.replace("/");
    } catch {
      setError("Sign-out could not be confirmed. Try again.");
      setSigningOut(false);
    }
  }
  return (
    <>
      {auth.data.required && (
        <div className="account-bar">
          <span>Private workspace</span>
          <Button
            variant="outline"
            size="sm"
            disabled={signingOut}
            onClick={logout}
          >
            {signingOut ? "Signing out…" : "Sign out"}
          </Button>
          {error && <span role="alert">{error}</span>}
        </div>
      )}
      <Workspace key={auth.data.workspace_id || "local"}>
        {auth.data.required && <UsageAllowance />}
        {children}
      </Workspace>
    </>
  );
}

function Workspace({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, staleTime: 1000 },
          mutations: { retry: false },
        },
      }),
  );
  useEffect(
    () => () => {
      void client.cancelQueries();
      client.clear();
    },
    [client],
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
