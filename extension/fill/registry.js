/**
 * registry.js — the adapter contract and registry for the application filler.
 *
 * Every ATS gets its own adapter. The registry picks the first adapter whose
 * `matches()` accepts the current page, and falls back to the generic one.
 *
 * An adapter is a plain object:
 *
 *   id         string, stable, used in the overlay and in stored field maps.
 *   label      what the overlay calls it.
 *   matches(location) -> boolean
 *   isReviewPage()    -> boolean   the filler halts when this is true
 *   scan()            -> Field[]   every visible, answerable control on screen
 *   fill(field, value) -> Promise<{ok, reason?}>
 *
 * A Field is { label, kind, el, options }:
 *   label    the visible label text, which is what the answer bank matches on.
 *            Never a CSS selector: selectors rot on every ATS redeploy, label
 *            text is what the applicant actually reads.
 *   kind     "text" | "textarea" | "select" | "radio" | "checkbox" | "combobox"
 *   el       the control, or the container for a group or custom widget.
 *   options  visible choices, when the control has a fixed set.
 *   members  for a radio or checkbox group, its inputs. Held explicitly so
 *            filling one group can never reach another group's inputs.
 */

"use strict";

(() => {
  const ns = (window.__jsFill = window.__jsFill || {});
  const adapters = [];

  function registerAdapter(adapter) {
    for (const key of ["id", "label", "matches", "isReviewPage", "scan", "fill"]) {
      if (!adapter[key]) throw new Error(`adapter is missing ${key}`);
    }
    adapters.push(adapter);
    return adapter;
  }

  /** Most specific adapter first; `generic` registers itself last on purpose. */
  function pickAdapter(location = window.location) {
    return adapters.find((a) => a.matches(location)) || null;
  }

  Object.assign(ns, { registerAdapter, pickAdapter, adapters });
})();
