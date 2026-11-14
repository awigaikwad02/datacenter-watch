// Methodology: static content; shell and reveal only.
// Loaded by methodology.html (/methodology), after assets/companies.js and assets/app.js.
// Reads data/status.json (RR.freshness) for the "Last data update" line in #runStatus, and
// data/health.json (fetched fresh, skipping caches) for the site health summary in #siteHealth.
// Uses window.RR; exports nothing and defines no named functions.
(function () {
  "use strict";
  const R = RR;
  R.shell("/methodology", "Methodology");
  // Status line from data/status.json, which the fetcher writes on every run that changes the data.
  const el = document.getElementById("runStatus");
  R.freshness().then((st) => {
    if (!el || !st.updated) return;
    el.innerHTML = "Last data update: <b>" + R.esc(R.fmtDate(st.updated)) + "</b> (" + R.esc(R.ago(st.updated)) + ") · <b>" + R.fmtN(st.items_total) + "</b> headlines · <b>" +
      R.fmtN(st.feeds_ok) + "</b> of " + R.fmtN(st.feeds_total) + " feeds returned data · " + R.fmtN(st.items_new) + " new that run";
  }).catch(() => { if (el) el.textContent = "The latest run report could not be loaded."; });

  // Site health from data/health.json, written by the daily health check (scripts/healthcheck.py
  // and scripts/healthcheck_browser.mjs).
  const box = document.getElementById("siteHealth");
  fetch("data/health.json?t=" + Date.now(), { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).then((h) => {
    if (!box || !h || !Array.isArray(h.checks)) return;
    const failing = h.checks.filter((c) => c.status === "fail");
    const when = h.browser_checked_at && h.browser_checked_at > h.checked_at ? h.browser_checked_at : h.checked_at;
    box.innerHTML = "Site health: " + (failing.length
      ? '<b class="bad">' + failing.length + " of " + h.checks.length + " checks failing</b>"
      : '<b class="ok">all ' + h.checks.length + " checks passing</b>") +
      " · last checked " + R.esc(R.fmtDate(when)) + " (" + R.esc(R.ago(when)) + ")" +
      (failing.length ? "<ul>" + failing.map((c) => "<li>" + R.esc(c.name) + ": " + R.esc(c.value) + (c.detail ? " <small>(" + R.esc(c.detail) + ")</small>" : "") + "</li>").join("") + "</ul>" : "");
    box.hidden = false;
  }).catch(() => {});
  R.ready();
})();
