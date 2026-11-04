/**
 * greenhouse.js — adapter for Greenhouse-hosted applications.
 *
 * Greenhouse ships no <select> elements at all. Every dropdown, including
 * Country, Location and each custom question, is a react-select combobox:
 * an `input[role=combobox].select__input` whose label lives on a separate
 * element referenced by aria-labelledby. Typing into one filters the list but
 * commits nothing, so the value disappears on blur unless an option is
 * clicked. That is the whole reason this adapter exists.
 *
 * Verified against a live Greenhouse form on 2026-11-03: 24 controls, every
 * one labelled through `label[for]` or aria-labelledby.
 */

"use strict";

(() => {
  const ns = window.__jsFill;
  const { cleanLabel, visibleText, isVisible, hasValue } = ns;
  const { setControlValue, chooseRadio, optionMatches, sleep } = ns;

  const NEEDS_REAL_CLICK = "needs a real click: this dropdown ignores synthetic input";

  const COMBO = "input[role='combobox']";
  const CONTROLS = [
    "input:not([type='hidden']):not([type='file']):not([type='submit']):not([type='button'])",
    "textarea",
    "select",
  ].join(", ");

  function labelFor(el) {
    const by = el.getAttribute("aria-labelledby");
    if (by) {
      const text = by
        .split(/\s+/)
        .map((id) => visibleText(document.getElementById(id)))
        .filter(Boolean)
        .join(" ");
      if (text) return text;
    }
    if (el.id) {
      const tag = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (tag) return visibleText(tag);
    }
    return cleanLabel(el.getAttribute("aria-label") || "");
  }

  /**
   * Fill one of Greenhouse's dropdowns, or say honestly that it cannot.
   *
   * Verified against a live form on 2026-11-03: these widgets do not react to
   * synthetic input at all. Typing does not filter the list, ArrowDown leaves
   * `aria-expanded` false, and a dispatched click on an option commits
   * nothing, because the options are in the DOM but not rendered until a real
   * gesture opens the menu. Browsers mark synthetic events untrusted and the
   * widget checks.
   *
   * So this tries, verifies, and reports failure rather than claiming a fill
   * that did not happen. A session driving a real browser can finish the job
   * with a trusted click; the extension cannot, and should say so.
   */
  async function fillCombobox(input, value) {
    input.focus();
    setControlValue(input, value);
    await sleep(150);

    const open = input.getAttribute("aria-expanded") === "true";
    const listbox = document.querySelector("[role='listbox'], .select__menu-list");
    const options = listbox
      ? Array.from(listbox.querySelectorAll("[role='option'], .select__option")).filter(isVisible)
      : [];

    if (!open || !options.length) {
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

    // Committing clears the filter input and shows the choice. If neither
    // happened the click was ignored, whatever it looked like.
    const committed =
      !input.value || Boolean(document.querySelector(".select__single-value, [class*='singleValue']"));
    if (!committed) {
      setControlValue(input, "");
      return { ok: false, reason: NEEDS_REAL_CLICK };
    }
    return { ok: true };
  }

  ns.registerAdapter({
    id: "greenhouse",
    label: "Greenhouse",

    matches(location) {
      if (/(^|\.)greenhouse\.io$/.test(location.hostname)) return true;
      // Companies embed the same form on their own domain, so fall back to
      // the markup rather than keeping a list of customer hostnames.
      return Boolean(
        document.querySelector("input.select__input[role='combobox']") &&
          document.querySelector("#first_name, #last_name"),
      );
    },

    isReviewPage() {
      // Greenhouse is a single page with a submit button at the bottom. There
      // is no review step to halt on, and this adapter never clicks submit.
      return false;
    },

    scan() {
      const out = [];
      const seen = new Set();
      for (const el of document.querySelectorAll(CONTROLS)) {
        if (!isVisible(el) || el.disabled || el.readOnly) continue;
        const label = labelFor(el);
        if (!label) continue;

        if (el.type === "radio" || el.type === "checkbox") {
          const name = el.name || el.id;
          if (seen.has(name)) continue;
          seen.add(name);
          const group = el.closest("fieldset, [role='radiogroup'], [role='group']");
          const scope = group || el.form || document.body;
          const members = el.name
            ? Array.from(scope.querySelectorAll(`input[name="${CSS.escape(el.name)}"]`))
            : [el];
          const legend = group && group.querySelector("legend");
          out.push({
            label: legend ? visibleText(legend) : label,
            kind: el.type,
            el: scope,
            options: members.map((m) => labelFor(m)).filter(Boolean),
            members,
          });
          continue;
        }

        const combo = el.matches(COMBO);
        out.push({
          label,
          kind: combo ? "combobox" : el.tagName === "TEXTAREA" ? "textarea" : "text",
          el,
          options: [],
          members: [],
        });
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
      return setControlValue(field.el, value)
        ? { ok: true }
        : { ok: false, reason: "the field rejected the value" };
    },
  });
})();
