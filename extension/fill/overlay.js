/**
 * overlay.js — the filler's widget, in a shadow root so no application
 * stylesheet can reach it and it cannot leak styles back into the page.
 *
 * Two clicks, deliberately. "Find fields" shows a plan: every label on screen,
 * what would go into it, and why anything was skipped. Nothing is typed until
 * "Fill these". The applicant reads the plan first, and always presses submit
 * themselves.
 */

"use strict";

(() => {
  const ns = window.__jsFill;

  const CSS = `
  :host { all: initial; }
  .panel {
    position: fixed; right: 16px; bottom: 16px; z-index: 2147483647;
    width: 340px; max-height: 70vh; display: flex; flex-direction: column;
    font: 13px/1.45 ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
    color: #111827; background: #fff; border: 1px solid #d1d5db; border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0,0,0,.18);
  }
  header { display: flex; align-items: center; gap: 8px; padding: 10px 12px;
    border-bottom: 1px solid #e5e7eb; }
  header strong { font-size: 13px; font-weight: 650; }
  header .who { color: #6b7280; font-size: 11px; }
  header button.x { margin-left: auto; border: 0; background: none; cursor: pointer;
    color: #6b7280; font-size: 16px; line-height: 1; padding: 2px 4px; }
  .body { overflow: auto; padding: 10px 12px; }
  .status { color: #374151; }
  .status.warn { color: #92400e; background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 6px; padding: 8px 10px; }
  ul { list-style: none; margin: 8px 0 0; padding: 0; }
  li { padding: 7px 0; border-top: 1px solid #f3f4f6; }
  li:first-child { border-top: 0; }
  .lbl { font-weight: 600; }
  .val { color: #065f46; word-break: break-word; }
  .why { color: #6b7280; }
  .kind { color: #9ca3af; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
  footer { display: flex; gap: 8px; align-items: center; padding: 10px 12px;
    border-top: 1px solid #e5e7eb; }
  button.go { border: 0; border-radius: 6px; padding: 7px 12px; cursor: pointer;
    font: inherit; font-weight: 600; background: #111827; color: #fff; }
  button.go[disabled] { background: #9ca3af; cursor: default; }
  footer .count { margin-left: auto; color: #6b7280; font-size: 11px; }
  @media (prefers-color-scheme: dark) {
    .panel { color: #e5e7eb; background: #111827; border-color: #374151; }
    header, footer { border-color: #1f2937; }
    li { border-color: #1f2937; }
    .status { color: #d1d5db; }
    .status.warn { color: #fde68a; background: #27220f; border-color: #78350f; }
    .why, .kind { color: #9ca3af; }
    .val { color: #6ee7b7; }
    button.go { background: #e5e7eb; color: #111827; }
  }`;

  function createOverlay({ adapterLabel, onScan, onApply, onClose }) {
    const host = document.createElement("div");
    host.id = "job-sentinel-filler";
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>${CSS}</style>
      <div class="panel">
        <header>
          <strong>Job Sentinel</strong>
          <span class="who">${adapterLabel}</span>
          <button class="x" title="Close">&times;</button>
        </header>
        <div class="body"><div class="status"></div><ul></ul></div>
        <footer>
          <button class="go"></button>
          <span class="count"></span>
        </footer>
      </div>`;
    document.documentElement.appendChild(host);

    const statusEl = root.querySelector(".status");
    const listEl = root.querySelector("ul");
    const goEl = root.querySelector("button.go");
    const countEl = root.querySelector(".count");

    root.querySelector("button.x").addEventListener("click", () => {
      host.remove();
      onClose?.();
    });

    function setStatus(text, warn = false) {
      statusEl.textContent = text;
      statusEl.className = warn ? "status warn" : "status";
    }

    function setRows(rows) {
      listEl.replaceChildren();
      for (const row of rows) {
        const li = document.createElement("li");
        const lbl = document.createElement("div");
        lbl.className = "lbl";
        lbl.textContent = row.label;
        li.appendChild(lbl);

        const detail = document.createElement("div");
        detail.className = row.value ? "val" : "why";
        detail.textContent = row.value ? row.value : row.why;
        li.appendChild(detail);

        if (row.kind) {
          const kind = document.createElement("div");
          kind.className = "kind";
          kind.textContent = row.kind;
          li.appendChild(kind);
        }
        listEl.appendChild(li);
      }
    }

    function setAction(text, handler, { disabled = false } = {}) {
      goEl.textContent = text;
      goEl.disabled = disabled;
      goEl.onclick = handler || null;
    }

    function setCount(text) {
      countEl.textContent = text;
    }

    setAction("Find fields", onScan);
    setStatus("Nothing typed yet. Find the fields first.");

    return { host, setStatus, setRows, setAction, setCount, onApply };
  }

  ns.createOverlay = createOverlay;
})();
