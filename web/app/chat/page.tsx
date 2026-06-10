"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { sendChat, type ChatTurn } from "@/lib/api";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "sentinel-chat-v1";
const MAX_INPUT = 8000;
const MAX_PERSISTED = 40;

const SUGGESTIONS = [
  "What's closing soon?",
  "Show my recent jobs",
  "Summarize my profile",
  "What can you do?",
];

function loadHistory(): ChatTurn[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (m): m is ChatTurn =>
        typeof m === "object" &&
        m !== null &&
        ((m as ChatTurn).role === "user" || (m as ChatTurn).role === "assistant") &&
        typeof (m as ChatTurn).content === "string",
    );
  } catch {
    return []; // corrupt storage → start fresh, never crash
  }
}

/** Render the assistant's lightweight markdown (bold + bullets + code). */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => (
        <p key={i} className={cn("min-h-[1em]", line.startsWith("•") && "pl-1")}>
          {line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, j) => {
            if (part.startsWith("**") && part.endsWith("**")) {
              return <strong key={j}>{part.slice(2, -2)}</strong>;
            }
            if (part.startsWith("`") && part.endsWith("`")) {
              return (
                <code key={j} className="rounded bg-night/90 px-1.5 py-0.5 font-mono text-xs text-brand-400">
                  {part.slice(1, -1)}
                </code>
              );
            }
            return <span key={j}>{part}</span>;
          })}
        </p>
      ))}
    </>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Hydrate from localStorage after mount (SSR-safe).
  useEffect(() => {
    setMessages(loadHistory());
    setHydrated(true);
  }, []);

  // Persist (capped) and keep the view pinned to the latest message.
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_PERSISTED)));
    } catch {
      /* storage full/blocked — chat still works in memory */
    }
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, hydrated]);

  const ask = useCallback(
    async (text: string) => {
      const content = text.trim().slice(0, MAX_INPUT);
      if (!content || busy) return;
      setFailed(false);
      setBusy(true);
      setInput("");
      const next: ChatTurn[] = [...messages, { role: "user", content }];
      setMessages(next);

      const res = await sendChat(next.slice(-12));
      if (res) {
        setMessages([...next, { role: "assistant", content: res.reply }]);
      } else {
        setFailed(true);
        setMessages(messages); // roll back; the input is restored below for retry
        setInput(content);
      }
      setBusy(false);
      inputRef.current?.focus();
    },
    [busy, messages],
  );

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void ask(input);
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-7rem)] max-w-3xl flex-col px-5 py-8">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Ask Sentinel</h1>
          <p className="mt-1 text-sm text-muted">
            Deadlines, jobs, your profile, ATS scoring — or anything, via your local model.
          </p>
        </div>
        {messages.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => setMessages([])} disabled={busy}>
            Clear
          </Button>
        )}
      </header>

      <div
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        className="mt-6 flex-1 space-y-4 overflow-y-auto rounded-2xl border border-line bg-surface p-4 shadow-card"
      >
        {messages.length === 0 && hydrated && (
          <div className="flex h-full flex-col items-center justify-center gap-5 text-center">
            <span
              aria-hidden="true"
              className="grid h-12 w-12 place-items-center rounded-2xl bg-night text-xl text-brand-400"
            >
              ◈
            </span>
            <p className="max-w-sm text-sm text-muted">
              Everything stays on your machine — answers come from your tracked jobs, your
              profile, and your local model.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => void ask(s)}
                  className="rounded-full border border-line bg-bg px-3.5 py-1.5 text-sm text-ink transition-colors hover:border-brand hover:text-brand"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div
              className={cn(
                "max-w-[85%] space-y-1 rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                m.role === "user"
                  ? "rounded-br-md bg-brand text-white"
                  : "rounded-bl-md border border-line bg-bg text-ink",
              )}
            >
              {m.role === "assistant" ? <Rich text={m.content} /> : m.content}
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex justify-start" aria-label="Sentinel is thinking">
            <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-line bg-bg px-4 py-3">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted"
                  style={{ animationDelay: `${i * 140}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {failed && (
          <p className="text-center text-sm text-amber-600">
            Couldn&apos;t reach the API — is <code className="font-mono">job-sentinel serve</code>{" "}
            running? Your message was kept below; press Enter to retry.
          </p>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="mt-4 flex items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(input);
        }}
      >
        <label htmlFor="chat-input" className="sr-only">
          Message Sentinel
        </label>
        <textarea
          id="chat-input"
          ref={inputRef}
          rows={Math.min(5, Math.max(1, input.split("\n").length))}
          value={input}
          maxLength={MAX_INPUT}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask anything — or paste a job description for an ATS score…"
          className="flex-1 resize-none rounded-xl border border-line bg-surface px-4 py-3 text-sm text-ink shadow-sm placeholder:text-muted/70 focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30"
        />
        <Button type="submit" disabled={busy || !input.trim()} aria-label="Send message">
          Send
        </Button>
      </form>
      <p className="mt-2 text-center text-xs text-muted/80">
        Enter to send · Shift+Enter for a new line
      </p>
    </div>
  );
}
