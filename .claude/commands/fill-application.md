---
description: Open an application form in the browser and fill it from the answer bank, stopping before submit.
---

Fill the application form at $ARGUMENTS (or the page already open, if no URL was
given) from the Job Sentinel answer bank.

The network hop stays with you. A page on an employer's domain must never be
able to read the answer bank itself: the API only allows local origins, and
widening that would let any site the user visits read their personal data.

## The loop

1. **Make sure the API is up.** `curl -s -o /dev/null -w "%{http_code}"
   http://127.0.0.1:8000/api/answers`. If it is not 200, start it with
   `job-sentinel serve` in the background.

2. **Open the page.** Use Claude in Chrome when the form needs the user's own
   sign-in, which Workday and most ATS accounts do. The built-in browser pane
   has no sign-ins. Do not create an account, type a password, or solve a
   CAPTCHA: hand those back to the user.

3. **Inject the filler**, in one `javascript_tool` call:

   ```js
   for (const f of ["dom.js","registry.js","adapters/workday.js","adapters/generic.js","claude.js"]) {
     await new Promise((res, rej) => {
       const s = document.createElement("script");
       s.src = "http://127.0.0.1:8000/fill/" + f;
       s.onload = res; s.onerror = rej;
       document.head.appendChild(s);
     });
   }
   window.__jsFill.labels()
   ```

   `labels()` returns `{adapter, review, fields:[{i, label, kind, options}]}`.
   **If `review` is true, stop.** Tell the user it is the review step, and that
   reading it and pressing submit is theirs.

4. **Resolve the labels** by calling the API from the shell, never from the page:

   ```bash
   curl -s -X POST http://127.0.0.1:8000/api/answers/match \
     -H "Content-Type: application/json" \
     -d '{"labels": ["...", "..."]}'
   ```

   Build a plan of `{i, candidates}` from the response. Skip anything with
   `private: true` or an empty `value`: those are the user's to answer. The
   `options` are alternate phrasings, tried in order, which is how a dropdown
   worded differently from the stored answer still lands.

5. **Fill** with `await window.__jsFill.apply(plan)`, then report per field what
   landed and what did not. Re-run `labels()` before any second `apply()`:
   indexes come from one scan.

6. **Stop.** Never click submit, continue, or next. List for the user what is
   still theirs to fill, then hand the page back.

## Report

Say which fields were filled, which were skipped and why, and what the user
still has to do before submitting. Do not claim a field was filled unless the
result for it came back `ok: true`.
