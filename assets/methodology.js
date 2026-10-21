// Methodology: static content; shell and reveal only.
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
  R.ready();
})();
