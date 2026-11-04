/**
 * workday.js — adapter for Workday-hosted applications.
 *
 * Workday tags everything with `data-automation-id`, which is far more stable
 * than its class names, so field discovery hangs off that. Its dropdowns are
 * not <select> elements: they are buttons that open a listbox, so filling one
 * means clicking the button, waiting for the listbox, and clicking the option.
 *
 * The adapter stops the filler dead on the review step. Reading the summary
 * and pressing submit stays with the applicant.
 */

"use strict";

(() => {
  const ns = window.__jsFill;
  const { cleanLabel, visibleText, isVisible, hasValue } = ns;
  const { setControlValue, selectOption, chooseRadio, optionMatches, waitFor, sleep } = ns;

  const FIELD = "[data-automation-id^='formField-']";

  /**
   * The question this field asks.
   *
   * Order matters. A radio group's container holds a <label> per choice, so
   * taking the first <label> labels the field "Yes" and the answer bank then
   * matches the wrong question. The group's own legend or aria-labelledby
   * comes first, and a per-choice label is never used as the field label.
   */
  function labelFor(container) {
    const legend = container.querySelector("legend");
    if (legend) {
      const text = visibleText(legend);
      if (text) return text;
    }

    const group = container.querySelector("[role='group'], [role='radiogroup'], fieldset");
    const labelled = group && group.getAttribute("aria-labelledby");
    if (labelled) {
      const text = labelled
        .split(/\s+/)
        .map((id) => visibleText(document.getElementById(id)))
        .filter(Boolean)
        .join(" ");
      if (text) return text;
    }

    for (const own of container.querySelectorAll("label")) {
      const target = own.htmlFor ? document.getElementById(own.htmlFor) : own.querySelector("input");
      if (target && (target.type === "radio" || target.type === "checkbox")) continue;
      const text = cleanLabel(own.textContent);
      if (text) return text;
    }

    const rich = container.querySelector("[data-automation-id='richText'] p");
    return rich ? cleanLabel(rich.textContent) : "";
  }

  function classify(container) {
    const group = container.querySelector("[role='radiogroup'], fieldset");
    if (group && group.querySelector("input[type='radio']")) {
      return { kind: "radio", el: group };
    }
    if (group && group.querySelector("input[type='checkbox']")) {
      return { kind: "checkbox", el: group };
    }
    const select = container.querySelector("select");
    if (select) return { kind: "select", el: select };
    const combo = container.querySelector("button[aria-haspopup='listbox'], [role='combobox']");
    if (combo) return { kind: "combobox", el: combo };
    const area = container.querySelector("textarea");
    if (area) return { kind: "textarea", el: area };
    const input = container.querySelector("input:not([type='file']):not([type='hidden'])");
    if (input) return { kind: "text", el: input };
    return null;
  }

  function membersOf(found) {
    if (found.kind !== "radio" && found.kind !== "checkbox") return [];
    return Array.from(found.el.querySelectorAll("input[type='radio'], input[type='checkbox']"));
  }

  function optionsFor(found) {
    if (found.kind === "select") {
      return Array.from(found.el.options)
        .map((o) => cleanLabel(o.textContent))
        .filter(Boolean);
    }
    if (found.kind === "radio" || found.kind === "checkbox") {
      return Array.from(found.el.querySelectorAll("label"))
        .map((l) => visibleText(l))
        .filter(Boolean);
    }
    return [];
  }

  /** Click a Workday dropdown open and pick the matching option. */
  async function fillCombobox(button, value) {
    const want = String(value).trim().toLowerCase();
    button.click();
    const listbox = await waitFor(() => document.querySelector("[role='listbox']"));
    if (!listbox) return { ok: false, reason: "the dropdown did not open" };

    const pick = Array.from(listbox.querySelectorAll("[role='option']")).find((o) =>
      optionMatches(visibleText(o), want),
    );
    if (!pick) {
      button.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      return { ok: false, reason: `no option reads "${value}"` };
    }
    pick.click();
    await sleep(120);
    return { ok: true };
  }

  ns.registerAdapter({
    id: "workday",
    label: "Workday",

    matches(location) {
      return /(^|\.)myworkdayjobs\.com$|(^|\.)myworkdaysite\.com$/.test(location.hostname);
    },

    isReviewPage() {
      if (document.querySelector("[data-automation-id='reviewSection']")) return true;
      const headings = document.querySelectorAll("h1, h2, h3, [role='heading']");
      return Array.from(headings).some((h) => /^review\b/i.test(visibleText(h)));
    },

    scan() {
      const out = [];
      for (const container of document.querySelectorAll(FIELD)) {
        if (!isVisible(container)) continue;
        const label = labelFor(container);
        if (!label) continue;
        const found = classify(container);
        if (!found || !isVisible(found.el)) continue;
        out.push({
          label,
          kind: found.kind,
          el: found.el,
          options: optionsFor(found),
          members: membersOf(found),
        });
      }
      return out;
    },

    async fill(field, value) {
      if (field.kind !== "radio" && field.kind !== "checkbox" && hasValue(field.el)) {
        return { ok: false, reason: "already filled" };
      }
      switch (field.kind) {
        case "combobox":
          return fillCombobox(field.el, value);
        case "select":
          return selectOption(field.el, value)
            ? { ok: true }
            : { ok: false, reason: `no option reads "${value}"` };
        case "radio":
        case "checkbox":
          return chooseRadio(field.members, value)
            ? { ok: true }
            : { ok: false, reason: `no choice reads "${value}"` };
        default:
          return setControlValue(field.el, value)
            ? { ok: true }
            : { ok: false, reason: "the field rejected the value" };
      }
    },
  });
})();
