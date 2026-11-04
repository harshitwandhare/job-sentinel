/**
 * content.js — orchestrates one pass of the application filler.
 *
 * Injected by the popup on demand, so the extension needs no standing host
 * permission on any ATS: the user's click on the toolbar icon is the grant.
 *
 * The pass is deliberately boring:
 *   1. Pick an adapter. Halt if it says this is the review step.
 *   2. Scan the visible labels and send them to the local API in one request.
 *   3. Show the plan. Type nothing.
 *   4. On the second click, fill, then report what landed and what did not.
 *
 * The filler never clicks submit, never answers a judgement call, and never
 * receives a value the answer bank marks private.
 */

"use strict";

(async () => {
  const ns = window.__jsFill;
  const DEFAULT_API_BASE = "http://127.0.0.1:8000";

  if (document.getElementById("job-sentinel-filler")) return; // already open

  function apiBase() {
    return new Promise((resolve) => {
      chrome.storage.local.get(["apiBase"], (got) => resolve(got.apiBase || DEFAULT_API_BASE));
    });
  }

  async function post(path, body) {
    const base = await apiBase();
    const resp = await fetch(base + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  const adapter = ns.pickAdapter();
  const overlay = ns.createOverlay({
    adapterLabel: adapter.label,
    onScan: () => scan(),
  });

  /** Rows the user reads before anything is typed. */
  let plan = [];

  async function scan() {
    if (adapter.isReviewPage()) {
      overlay.setStatus(
        "This is the review step. Read what you are about to send and submit it yourself.",
        true,
      );
      overlay.setRows([]);
      overlay.setAction("Find fields", scan);
      return;
    }

    const fields = adapter.scan();
    if (!fields.length) {
      overlay.setStatus("No form fields on screen. Open the application step first.");
      overlay.setRows([]);
      return;
    }

    overlay.setStatus("Asking your tracker what it knows…");
    let matches;
    try {
      matches = await post("/api/answers/match", { labels: fields.map((f) => f.label) });
    } catch (err) {
      const offline = err instanceof TypeError;
      overlay.setStatus(
        offline
          ? "Job Sentinel is not running. Start it with: job-sentinel serve"
          : `Your tracker answered with an error: ${err.message}`,
        true,
      );
      return;
    }

    plan = fields.map((field, i) => {
      const m = matches[i] || {};
      const row = { field, label: field.label, kind: field.kind, value: null, why: "" };
      if (m.private) {
        row.why = m.note || "you answer this one yourself";
      } else if (!m.field_id) {
        row.why = "no stored answer for this label";
      } else if (!m.value) {
        row.why = m.note || "stored, but left blank on purpose";
      } else {
        row.value = m.value;
        // A dropdown rarely words a choice the way the bank stores it. The
        // field's `options` are the other phrasings the user accepts, tried
        // in order, so "Master of Science" can still land on "Master's".
        row.candidates = [m.value, ...(m.options || []).filter((o) => o !== m.value)];
      }
      return row;
    });

    const fillable = plan.filter((r) => r.value);
    overlay.setRows(plan);
    overlay.setCount(`${fillable.length} of ${plan.length} fields`);
    if (!fillable.length) {
      overlay.setStatus("Nothing here the bank can answer. Fill these by hand.");
      overlay.setAction("Find fields", scan);
      return;
    }
    overlay.setStatus(`Ready to fill ${fillable.length}. Nothing is typed until you say so.`);
    overlay.setAction(`Fill these ${fillable.length}`, apply);
  }

  async function apply() {
    overlay.setAction("Filling…", null, { disabled: true });
    const done = [];
    for (const row of plan) {
      if (!row.value) {
        done.push(row);
        continue;
      }
      let result = { ok: false, reason: "no value" };
      for (const candidate of row.candidates || [row.value]) {
        try {
          result = await adapter.fill(row.field, candidate);
        } catch (err) {
          result = { ok: false, reason: err.message };
        }
        if (result.ok) {
          row.value = candidate;
          break;
        }
      }
      done.push(
        result.ok
          ? { ...row, why: "" }
          : { ...row, value: null, why: `not filled: ${result.reason}` },
      );
      await ns.sleep(60); // let the form's own validation settle between fields
    }

    const filled = done.filter((r) => r.value).length;
    overlay.setRows(done);
    overlay.setCount(`${filled} filled`);
    overlay.setStatus(
      filled === 0
        ? "Nothing landed. Check the labels above against the form."
        : "Filled. Read every field before you move on, then submit it yourself.",
    );
    overlay.setAction("Scan again", scan);
  }
})();
