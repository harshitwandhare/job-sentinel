/**
 * claude.js — the same adapters, driven by a Claude session instead of the
 * extension's overlay.
 *
 * The browser cannot call the local API from an employer's page: the API only
 * allows local origins, and widening that to every job site would mean any
 * page you visit could read your answer bank. So the network hop stays with
 * Claude. The page does DOM work only:
 *
 *   1. Claude injects this file plus the adapters from the local API.
 *   2. Claude calls __jsFill.labels(), gets the questions on screen.
 *   3. Claude posts them to /api/answers/match from the shell.
 *   4. Claude calls __jsFill.apply([...]) with the values that came back.
 *
 * Fields are addressed by index into one scan, so a value can never be typed
 * into a field matched from different text. Re-scan before every apply.
 */

"use strict";

(() => {
  const ns = window.__jsFill;
  let scanned = [];

  /** The questions on screen right now, with the adapter that read them. */
  function labels() {
    const adapter = ns.pickAdapter();
    if (adapter.isReviewPage()) {
      return { adapter: adapter.id, review: true, fields: [] };
    }
    scanned = adapter.scan();
    return {
      adapter: adapter.id,
      review: false,
      fields: scanned.map((f, i) => ({
        i,
        label: f.label,
        kind: f.kind,
        options: f.options,
      })),
    };
  }

  /**
   * Fill the fields named by index. `plan` is [{ i, value }] or
   * [{ i, candidates: [...] }]; candidates are tried in order, which is how a
   * dropdown worded differently from the stored answer still lands.
   */
  async function apply(plan) {
    const adapter = ns.pickAdapter();
    if (adapter.isReviewPage()) {
      return { review: true, results: [] };
    }
    if (!scanned.length) labels();

    const results = [];
    for (const item of plan) {
      const field = scanned[item.i];
      if (!field) {
        results.push({ i: item.i, ok: false, reason: "no field at that index" });
        continue;
      }
      const candidates = item.candidates || [item.value];
      let result = { ok: false, reason: "no value given" };
      let used = null;
      for (const candidate of candidates) {
        try {
          result = await adapter.fill(field, candidate);
        } catch (err) {
          result = { ok: false, reason: err.message };
        }
        if (result.ok) {
          used = candidate;
          break;
        }
      }
      results.push({ i: item.i, label: field.label, ok: result.ok, value: used, reason: result.reason });
      await ns.sleep(60);
    }
    return { review: false, results };
  }

  Object.assign(ns, { labels, apply });
})();
