# Job Sentinel (Browser Extension)

One-click job clipping for Chrome and Firefox. Navigate to any job posting, click the
extension, review the auto-filled fields, and save the role straight into your local
Job Sentinel application tracker. No account, no cloud service — everything stays on
your machine.

## What it does

- Extracts job details from the current page (title, company, location, salary, URL).
- Displays them in editable fields so you can correct anything before saving.
- POSTs to your locally running Job Sentinel API (`http://127.0.0.1:8000`).
- Shows a success state with a direct link to the web dashboard.

Extraction is best-effort and prioritised:

1. **schema.org `JobPosting` JSON-LD** — covers LinkedIn, Greenhouse, Lever, Indeed,
   Workday, and most modern ATS boards.
2. **OpenGraph tags + common DOM selectors** — fallback for pages without structured data.

All fields are optional and user-editable before saving, so partial extraction is fine.

## Filling an application

The second half of the extension types an application form for you from the
answer bank you keep in Job Sentinel (`job-sentinel answers init` to start one).

Open the form, click the extension, then **Fill this application**. The overlay
appears bottom-right and does two things in order:

1. **Find fields.** It reads every visible label on screen and sends them, in
   one request, to `POST /api/answers/match`. It then shows a plan: each label,
   the value that would go into it, and the reason for anything it is leaving
   alone. Nothing has been typed at this point.
2. **Fill these.** Only on this second click does it write values, one field at
   a time, reporting what landed and what the form rejected.

What it will not do:

- **Submit.** It halts on the review step and says so. Reading the summary and
  pressing submit stays with you.
- **Answer a judgement call.** Anything listed as `private` in the answer bank
  (GPA, address, "why this company") never leaves the API, so the overlay shows
  it as yours to fill.
- **Overwrite.** A field that already holds a value is left as it is.
- **Hold a permission you did not grant.** The filler scripts are injected when
  you click the button, under `activeTab`. The extension declares no content
  scripts and no host permissions beyond your local API.

## Filling without the extension

The same adapters run from a Claude Code session, which is the route when you
want several applications opened and prefilled in a row rather than one form at
a time. Run `/fill-application <url>` in a session with this repository open.

Under the hood the session loads `extension/fill/*.js` from the running local
API (`GET /fill/<name>`) into the page, calls `__jsFill.labels()` to read the
questions, resolves them against `POST /api/answers/match` **from the shell**,
and calls `__jsFill.apply()` with the values.

The network hop stays outside the page on purpose. A page on an employer's
domain cannot read the answer bank: CORS allows local origins only, and
widening that would let any site you visit read your personal data. Loading a
script by URL is not a cross-origin read, so the page gets the code and Claude
keeps the data.

What still cannot be automated, by anyone: creating the account, email or SMS
verification, CAPTCHAs, and the submit click. Claude will not do those.

### Why values are set the way they are

Assigning `input.value = x` does not fire React's listeners, so a React-rendered
form keeps its old state and reverts the field on blur. That is why Simplify's
autofill appears to work and then silently loses half the form. The filler goes
through the native value setter on the element prototype and dispatches the
events React listens for (`extension/fill/dom.js`). Dropdowns on Workday are not
`<select>` elements either, so filling one means clicking the button, waiting for
the listbox, and clicking the option.

### Adding an adapter

Adapters live in `extension/fill/adapters/`. One is an object with six members,
documented in `extension/fill/registry.js`:

```js
ns.registerAdapter({
  id: "greenhouse",
  label: "Greenhouse",
  matches(location) { ... },   // is this page mine?
  isReviewPage() { ... },      // true halts the filler
  scan() { ... },              // -> [{ label, kind, el, options }]
  async fill(field, value) { ... },  // -> { ok, reason? }
});
```

`extension/fill/test-form.html` is a stand-in application form covering the cases
that break adapters: a Workday-style dropdown that opens late, a radio group with
a legend, a radio group with nothing naming it, and a hidden field. Serve the
`fill/` directory over HTTP and drive the adapters from the page console rather
than developing against an employer's live form.

Known gap: Greenhouse renders its School and Degree pickers as unlabelled search
inputs over a hidden `<select>`, so the generic adapter skips them. They need a
Greenhouse adapter; until then you fill those two by hand.

`scan()` must report the **visible label text**, not a selector. Selectors break
on every ATS redeploy; the words the applicant reads do not. Register the file in
`FILLER_FILES` in `popup.js`, before `fill/content.js` and before the generic
adapter, which must stay last so a real adapter always wins.

## Prerequisites

Job Sentinel must be running locally before you click "Track this job":

```
job-sentinel web      # starts the API + Next.js UI together
# or
job-sentinel serve    # API only (http://127.0.0.1:8000)
```

## Loading the extension

### Chrome / Chromium / Edge

1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable **Developer mode** (toggle, top-right).
3. Click **Load unpacked**.
4. Select the `extension/` folder inside this repository.
5. The "Job Sentinel" extension appears in your toolbar.

### Firefox

1. Open `about:debugging`.
2. Click **This Firefox** in the left sidebar.
3. Click **Load Temporary Add-on…**.
4. Navigate to the `extension/` folder and select `manifest.json`.

> **Note:** Firefox temporary add-ons are removed when the browser restarts. For a
> persistent install, the extension would need to be signed via AMO.

## Settings

Click the **Settings** link at the bottom of the popup to change the API base URL if
you run Job Sentinel on a non-default port. The setting is stored in
`chrome.storage.local` and persists across browser restarts.

## Privacy

This extension communicates **only** with your local Job Sentinel instance
(`http://127.0.0.1:8000` by default). No data is sent to any remote server. No
analytics, no telemetry. The source is plain JS with no build step — read it.
