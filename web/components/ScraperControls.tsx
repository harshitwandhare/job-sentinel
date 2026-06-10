"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import {
  getOpsStatus,
  getStats,
  startLogin,
  startScrape,
  startWatcher,
  stopWatcher,
  type OpsStatus,
} from "@/lib/api";

function fmtWhen(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/**
 * Login + scrape + watcher controls for the jobs page.
 * Polls /api/ops/status while anything is running and refreshes the
 * server-rendered job list when a scrape completes.
 */
export function ScraperControls() {
  const router = useRouter();
  const [status, setStatus] = useState<OpsStatus | null>(null);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [loaded, setLoaded] = useState(false);
  const [notice, setNotice] = useState("");
  const [sendAlerts, setSendAlerts] = useState(false);
  const prevScrapeState = useRef<string>("idle");

  const refresh = useCallback(async () => {
    const [s, st] = await Promise.all([getOpsStatus(), getStats()]);
    setStatus(s);
    setStats(st);
    setLoaded(true);
    // When a scrape just finished, re-render the job list below.
    if (s && prevScrapeState.current === "running" && s.scrape.state !== "running") {
      router.refresh();
    }
    prevScrapeState.current = s?.scrape.state ?? "idle";
  }, [router]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const busy =
    status?.login.state === "running" ||
    status?.scrape.state === "running" ||
    status?.watcher.running === true;

  useEffect(() => {
    const interval = setInterval(() => void refresh(), busy ? 2500 : 15000);
    return () => clearInterval(interval);
  }, [busy, refresh]);

  async function onLogin() {
    setNotice("");
    const r = await startLogin();
    if (!r.ok) setNotice(r.detail ?? "Could not start the login.");
    await refresh();
  }

  async function onScrape() {
    setNotice("");
    const r = await startScrape(sendAlerts);
    if (!r.ok) setNotice(r.detail ?? "Could not start the scrape.");
    await refresh();
  }

  async function onWatcher() {
    setNotice("");
    const r = status?.watcher.running ? await stopWatcher() : await startWatcher();
    if (!r.ok) setNotice(r.detail ?? "Could not toggle the watcher.");
    await refresh();
  }

  if (!loaded) {
    return (
      <Card>
        <CardSub>Checking scraper status…</CardSub>
      </Card>
    );
  }

  if (!status) {
    return (
      <Card>
        <CardTitle>API offline</CardTitle>
        <CardSub className="mt-2">
          Start the backend with <code>job-sentinel serve</code>, then refresh this page.
        </CardSub>
      </Card>
    );
  }

  const { session, login, scrape, watcher } = status;
  const loginRunning = login.state === "running";
  const scrapeRunning = scrape.state === "running";
  const statTotal = Object.values(stats).reduce((a, b) => a + b, 0);

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <CardTitle>Scraper</CardTitle>
          <CardSub className="mt-1">
            Adapter: <span className="font-medium">{status.adapter ?? "—"}</span>
            {statTotal > 0 && (
              <>
                {" · "}
                {Object.entries(stats)
                  .filter(([, n]) => n > 0)
                  .map(([k, n]) => `${n} ${k}`)
                  .join(" · ")}
              </>
            )}
          </CardSub>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
            session.exists ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
          }`}
        >
          {session.exists ? `Logged in · session saved ${fmtWhen(session.saved_at)}` : "Not logged in"}
        </span>
      </div>

      {!status.config_ok && (
        <p className="text-sm text-amber-600">{status.config_error}</p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" onClick={onLogin} disabled={loginRunning || scrapeRunning}>
          {loginRunning ? "Waiting for sign-in…" : session.exists ? "Re-login" : "Login"}
        </Button>
        <Button onClick={onScrape} disabled={loginRunning || scrapeRunning}>
          {scrapeRunning ? "Scraping…" : "Run scraper"}
        </Button>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={sendAlerts}
            onChange={(e) => setSendAlerts(e.target.checked)}
          />
          Send alerts (off = dry run)
        </label>
        <Button variant="outline" onClick={onWatcher} disabled={loginRunning}>
          {watcher.running ? "Stop watcher" : "Start watcher"}
        </Button>
        {watcher.running && watcher.interval_seconds && (
          <span className="text-xs text-muted">
            watching every {Math.round(watcher.interval_seconds / 60)} min
          </span>
        )}
      </div>

      {loginRunning && <p className="text-sm text-sky-700">{login.message}</p>}
      {!loginRunning && login.state === "error" && (
        <p className="text-sm text-amber-600">{login.message}</p>
      )}
      {!loginRunning && login.state === "ok" && scrape.state === "idle" && (
        <p className="text-sm text-emerald-700">{login.message}</p>
      )}

      {scrapeRunning && <p className="text-sm text-sky-700">{scrape.message}</p>}
      {scrape.state === "ok" && <p className="text-sm text-emerald-700">{scrape.message}</p>}
      {scrape.state === "error" && <p className="text-sm text-amber-600">{scrape.message}</p>}

      {notice && <p className="text-sm text-amber-600">{notice}</p>}
    </Card>
  );
}
