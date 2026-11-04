/**
 * ashby.js — adapter for Ashby-hosted applications.
 *
 * Ashby wraps every question in a `_fieldEntry` container holding one label.
 * Text fields also carry a proper `label[for]`, so those are easy. The catch
 * is that a container often holds extra controls belonging to sub-questions:
 * the SMS and WhatsApp consent radios sit inside the Phone entry. Reading the
 * container label for those would answer "do you consent" with a phone number.
 *
 * So a container label is claimed by the first control that uses it, and every
 * later control in the same container falls back to its own name. A field
 * named `smsConsent` will not match the bank, which is the right outcome: it
 * is reported as unanswered instead of guessed.
 *
 * Verified against a live Ashby form on 2026-11-03.
 */

"use strict";

(() => {
  const ns = window.__jsFill;
  const { cleanLabel, visibleText, isVisible, hasValue } = ns;
  const { setControlValue, selectOption, chooseRadio, optionMatches, sleep } = ns;

  const NEEDS_REAL_CLICK = "needs a real click: this dropdown ignores synthetic input";

  const ENTRY = "[class*='_fieldEntry'], .ashby-application-form-field-entry";
  const CONTROLS =
    "input:not([type='hidden']):not([type='file']):not([type='submit']), textarea, select";

  function ownLabel(el) {
    if (el.id) {
      const tag = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (tag) return visibleText(tag);
    }
    return cleanLabel(el.getAttribute("aria-label") || "");
  }

  function kindOf(el) {
    if (el.getAttribute("role") === "combobox") return "combobox";
    if (el.tagName === "SELECT") return "select";
    if (el.tagName === "TEXTAREA") return "textarea";
    return "text";
  }

  /**
   * Fill an Ashby dropdown, or say honestly that it cannot.
   *
   * Same caveat as Greenhouse: a widget that only opens on a trusted gesture
   * cannot be driven by dispatched events. Verify, then report.
   */
  async function fillCombobox(input, value) {
    input.focus();
    setControlValue(input, value);
    await sleep(150);

    const listbox = document.querySelector("[role='listbox']");
    const options = listbox
      ? Array.from(listbox.querySelectorAll("[role='option']")).filter(isVisible)
      : [];
    if (!options.length) {
      setControlValue(input, "");
      return { ok: false, reason: NEEDS_REAL_CLICK };
    }

    const pick = options.find((o) => optionMatches(visibleText(o), value));
    if (!pick) {
      setControlValue(input, "");
      input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      return { ok: false, reason: `no option reads "${value}"` };
    }

    pick.click();
    await sleep(150);
    if (input.value && !document.querySelector("[class*='selectedValue'], [class*='singleValue']")) {
      setControlValue(input, "");
      return { ok: false, reason: NEEDS_REAL_CLICK };
    }
    return { ok: true };
  }

  ns.registerAdapter({
    id: "ashby",
    label: "Ashby",

    matches(location) {
      if (/(^|\.)ashbyhq\.com$/.test(location.hostname)) return true;
      return Boolean(document.querySelector(".ashby-application-form-field-entry"));
    },

    isReviewPage() {
      return false;
    },

    scan() {
      const out = [];
      const seenGroups = new Set();

      for (const entry of document.querySelectorAll(ENTRY)) {
        if (!isVisible(entry)) continue;
        const entryLabel = visibleText(entry.querySelector("label"));
        let claimed = false;

        for (const el of entry.querySelectorAll(CONTROLS)) {
          if (!isVisible(el) || el.disabled || el.readOnly) continue;

          if (el.type === "radio" || el.type === "checkbox") {
            const name = el.name || el.id;
            if (!name || seenGroups.has(name)) continue;
            seenGroups.add(name);
            const members = Array.from(
              entry.querySelectorAll(`input[name="${CSS.escape(name)}"]`),
            );
            const label = claimed ? cleanLabel(name) : entryLabel;
            claimed = true;
            if (!label) continue;
            out.push({
              label,
              kind: el.type,
              el: entry,
              options: members.map((m) => visibleText(m.closest("label") || m.parentElement)),
              members,
            });
            continue;
          }

          const label = ownLabel(el) || (claimed ? cleanLabel(el.name || "") : entryLabel);
          if (!label) continue;
          claimed = true;
          out.push({
            label,
            kind: kindOf(el),
            el,
            options:
              el.tagName === "SELECT" ? Array.from(el.options).map((o) => visibleText(o)) : [],
            members: [],
          });
        }
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
      if (field.kind === "combobox") return fillCombobox(field.el, value);
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
