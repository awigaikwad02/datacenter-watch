// Project Atlas: clustered U.S. map, filters (panel on desktop, bottom sheet on mobile),
// a list synced with the filters and map viewport, and a deep-linkable detail panel.
(function () {
  "use strict";
  const R = RR, $ = (s) => document.querySelector(s);
  const STATUSES = Object.keys(R.STATUS);
  // Cancelled / Blocked projects and low-confidence pins are off by default.
  const DEFAULT_STATUSES = STATUSES.filter((s) => s !== R.CANCELLED);
  const f = { q: "", statuses: new Set(DEFAULT_STATUSES), low: false, company: "", state: "", year: "", kind: "", mw: 0, usd: 0, inView: true };
  let all = [], news = [], map, cluster, approx = null, markers = {}, sel = null, releaseSheet = null;
  R.shell("/atlas", "Project Atlas");
  $("#fitBtn").innerHTML = R.icon("focus");
  $("#sheetClose").innerHTML = R.icon("x");

  // ---------- Filtering ----------
  const hay = (p) => p._hay || (p._hay = [p.name, p.company, p.place, R.STATES[p.state], p.companies.join(" "), p.notes].join(" ").toLowerCase());
  function match(p, skip) {
    if (skip !== "status" && !f.statuses.has(p.status)) return false;
    if (!f.low && p.confidence === "low" && !p.approx) return false;
    if (skip !== "company" && f.company && !p.companies.includes(f.company)) return false;
    if (skip !== "state" && f.state && p.state !== f.state) return false;
    if (skip !== "year" && f.year && String(p.year) !== f.year) return false;
    if (f.kind && (f.kind === "curated") !== p.curated) return false;
    if (f.mw && !(p.capacity_mw >= f.mw)) return false;
    if (f.usd && !(p.investment_usd_b >= f.usd)) return false;
    if (f.q && !f.q.toLowerCase().split(/\s+/).every((w) => hay(p).includes(w))) return false;
    return true;
  }
  const filtered = (skip) => all.filter((p) => match(p, skip));

  // ---------- Controls ----------
  function options(id, counts, label, current, fmt, order) {
    const keys = Object.keys(counts).concat(current && !counts[current] ? [current] : []);
    keys.sort(order || ((a, b) => (fmt ? fmt(a) : a).localeCompare(fmt ? fmt(b) : b)));
    $(id).innerHTML = '<option value="">' + label + "</option>" + keys.map((k) => '<option value="' + R.esc(k) + '"' + (k === current ? " selected" : "") + ">" + R.esc(fmt ? fmt(k) : k) + " (" + (counts[k] || 0) + ")</option>").join("");
  }
  function tally(skip, key) {
    const c = {};
    filtered(skip).forEach((p) => [].concat(key(p)).forEach((v) => { if (v) c[v] = (c[v] || 0) + 1; }));
    return c;
  }
  function controls() {
    const sc = tally("status", (p) => p.status);
    const onlyOps = f.statuses.size === 1 && f.statuses.has("Operational");
    $("#statusChips").innerHTML = '<button class="chip quick" data-quick="Operational" aria-pressed="' + onlyOps + '">Operational only</button>' +
      STATUSES.map((s) => '<button class="chip" data-status="' + s + '" style="--tone:' + R.STATUS[s].tone + '" aria-pressed="' + f.statuses.has(s) + '"><span class="dot"></span>' + (s === R.CANCELLED ? "Cancelled" : s) + ' <span class="n">' + (sc[s] || 0) + "</span></button>").join("");
    $("#lowConf").checked = f.low;
    options("#company", tally("company", (p) => p.companies), "All companies", f.company);
    options("#state", tally("state", (p) => p.state), "All states", f.state, (s) => R.STATES[s] || s);
    options("#year", tally("year", (p) => (p.year ? String(p.year) : "")), "Any year", f.year, null, (a, b) => b - a);
    $("#kind").value = f.kind;
    $("#mwOut").textContent = f.mw ? "≥ " + R.fmtMW(f.mw) : "Any";
    $("#usdOut").textContent = f.usd ? "≥ $" + f.usd + "B" : "Any";
    $("#mw").value = f.mw;
    $("#usd").value = f.usd;
    const n = activeCount();
    document.querySelectorAll(".js-filters").forEach((b) => { b.innerHTML = R.icon("filter") + "Filters" + (n ? " · " + n : ""); });
  }
  function activeCount() {
    const statusChanged = f.statuses.size !== DEFAULT_STATUSES.length || DEFAULT_STATUSES.some((s) => !f.statuses.has(s));
    return [f.q, f.company, f.state, f.year, f.kind, f.mw, f.usd, f.low].filter(Boolean).length + (statusChanged ? 1 : 0);
  }

  // ---------- Map ----------
  function marker(p) {
    const m = window.L.marker([p.lat, p.lon], { icon: R.pinIcon(p, false), title: p.curated ? p.name : p.place, keyboard: true, riseOnHover: true });
    m.bindTooltip("<b>" + R.esc(p.curated ? p.name : short(p.name)) + "</b><small>" + R.esc(p.status) + (p.capacity_mw ? " · " + R.fmtMW(p.capacity_mw) : "") + " · " + R.esc(p.place) + "</small>", { className: "rr-tip", direction: "top", offset: [0, -12] });
    m.on("click", () => select(p.id, "map"));
    return m;
  }
  const short = (t) => (t.length > 80 ? t.slice(0, 78) + "…" : t);
  // City- and county-level sites are pins; state-level ones are summed into one approximate bubble per state.
  function drawMarkers(list) {
    cluster.clearLayers();
    cluster.addLayers(list.filter((p) => p.curated || !p.approx).map((p) => (markers[p.id] = markers[p.id] || marker(p))));
    approx.set(list);
  }

  // ---------- List and stats ----------
  function inBounds(p) { return !f.inView || !map || map.getBounds().pad(0.02).contains([p.lat, p.lon]); }
  function renderList() {
    const list = filtered();
    const shown = list.filter(inBounds).sort((a, b) => (b.capacity_mw || 0) - (a.capacity_mw || 0) || b.curated - a.curated || b.t - a.t);
    $("#listCount").textContent = f.inView ? shown.length + " in view · " + list.length + " total" : list.length + " projects";
    const cur = list.filter((p) => p.curated), mw = cur.reduce((a, p) => a + (p.capacity_mw || 0), 0);
    $("#miniStats").innerHTML = [[list.length, "Projects"], [mw ? (mw / 1000).toFixed(1) : "0", "GW curated"], [list.filter((p) => p.status === "Under construction").length, "Building"], [new Set(list.map((p) => p.state)).size, "States"]]
      .map((c) => "<div><b>" + c[0] + "</b><span>" + c[1] + "</span></div>").join("");
    if (!shown.length) {
      $("#list").innerHTML = '<div class="empty">' + R.icon("map") + "<b>" + (list.length ? "Nothing in this part of the map" : "No projects match") + "</b>" + (list.length ? "Zoom out, or untick “Only what's in view”." : "Loosen a filter or reset them.") + "</div>";
      return;
    }
    $("#list").innerHTML = shown.map((p) => {
      const who = p.curated ? p.company : (p.source || "News") + " · " + R.ago(p.published);
      return '<button class="proj-card" data-id="' + R.esc(p.id) + '"' + (sel === p.id ? ' aria-current="true"' : "") + ' style="--tone:' + R.status(p.status).tone + '">' +
        '<span class="sdot' + (p.curated ? "" : " auto") + '" aria-hidden="true"></span><span><b>' + R.esc(p.curated ? p.name : short(p.name)) + "</b><small>" + R.esc(p.place) + (p.approx ? " (approximate)" : "") + " · " + R.esc(p.status) + "</small><small>" + R.esc(who || "") + (p.stories > 1 ? " · " + p.stories + " sources" : "") + "</small></span>" +
        '<span class="cap">' + (p.capacity_mw ? R.fmtMW(p.capacity_mw) : p.investment_usd_b ? R.fmtMoney(p.investment_usd_b) : "") + "</span></button>";
    }).join("");
  }
  function update() {
    controls();
    drawMarkers(filtered());
    renderList();
    $("#legend").innerHTML = R.legendHTML();
  }

  // ---------- Detail panel ----------
  function related(p, source) {
    const town = p.place.split(",")[0].toLowerCase();
    return (source || news).map((n) => {
      let s = 0;
      if (own(p).has(n.id)) return [0, n]; // already listed under "News about this project"
      const sameState = n.state === p.state || (n.states || []).includes(p.state);
      if (sameState && p.companies.some((c) => n.companies.includes(c))) s += 6;
      if (town.length > 3 && n.title.toLowerCase().includes(town)) s += 5;
      if (p.curated && p.name.length > 6 && n.title.toLowerCase().includes(p.name.toLowerCase())) s += 8;
      return [s, n];
    }).filter((x) => x[0] >= 5).sort((a, b) => b[0] - a[0] || b[1].t - a[1].t).slice(0, source ? 8 : 6).map((x) => x[1]);
  }
  const own = (p) => p._own || (p._own = new Set((p.news || []).map((n) => n.id)));
  // Status timeline from the registry: every status change and event, each linked to the headline behind it.
  function statusTimeline(p) {
    const byId = Object.fromEntries((p.news || []).map((n) => [n.id, n]));
    const steps = (p.status_history || []).map((h) => Object.assign({ label: h.status, kind: "status" }, h))
      .concat((p.events || []).map((e) => Object.assign({ label: e.type, kind: "event" }, e)))
      .sort((a, b) => String(a.date).localeCompare(String(b.date)));
    if (!steps.length) return '<p class="co-empty">No status changes recorded yet.</p>';
    return '<ol class="milestones status-steps">' + steps.map((s) => {
      const n = byId[s.headline_id], tone = s.kind === "status" ? R.status(s.label).tone : "var(--faint)";
      const why = n ? '<br><a href="' + R.esc(n.link) + '" target="_blank" rel="noopener">' + R.esc(n.title) + "</a> <small>" + R.esc(n.source) + "</small>"
        : s.by === "curated" ? " <small>(curated)</small>" : s.by === "override" ? " <small>(correction)</small>" : "";
      return '<li style="--tone:' + tone + '"><time datetime="' + R.esc(s.date) + '">' + R.esc(R.fmtDate(s.date)) + "</time><div><span class=\"step-" + s.kind + '">' + R.esc(s.label) + "</span>" + why + "</div></li>";
    }).join("") + "</ol>";
  }
  function detailHTML(p) {
    const tone = R.status(p.status).tone, rel = related(p);
    const source = p.source_url || (rel[0] && rel[0].link);
    const kv = [["Capacity", p.capacity_mw ? R.fmtMW(p.capacity_mw) : "Not reported"], ["Investment", p.investment_usd_b ? R.fmtMoney(p.investment_usd_b) : "Not reported"],
      [p.curated ? "Announced" : "First reported", p.date ? R.fmtDate(p.date, p.curated ? { month: "short", year: "numeric" } : undefined) : "Not reported"], ["State", R.STATES[p.state] || p.state]];
    return '<div class="detail-head" style="--tone:' + tone + '"><span class="tag" style="--tone:' + tone + '"><span class="dot"></span>' + R.esc(p.status) + (p.curated ? " · Curated" : " · Detected") + "</span>" +
      '<h2 id="detailTitle">' + R.esc(p.name) + '</h2><div class="loc">' + R.icon("pin") + R.esc(p.place) + (!p.curated && p.precision && p.precision !== "city" ? " (approximate, " + R.esc(p.precision === "source" ? "outlet's home state" : p.precision + " level") + ")" : "") + "</div>" +
      '<button class="icon-btn close" id="closeDetail" aria-label="Close project details">' + R.icon("x") + "</button></div>" +
      '<div class="detail-body"><p>' + R.esc(R.summary(p)) + "</p>" +
      '<div class="kv">' + kv.map((k) => "<div><span>" + k[0] + "</span><b>" + R.esc(k[1]) + "</b></div>").join("") + "</div>" +
      (p.companies.length ? '<div><h3 class="sub-h">Companies</h3><div class="news-tags">' + p.companies.map((c) => '<a class="tag plain" href="/companies#' + encodeURIComponent(c) + '">' + R.icon("building") + R.esc(c) + "</a>").join("") + "</div></div>" : "") +
      (p.timeline && p.timeline.length ? '<div><h3 class="sub-h">Milestones</h3><ol class="milestones">' + p.timeline.slice().sort((a, b) => String(a.date).localeCompare(String(b.date))).map((m) =>
        '<li><time datetime="' + R.esc(m.date) + '">' + R.esc(R.fmtDate(m.date, m.date.length === 7 ? { month: "short", year: "numeric" } : undefined)) + "</time><div><span>" + R.esc(m.event) + "</span>" +
        (m.url ? '<br><a href="' + R.esc(m.url) + '" target="_blank" rel="noopener">' + R.esc(new URL(m.url).hostname.replace(/^www\./, "")) + " →</a>" : "") + "</div></li>").join("") + "</ol></div>" : "") +
      '<div><h3 class="sub-h">Status timeline</h3>' + statusTimeline(p) + "</div>" +
      (p.notes ? '<div><h3 class="sub-h">Notes</h3><p>' + R.esc(p.notes) + "</p></div>" : "") +
      '<div><h3 class="sub-h">News about this project</h3>' + ((p.news || []).length ? '<div class="headlines">' + p.news.map((n) => '<a href="' + R.esc(n.link) + '" target="_blank" rel="noopener">' + R.esc(n.title) + "<small>" + R.esc(n.source || "News") + " · " + R.esc(R.fmtDate(n.published)) + (n.stage_signal ? " · " + R.esc(n.stage_signal) : "") + "</small></a>").join("") + "</div>" : '<p class="co-empty">No headlines attached to this project yet.</p>') + "</div>" +
      '<div id="archiveRel" hidden></div>' +
      '<div><h3 class="sub-h">Related headlines</h3>' + (rel.length ? '<div class="headlines">' + rel.map((n) => '<a href="' + R.esc(n.link) + '" target="_blank" rel="noopener">' + R.esc(n.title) + "<small>" + R.esc(n.source) + " · " + R.ago(n.published) + "</small></a>").join("") + "</div>" : '<p class="co-empty">No matching headlines in the last 90 days.</p>') + "</div>" +
      '<div class="detail-actions">' + (source ? '<a class="btn sm" href="' + R.esc(source) + '" target="_blank" rel="noopener">' + R.icon("external") + "Latest source</a>" : "") +
      '<a class="btn sm" href="/projects/' + encodeURIComponent(p.id) + '/">' + R.icon("external") + "Project page</a>" +
      '<button class="btn sm" id="shareProject">' + R.icon("share") + "Share</button></div>" +
      '<div class="note">' + (p.curated ? (p.verified ? "Curated and checked against public sources." : "Curated from public reporting; not yet verified against current sources.") : (p.approx ? "Detected automatically from headlines that name only a state, so it is counted in the state's approximate bubble rather than pinned." : "Detected automatically from headlines (confidence: " + R.esc(p.confidence) + "). The pin sits at the place named, which can be off.")) + ' <a href="/methodology#report">Report a wrong pin</a>.</div></div>';
  }
  function setPin(id, on) {
    const p = all.find((x) => x.id === id), m = markers[id];
    if (p && m) m.setIcon(R.pinIcon(p, on));
  }
  function select(id, from) {
    const p = all.find((x) => x.id === id);
    if (!p) return;
    if (sel) setPin(sel, false);
    sel = id;
    const d = $("#detail");
    d.innerHTML = detailHTML(p);
    d.classList.add("open");
    $("#closeDetail").addEventListener("click", close);
    $("#shareProject").addEventListener("click", () => R.share(p.name + " · The Rack Report", location.href.split("#")[0] + "#project=" + encodeURIComponent(id)));
    history.replaceState(null, "", "#project=" + encodeURIComponent(id));
    archiveRelated(p);
    if (from !== "map") setTimeout(() => $("#closeDetail").focus(), 50);
    if ($("#atlas").classList.contains("list-view")) setMode("map");
    const m = markers[id];
    const go = () => {
      const z = Math.max(map.getZoom(), p.curated || p.precision === "city" ? 8 : 6);
      const wide = innerWidth >= 1024;
      const pt = map.project([p.lat, p.lon], z).add([wide ? 200 : 0, wide ? 0 : 120]);
      map.flyTo(map.unproject(pt, z), z, { duration: R.reducedMotion() ? 0 : 0.9 });
      setTimeout(() => setPin(id, true), R.reducedMotion() ? 0 : 950);
    };
    if (m && cluster.hasLayer(m)) cluster.zoomToShowLayer(m, go); else go();
    document.querySelectorAll(".proj-card[aria-current]").forEach((e) => e.removeAttribute("aria-current"));
    const row = document.querySelector('.proj-card[data-id="' + CSS.escape(id) + '"]');
    if (row) row.setAttribute("aria-current", "true");
  }
  function archiveRelated(p) {
    R.archive().then((a) => {
      if (sel !== p.id) return;
      const shown = new Set(news.map((n) => n.id).concat([...own(p)]));
      const rel = related(p, a.items.filter((n) => !shown.has(n.id)));
      const box = document.getElementById("archiveRel");
      if (!box || !rel.length) return;
      box.innerHTML = '<h3 class="sub-h">From the archive</h3><div class="headlines">' + rel.map((n) =>
        '<a href="' + R.esc(n.link) + '" target="_blank" rel="noopener">' + R.esc(n.title) + "<small>" + R.esc(n.source) + " · " + R.esc(R.fmtDate(n.published)) + "</small></a>").join("") + "</div>";
      box.hidden = false;
      box.parentNode.insertBefore(box, box.nextElementSibling.nextElementSibling);
    }).catch(() => {});
  }
  function close() {
    const d = $("#detail");
    if (!d.classList.contains("open")) return;
    d.classList.remove("open");
    if (sel) {
      setPin(sel, false);
      const row = document.querySelector('.proj-card[data-id="' + CSS.escape(sel) + '"]');
      if (row) { row.removeAttribute("aria-current"); row.focus(); }
    }
    sel = null;
    history.replaceState(null, "", location.pathname);
  }

  // ---------- Mobile: list/map toggle and filter sheet ----------
  function setMode(mode) {
    $("#atlas").classList.toggle("list-view", mode === "list");
    document.querySelectorAll("[data-mode]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
    if (mode === "list") { f.inView = false; $("#inView").checked = false; renderList(); }
    if (mode === "map") setTimeout(() => map.invalidateSize(), 50);
  }
  function openSheet() {
    const sheet = $("#sheet");
    sheet.hidden = false;
    $("#sheetBody").appendChild($("#filterPanel"));
    $("#sheetApply").textContent = "Show " + filtered().length + " projects";
    requestAnimationFrame(() => { sheet.classList.add("open"); $("#sheetBack").classList.add("open"); });
    releaseSheet = R.trapFocus(sheet, closeSheet);
  }
  function closeSheet() {
    const sheet = $("#sheet");
    sheet.classList.remove("open");
    $("#sheetBack").classList.remove("open");
    $("#panelHome").appendChild($("#filterPanel"));
    if ($("#atlas").classList.contains("list-view")) renderList();
    if (releaseSheet) { releaseSheet(); releaseSheet = null; }
    setTimeout(() => { sheet.hidden = true; }, 350);
  }

  // ---------- Events ----------
  function changed() {
    update();
    if ($("#sheet").classList.contains("open")) $("#sheetApply").textContent = "Show " + filtered().length + " projects";
  }
  function reset() {
    Object.assign(f, { q: "", company: "", state: "", year: "", kind: "", mw: 0, usd: 0, low: false });
    f.statuses = new Set(DEFAULT_STATUSES);
    $("#q").value = "";
    changed();
  }
  function bind() {
    $("#q").addEventListener("input", R.debounce((e) => { f.q = e.target.value.trim(); changed(); }, 150));
    ["company", "state", "year", "kind"].forEach((k) => $("#" + k).addEventListener("change", (e) => {
      f[k] = e.target.value;
      changed();
      if (k === "state" || k === "company") fitTo(filtered());
    }));
    $("#mw").addEventListener("input", (e) => { f.mw = Number(e.target.value); changed(); });
    $("#usd").addEventListener("input", (e) => { f.usd = Number(e.target.value); changed(); });
    $("#inView").addEventListener("change", (e) => { f.inView = e.target.checked; renderList(); });
    $("#resetFilters").addEventListener("click", reset);
    $("#lowConf").addEventListener("change", (e) => { f.low = e.target.checked; changed(); });
    $("#statusChips").addEventListener("click", (e) => {
      const q = e.target.closest("[data-quick]");
      if (q) {
        const on = f.statuses.size === 1 && f.statuses.has(q.dataset.quick);
        f.statuses = on ? new Set(DEFAULT_STATUSES) : new Set([q.dataset.quick]);
        changed();
        const nq = document.querySelector("#statusChips [data-quick]");
        if (nq) nq.focus();
        return;
      }
      const b = e.target.closest("[data-status]");
      if (!b) return;
      const s = b.dataset.status;
      // Each chip toggles its status; Cancelled is just another chip, off by default.
      if (f.statuses.has(s)) { f.statuses.delete(s); if (!f.statuses.size) f.statuses = new Set(DEFAULT_STATUSES); }
      else f.statuses.add(s);
      changed();
      const nb = document.querySelector('#statusChips [data-status="' + s + '"]');
      if (nb) { nb.classList.add("pop"); nb.focus(); }
    });
    $("#list").addEventListener("click", (e) => { const b = e.target.closest(".proj-card"); if (b) select(b.dataset.id, "list"); });
    $("#fitBtn").addEventListener("click", () => { close(); map.flyToBounds(R.US.view, { duration: R.reducedMotion() ? 0 : 0.8 }); });
    document.querySelectorAll(".js-filters").forEach((b) => b.addEventListener("click", openSheet));
    $("#sheetClose").addEventListener("click", closeSheet);
    $("#sheetApply").addEventListener("click", closeSheet);
    $("#sheetReset").addEventListener("click", reset);
    $("#sheetBack").addEventListener("click", closeSheet);
    document.addEventListener("click", (e) => { const b = e.target.closest("[data-mode]"); if (b) setMode(b.dataset.mode); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#sheet").classList.contains("open")) close(); });
    map.on("moveend", R.debounce(renderList, 80));
    window.addEventListener("hashchange", readHash);
  }
  function fitTo(list) {
    if (!list.length) return;
    map.fitBounds(list.map((p) => [p.lat, p.lon]), { padding: [60, 60], maxZoom: 7 });
  }
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    if (h.get("company")) {
      const want = h.get("company").toLowerCase().replace(/-/g, " ");
      f.company = Object.keys(window.RR_COMPANIES).find((n) => n.toLowerCase() === want) || h.get("company");
      changed(); fitTo(filtered());
    }
    if (h.get("state")) { f.state = h.get("state").toUpperCase(); changed(); fitTo(filtered()); }
    if (h.get("project")) setTimeout(() => select(h.get("project"), "hash"), 250);
  }

  Promise.all([R.projects(), R.news().catch(() => ({ items: [] })), R.loadLeaflet()]).then(([projects, n]) => {
    all = projects;
    news = n.items;
    map = R.baseMap($("#map"));
    window.L.control.zoom({ position: "bottomright" }).addTo(map);
    cluster = R.clusterGroup();
    map.addLayer(cluster);
    approx = R.approxLayer(map, cluster, (st) => { f.state = st; changed(); fitTo(filtered()); });
    bind();
    update();
    readHash();
    // New data: redraw pins and list with the same filters, zoom and open panel. Markers are
    // rebuilt so status changes show, except the selected one, which keeps its highlight.
    R.live((n, projects) => {
      all = projects;
      news = n.items;
      markers = sel && markers[sel] ? { [sel]: markers[sel] } : {};
      update();
    });
    R.ready();
  }).catch((err) => {
    console.error(err);
    $("#list").innerHTML = '<div class="empty">' + R.icon("alert") + "<b>Couldn't load the Atlas</b>Check your connection and reload. The map library loads from unpkg.com.</div>";
    R.ready();
  });
})();
