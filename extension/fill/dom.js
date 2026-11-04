/**
 * dom.js — shared DOM helpers for the application filler.
 *
 * The one thing worth reading here is setControlValue(). Assigning
 * `input.value = x` does not fire React's listeners, so a React-rendered form
 * (Workday, Greenhouse, Microsoft's own ATS) keeps its old state and reverts
 * the field the moment it loses focus. The fix is to go through the native
 * value setter on the element prototype and then dispatch the events React
 * actually listens for. This is a correctness problem, not a timing one.
 */

"use strict";

(() => {
  const ns = (window.__jsFill = window.__jsFill || {});

  /** Collapse whitespace and drop the decoration form labels carry. */
  function cleanLabel(raw) {
    return String(raw || "")
      .replace(/\s+/g, " ")
      .replace(/\s*\*+\s*$/, "")
      .replace(/\s*\(required\)\s*$/i, "")
      .replace(/\s*required\s*$/i, "")
      .trim();
  }

  /** Visible text of an element, ignoring anything screen-reader only. */
  function visibleText(el) {
    if (!el) return "";
    const clone = el.cloneNode(true);
    clone.querySelectorAll("script, style, [aria-hidden='true']").forEach((n) => n.remove());
    return cleanLabel(clone.textContent);
  }

  /**
   * False for anything display:none, visibility:hidden, or hidden from
   * assistive tech. Deliberately not a box-size check: a field's wrapper can
   * legitimately measure zero in a flex or grid layout while the control
   * inside it is on screen and typeable.
   */
  function isVisible(el) {
    if (!el || !el.isConnected) return false;
    if (el.closest("[hidden], [aria-hidden='true']")) return false;
    if (typeof el.checkVisibility === "function") {
      return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
    }
    return Boolean(el.offsetParent) || el.getClientRects().length > 0;
  }

  /** True when the control already holds a value we should not stamp over. */
  function hasValue(el) {
    if (!el) return false;
    if (el.type === "checkbox" || el.type === "radio") return el.checked;
    return Boolean(String(el.value || "").trim());
  }

  /**
   * Set a text, textarea or select value so a React form sees the change.
   * Returns true when the control ended up holding the value we asked for.
   */
  function setControlValue(el, value) {
    const proto = Object.getPrototypeOf(el);
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    el.focus();
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
    return String(el.value) === String(value);
  }

  /**
   * Does this option answer the value we want?
   *
   * Exact first, then a prefix that ends on a word boundary, so "Master"
   * finds "Master's Degree" while "No" never lands on "None of the above".
   * A bare startsWith would, and ticking the wrong box on a yes/no question
   * is the single worst thing this code could do.
   */
  function optionMatches(optionText, want) {
    const a = cleanLabel(optionText).toLowerCase();
    const b = String(want).trim().toLowerCase();
    if (!a || !b) return false;
    if (a === b) return true;
    return a.startsWith(b) && !/[a-z0-9]/.test(a.charAt(b.length));
  }

  /** Pick the option whose text or value matches, case-insensitively. */
  function selectOption(el, value) {
    const want = String(value).trim().toLowerCase();
    const match = Array.from(el.options).find(
      (o) => optionMatches(o.textContent, want) || String(o.value).toLowerCase() === want,
    );
    if (!match) return false;
    return setControlValue(el, match.value);
  }

  /**
   * Click the choice whose label matches `value`.
   *
   * Takes the group's members explicitly. Re-querying a container would reach
   * every radio under it, and when the container is the form or the document
   * (a group with no fieldset around it) that means answering a different
   * question by accident.
   */
  function chooseRadio(members, value) {
    const want = String(value).trim().toLowerCase();
    for (const input of members) {
      const own = input.id ? document.querySelector(`label[for="${CSS.escape(input.id)}"]`) : null;
      const text = visibleText(own || input.closest("label") || input.parentElement);
      if (optionMatches(text, want)) {
        input.click();
        return input.checked;
      }
    }
    return false;
  }

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  /** Poll until `fn()` returns something truthy, or give up. */
  async function waitFor(fn, { timeout = 2500, step = 100 } = {}) {
    const deadline = Date.now() + timeout;
    for (;;) {
      const got = fn();
      if (got) return got;
      if (Date.now() > deadline) return null;
      await sleep(step);
    }
  }

  Object.assign(ns, {
    cleanLabel,
    optionMatches,
    visibleText,
    isVisible,
    hasValue,
    setControlValue,
    selectOption,
    chooseRadio,
    sleep,
    waitFor,
  });
})();
