"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { authLogin, authLogout, getAuthStatus, type AuthStatus } from "@/lib/api";

/**
 * Sign-in screen for instances running with AUTH_MODE=demo|required.
 * With AUTH_MODE=off (the default local setup) this page just says so.
 */
export default function LoginPage() {
  const router = useRouter();
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getAuthStatus().then((s) => {
      setStatus(s);
      setLoaded(true);
    });
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const result = await authLogin(username, password);
    setBusy(false);
    if (result.ok) {
      router.push("/jobs");
    } else {
      setError(result.detail ?? "Login failed.");
    }
  }

  return (
    <div className="mx-auto max-w-md px-5 py-16">
      <Card className="space-y-4">
        <CardTitle>Sign in</CardTitle>

        {loaded && status?.mode === "off" && (
          <CardSub>
            This instance runs without authentication (<code>AUTH_MODE=off</code>) — everything
            is already available. To require logins, create an account with{" "}
            <code>job-sentinel users add &lt;name&gt; --admin</code> and start the API with{" "}
            <code>AUTH_MODE=demo</code> or <code>AUTH_MODE=required</code>.
          </CardSub>
        )}

        {loaded && status && status.mode !== "off" && status.user && (
          <div className="space-y-3">
            <CardSub>
              Signed in as <strong>{status.user.username}</strong>
              {status.user.is_admin ? " (admin)" : ""}.
            </CardSub>
            <Button
              variant="outline"
              onClick={() => {
                authLogout();
                router.refresh();
                setStatus({ ...status, user: null });
              }}
            >
              Sign out
            </Button>
          </div>
        )}

        {loaded && status && status.mode !== "off" && !status.user && (
          <form onSubmit={onSubmit} className="space-y-3">
            {status.mode === "demo" && (
              <CardSub>
                Demo mode: browsing is open, but actions (scrape, profile edits, resume builds)
                need an account.
              </CardSub>
            )}
            <Input
              placeholder="Username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <Input
              type="password"
              placeholder="Password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button type="submit" disabled={busy || !username || !password}>
              {busy ? "Signing in…" : "Sign in"}
            </Button>
            {error && <p className="text-sm text-amber-600">{error}</p>}
          </form>
        )}

        {loaded && !status && (
          <CardSub>
            Could not reach the API — start it with <code>job-sentinel serve</code>.
          </CardSub>
        )}
      </Card>
    </div>
  );
}
