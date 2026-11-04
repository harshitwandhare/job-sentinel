---
description: Find the latest postings, screen them, then open and prefill each one. Stops before submit.
---

Run the whole apply loop for $ARGUMENTS (a search, e.g. "software engineer intern
summer 2027"). If no search was given, work from what is already queued.

## 1. Find and queue

Start the API if it is not up (`curl -s -o /dev/null -w "%{http_code}"
http://127.0.0.1:8000/health`; start with `job-sentinel serve` in the
background).

```bash
job-sentinel apply find --keywords "<search>" --days 7
```

This searches every enabled source, re-reads each posting through the board
that actually serves it, drops anything the posting itself rules out, skips
anything already tracked in any stage, and saves the rest as queued
applications. Report the blocked ones with the sentence each was blocked on:
a wrong screen should be visible, not silent.

`job-sentinel apply queue` lists what is waiting.

## 2. Open and prefill, one posting at a time

Use Claude in Chrome when the form needs the user's sign-in, which Workday
does. Never create an account, type a password, or solve a CAPTCHA.

**Load the filler.** Try the cheap route first:

```js
for (const f of ["dom.js","registry.js","adapters/workday.js","adapters/greenhouse.js","adapters/lever.js","adapters/ashby.js","adapters/generic.js","claude.js"]) {
  await new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = "http://127.0.0.1:8000/fill/" + f;
    s.onload = res; s.onerror = () => rej(new Error("blocked: " + f));
    document.head.appendChild(s);
  });
}
window.__jsFill.labels()
```

Greenhouse and some others ship a Content-Security-Policy that blocks both a
script tag and a fetch to localhost. When the load fails, read the bundle with
`curl -s "http://127.0.0.1:8000/fill/bundle.js?min=1"` and paste it as the body
of one `javascript_tool` call instead. Evaluation through the browser tools is
not subject to CSP.

**Read the questions.** `labels()` returns `{adapter, review, fields:[{i, label,
kind, options}]}`. If `review` is true, stop: that is the review step, and
reading it and submitting are the user's.

**Resolve them from the shell**, never from the page:

```bash
curl -s -X POST http://127.0.0.1:8000/api/answers/match \
  -H "Content-Type: application/json" \
  -d '{"ats": "<adapter id>", "labels": ["...", "..."]}'
```

Build `[{i, candidates}]` from the response. Skip `private: true` and empty
values: those are the user's. `options` are alternate phrasings, tried in
order. Pass the adapter id as `ats` so learned wordings are scoped correctly.

**Fill** with `await window.__jsFill.apply(plan)`.

## 3. Finish the dropdowns a script cannot

A result of `needs a real click: this dropdown ignores synthetic input` is not
a bug. Greenhouse and Ashby dropdowns only open on a trusted gesture, and a
dispatched event is marked untrusted. Finish those with real input:

1. `window.__jsFill.locate(i)` gives the field's centre coordinates.
2. Click there with the `computer` tool, type the value for real.
3. `window.__jsFill.openOptions()` lists the visible options with coordinates.
4. Click the right one.

## 4. Learn what was missed

For every label that came back with no `field_id`, decide whether the answer
bank already holds the answer under different words. If it does, teach it:

```bash
job-sentinel answers learn "<the form's wording>" <field_id> --ats <adapter id>
```

Next time that wording resolves without asking. If the bank genuinely has no
answer, say so and leave it: do not invent one.

## 5. Hand back

Mark the application as filled in the tracker
(`job-sentinel apps stage <id> applied` only after the user submits, not
before). Tell the user, per posting: what was filled, what is still theirs,
and that submit is theirs. Never click submit, continue, or next.

Do not claim a field was filled unless its result came back `ok: true`.
