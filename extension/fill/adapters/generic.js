/**
 * generic.js — the fallback adapter: plain HTML form semantics.
 *
 * It reads labels the way a screen reader does, through `label[for]`,
 * `aria-label`, `aria-labelledby` and the nearest legend. That covers
 * Greenhouse, Lever, Ashby, SmartRecruiters and Microsoft's own ATS well
 * enough to be useful, and anything it gets wrong shows up in the overlay
 * before a single character is typed.
 *
 * It registers last, so a real adapter always wins.
 */

"use strict";

(() => {
  const ns = window.__jsFill;
  const { cleanLabel, visibleText, isVisible, hasValue } = ns;
  const { setControlValue, selectOption, chooseRadio } = ns;

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
    const aria = el.getAttribute("aria-label");
    if (aria) return cleanLabel(aria);
    if (el.id) {
      const tag = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (tag) return visibleText(tag);
    }
    const wrapping = el.closest("label");
    if (wrapping) return visibleText(wrapping);
    const legend = el.closest("fieldset")?.querySelector("legend");
    if (legend) return visibleText(legend);
    return cleanLabel(el.getAttribute("placeholder") || el.name || "");
  }

  /** The element that names a radio or checkbox group, if anything does. */
  function groupOf(el) {
    if (el.type !== "radio" && el.type !== "checkbox") return null;
    return el.closest("fieldset, [role='radiogroup'], [role='group']");
  }

  /**
   * The question a radio or checkbox group asks.
   *
   * Never the text beside one choice: labelling the field "Yes" would have the
   * answer bank match the wrong question and tick the wrong box. When nothing
   * names the group, fall back to the control's `name` and let the overlay
   * report it as unanswered rather than guess.
   */
  function groupLabel(group, el) {
    const legend = group.querySelector?.("legend");
    if (legend) {
      const text = visibleText(legend);
      if (text) return text;
    }
    const by = group.getAttribute?.("aria-labelledby");
    if (by) {
      const text = by
        .split(/\s+/)
        .map((id) => visibleText(document.getElementById(id)))
        .filter(Boolean)
        .join(" ");
      if (text) return text;
    }
    const aria = group.getAttribute?.("aria-label");
    if (aria) return cleanLabel(aria);
    return cleanLabel(el.name || "");
  }

  function kindOf(el) {
    if (el.tagName === "SELECT") return "select";
    if (el.tagName === "TEXTAREA") return "textarea";
    if (el.type === "radio") return "radio";
    if (el.type === "checkbox") return "checkbox";
    return "text";
  }

  ns.registerAdapter({
    id: "generic",
    label: "generic HTML form",

    matches() {
      return true;
    },

    isReviewPage() {
      const headings = document.querySelectorAll("h1, h2, h3, [role='heading']");
      return Array.from(headings).some((h) => /^review\b/i.test(visibleText(h)));
    },

    scan() {
      const out = [];
      const seen = new Set();
      for (const el of document.querySelectorAll(CONTROLS)) {
        if (!isVisible(el) || el.disabled || el.readOnly) continue;

        if (el.type === "radio" || el.type === "checkbox") {
          const name = el.name || "";
          const key = `${el.type}:${name || el.id}`;
          if (seen.has(key)) continue;
          seen.add(key);

          // A group with nothing naming it gets its control name as the label.
          // That rarely matches the bank, which is the point: a mislabelled
          // group would tick a box against the wrong question.
          const group = groupOf(el);
          const scope = group || el.form || document.body;
          const label = group ? groupLabel(group, el) : cleanLabel(name);
          if (!label) continue;
          const members = name
            ? Array.from(scope.querySelectorAll(`input[name="${CSS.escape(name)}"]`))
            : [el];
          out.push({
            label,
            kind: kindOf(el),
            el: scope,
            options: members.map((m) => labelFor(m)).filter(Boolean),
            members,
          });
          continue;
        }

        const label = labelFor(el);
        if (!label) continue;
        const options =
          el.tagName === "SELECT"
            ? Array.from(el.options)
                .map((o) => cleanLabel(o.textContent))
                .filter(Boolean)
            : [];
        out.push({ label, kind: kindOf(el), el, options });
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
