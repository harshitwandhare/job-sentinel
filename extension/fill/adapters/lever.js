/**
 * lever.js — adapter for Lever-hosted applications.
 *
 * Lever puts no label on its core fields at all: name, email, phone, org and
 * the URL fields are bare inputs identified only by `name`. What the applicant
 * reads is the `.application-label` in the `.application-question` wrapper
 * around them, so that wrapper is the unit of discovery here rather than the
 * control.
 *
 * Verified against a live Lever form on 2026-11-03: 36 controls, 21 labelled
 * wrappers, zero `label[for]` pairs.
 */

"use strict";

(() => {
  const ns = window.__jsFill;
  const { visibleText, isVisible, hasValue } = ns;
  const { setControlValue, selectOption, chooseRadio } = ns;

  const QUESTION = ".application-question";
  const CONTROLS =
    "input:not([type='hidden']):not([type='file']):not([type='submit']), textarea, select";

  /** Strip Lever's required marker, which is a glyph rather than an asterisk. */
  function labelOf(wrapper) {
    const own = wrapper.querySelector(".application-label");
    return visibleText(own)
      .replace(/[✱✲*]\s*$/, "")
      .trim();
  }

  function describe(wrapper, label) {
    const controls = Array.from(wrapper.querySelectorAll(CONTROLS)).filter(isVisible);
    if (!controls.length) return null;

    const first = controls[0];
    if (first.type === "radio" || first.type === "checkbox") {
      return {
        label,
        kind: first.type,
        el: wrapper,
        options: controls.map((c) => visibleText(c.closest("label") || c.parentElement)),
        members: controls,
      };
    }
    if (first.tagName === "SELECT") {
      return {
        label,
        kind: "select",
        el: first,
        options: Array.from(first.options).map((o) => visibleText(o)),
        members: [],
      };
    }
    return {
      label,
      kind: first.tagName === "TEXTAREA" ? "textarea" : "text",
      el: first,
      options: [],
      members: [],
    };
  }

  ns.registerAdapter({
    id: "lever",
    label: "Lever",

    matches(location) {
      if (/(^|\.)lever\.co$/.test(location.hostname)) return true;
      return Boolean(document.querySelector(".application-question .application-label"));
    },

    isReviewPage() {
      // Lever is one page with a submit button. Nothing to halt on, and this
      // adapter never clicks it.
      return false;
    },

    scan() {
      const out = [];
      for (const wrapper of document.querySelectorAll(QUESTION)) {
        if (!isVisible(wrapper)) continue;
        const label = labelOf(wrapper);
        if (!label) continue;
        const field = describe(wrapper, label);
        if (field) out.push(field);
      }
      return out;
    },

    async fill(field, value) {
      if (field.kind === "radio" || field.kind === "checkbox") {
        return chooseRadio(field.members, value)
          ? { ok: true }
          : { ok: false, reason: `no choice reads "${value}"` };
      }
      if (hasValue(field.el)) return { ok: false, reason: "already filled" };
      if (field.kind === "select") {
        return selectOption(field.el, value)
          ? { ok: true }
          : { ok: false, reason: `no option reads "${value}"` };
      }
      return setControlValue(field.el, value)
        ? { ok: true }
        : { ok: false, reason: "the field rejected the value" };
    },
  });
})();
