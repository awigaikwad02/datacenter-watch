// Projects map: vector U.S. base with state shading, clustered project pins, filters, list and detail panel.
(function () {
  const D = DCW, $ = (s) => document.querySelector(s);
  const US_BOUNDS = [[24.4, -125], [49.5, -66.9]];
  const STAGES = ["Announced", "Under construction", "Operational"];
  const CODE = Object.fromEntries(Object.entries(D.STATES).map(([k, v]) => [v, k]));

  const f = { q: "", stages: new Set(STAGES), co: "", st: "", mw: 0, curated: true, auto: true, shade: true, labels: true, sort: "mw", metric: "count" };
  let all = [], coBySlug = {}, news = [], matchCos = () => [], sel = null;
  let map, statesLayer, labelLayer, cluster, markers = {};

  D.chrome("projects.html");

  // ---------- Colors (Leaflet paths need real colors, not CSS variables) ----------
  function token(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function hex(c) {
    if (c.startsWith("#")) { const h = c.length === 4 ? c.replace(/#(.)(.)(.)/, "#$1$1$2$2$3$3") : c; return [1, 3, 5].map((i) => parseInt(h.substr(i, 2), 16)); }
    const m = c.match(/[\d.]+/g); return m ? m.slice(0, 3).map(Number) : [128, 128, 128];
  }
  function mix(a, b, t) { const A = hex(a), B = hex(b); return "rgb(" + A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(",") + ")"; }

  // ---------- Data prep ----------
  function jitter(id, amt) {
    let h = 0; for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) | 0;
    return [((h & 0xffff) / 0xffff - 0.5) * amt, (((h >>> 16) & 0xffff) / 0xffff - 0.5) * amt];
  }
  function prep(p, auto) {
    const o = Object.assign({}, p, { auto });
    if (auto) {
      const [a, b] = jitter(p.id, p.precision === "state" ? 2.2 : 0.25);
      o.lat = p.lat + a; o.lon = p.lon + b;
      o.companies = matchCos(p.name);
      o.t = new Date(p.published).getTime();
    } else {
      o.t = p.announced ? new Date(p.announced + "-01").getTime() : 0;
    }
    o.companies = o.companies || [];
    o.hay = [o.name, o.company, o.location, D.STATES[o.state], o.notes, o.companies.map((c) => (coBySlug[c] || {}).name).join(" ")].join(" ").toLowerCase();
    return o;
  }
  function visible(p, skip) {
    if (p.auto ? !f.auto : !f.curated) return false;
    if (skip !== "stage" && !f.stages.has(p.status)) return false;
    if (skip !== "co" && f.co && !p.companies.includes(f.co)) return false;
    if (skip !== "st" && f.st && p.state !== f.st) return false;
    if (f.mw && !(p.capacity_mw >= f.mw)) return false;
    if (f.q && !f.q.toLowerCase().split(/\s+/).every((w) => p.hay.includes(w))) return false;
    return true;
  }

  // ---------- Map ----------
  function initMap(topo) {
    map = L.map("map", { zoomControl: false, minZoom: 2, maxZoom: 13, zoomSnap: 0.25, maxBounds: [[5, -200], [78, -40]], worldCopyJump: false, preferCanvas: false });
    L.control.zoom({ position: "bottomright" }).addTo(map);
    map.attributionControl.setPrefix(false);
    map.createPane("states").style.zIndex = 250;
    map.createPane("labels").style.zIndex = 350;
    map.getPane("labels").style.pointerEvents = "none";

    const geo = topojson.feature(topo, topo.objects.states);
    statesLayer = L.geoJSON(geo, {
      pane: "states",
      style: stateStyle,
      onEachFeature: (ft, layer) => {
        const code = CODE[ft.properties.name];
        ft.properties.code = code;
        layer.on({
          mouseover: (e) => { e.target.setStyle({ weight: 2, color: token("--accent") }); e.target.bringToFront(); },
          mouseout: (e) => statesLayer.resetStyle(e.target),
          click: () => { f.st = f.st === code ? "" : code; if (f.st) map.flyToBounds(layer.getBounds(), { padding: [40, 40], duration: 0.8, maxZoom: 7 }); update(); },
        });
        layer.bindTooltip(() => stateTip(code), { sticky: true, className: "dc-tip", direction: "top", offset: [0, -8] });
      },
    }).addTo(map);
    statesLayer.getAttribution = () => "U.S. Census via us-atlas";

    setLabels();
    cluster = L.markerClusterGroup({
      showCoverageOnHover: false, maxClusterRadius: 44, spiderfyOnMaxZoom: true, disableClusteringAtZoom: 8,
      iconCreateFunction: (c) => {
        const n = c.getChildCount(), s = n < 10 ? 34 : n < 25 ? 40 : 46;
        return L.divIcon({ html: '<div class="cluster">' + n + "</div>", className: "", iconSize: [s, s] });
      },
    });
    map.addLayer(cluster);
    map.fitBounds(US_BOUNDS, { padding: [10, 10] });
    map.on("click", () => { if (sel) closeDetail(); });
  }
  function setLabels() {
    if (labelLayer) { map.removeLayer(labelLayer); labelLayer = null; }
    if (!f.labels) return;
    const kind = D.currentTheme() === "dark" ? "dark_only_labels" : "light_only_labels";
    labelLayer = L.tileLayer("https://{s}.basemaps.cartocdn.com/" + kind + "/{z}/{x}/{y}{r}.png", {
      pane: "labels", subdomains: "abcd", maxZoom: 19, opacity: 0.9,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);
  }

  let stateVals = {}, stateMax = 1;
  function computeStateVals() {
    stateVals = {};
    all.filter((p) => visible(p, "st")).forEach((p) => {
      const v = f.metric === "gw" ? (p.capacity_mw || 0) / 1000 : 1;
      stateVals[p.state] = (stateVals[p.state] || 0) + v;
    });
    stateMax = Math.max(0.001, ...Object.values(stateVals));
  }
  function stateStyle(ft) {
    const code = ft.properties.code || CODE[ft.properties.name];
    const v = stateVals[code] || 0;
    const land = token("--map-land"), acc = token("--accent"), line = token("--map-line");
    const t = f.shade && v ? 0.18 + 0.82 * Math.sqrt(v / stateMax) : 0;
    const on = f.st === code;
    return { pane: "states", color: on ? acc : line, weight: on ? 2.4 : 1, fillColor: t ? mix(land, acc, t * (D.currentTheme() === "dark" ? 0.75 : 0.55)) : land, fillOpacity: 1 };
  }
  function stateTip(code) {
    const ps = all.filter((p) => p.state === code && visible(p, "st"));
    const mw = ps.reduce((a, p) => a + (p.capacity_mw || 0), 0);
    return "<b>" + D.STATES[code] + "</b><small>" + ps.length + " project" + (ps.length === 1 ? "" : "s") + (mw ? " · " + D.fmtMW(mw) + " tracked" : "") + "</small>";
  }

  function pinSize(p) {
    if (p.auto) return 13;
    return p.capacity_mw ? Math.round(Math.min(36, 14 + Math.sqrt(p.capacity_mw) / 2.4)) : 15;
  }
  function makeMarker(p) {
    const s = pinSize(p), tone = p.auto ? "var(--st-detected)" : D.STATUS[p.status].tone;
    const icon = L.divIcon({
      className: "", iconSize: [s, s],
      html: '<div class="pin' + (p.auto ? " auto" : "") + (!p.auto && p.status === "Under construction" ? " pulse" : "") + '" style="--tone:' + tone + '"></div>',
    });
    const m = L.marker([p.lat, p.lon], { icon, riseOnHover: true, keyboard: true, title: p.name });
    m.bindTooltip("<b>" + D.esc(p.auto ? shortTitle(p.name) : p.name) + "</b><small>" + D.esc(p.status) + (p.capacity_mw ? " · " + D.fmtMW(p.capacity_mw) : "") + " · " + D.esc(placeName(p)) + "</small>", { className: "dc-tip", direction: "top", offset: [0, -s / 2] });
    m.on("click", (e) => { L.DomEvent.stopPropagation(e); select(p.id, false); });
    return m;
  }
  const shortTitle = (t) => (t.length > 70 ? t.slice(0, 68) + "…" : t);
  const placeName = (p) => (p.location || "").replace(/, US$/, "");

  // ---------- Rendering ----------
  function renderStageChips() {
    const counts = {};
    all.filter((p) => visible(p, "stage")).forEach((p) => { counts[p.status] = (counts[p.status] || 0) + 1; });
    $("#statusChips").innerHTML = STAGES.map((s) =>
      '<button class="chip" data-stage="' + s + '" style="--tone:' + D.STATUS[s].tone + '" aria-pressed="' + f.stages.has(s) + '"><span class="dot"></span>' + s + ' <span class="n">' + (counts[s] || 0) + "</span></button>").join("");
  }
  function renderSelects() {
    const cos = {};
    all.filter((p) => visible(p, "co")).forEach((p) => p.companies.forEach((c) => { cos[c] = (cos[c] || 0) + 1; }));
    $("#company").innerHTML = '<option value="">All companies</option>' + Object.values(coBySlug).filter((c) => cos[c.slug] || c.slug === f.co)
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((c) => '<option value="' + c.slug + '"' + (f.co === c.slug ? " selected" : "") + ">" + D.esc(c.name) + " (" + (cos[c.slug] || 0) + ")</option>").join("");
    const sts = {};
    all.filter((p) => visible(p, "st")).forEach((p) => { sts[p.state] = (sts[p.state] || 0) + 1; });
    $("#stateSel").innerHTML = '<option value="">All states</option>' + Object.keys(sts).concat(f.st && !sts[f.st] ? [f.st] : []).sort((a, b) => D.STATES[a].localeCompare(D.STATES[b]))
      .map((s) => '<option value="' + s + '"' + (f.st === s ? " selected" : "") + ">" + D.STATES[s] + " (" + (sts[s] || 0) + ")</option>").join("");
  }
  function renderStats(list) {
    const cur = list.filter((p) => !p.auto);
    const mw = cur.reduce((a, p) => a + (p.capacity_mw || 0), 0);
    const cells = [
      [cur.length, "Projects"],
      [mw ? (mw / 1000).toFixed(1) : "—", "GW tracked"],
      [cur.filter((p) => p.status === "Under construction").length, "Building"],
      [new Set(list.map((p) => p.state)).size, "States"],
    ];
    $("#miniStats").innerHTML = cells.map((c) => "<div><b>" + c[0] + "</b><span>" + c[1] + "</span></div>").join("");
  }
  function sorted(list) {
    const by = {
      mw: (a, b) => (b.capacity_mw || 0) - (a.capacity_mw || 0) || a.auto - b.auto || a.name.localeCompare(b.name),
      new: (a, b) => b.t - a.t,
      name: (a, b) => a.name.localeCompare(b.name),
      state: (a, b) => D.STATES[a.state].localeCompare(D.STATES[b.state]) || (b.capacity_mw || 0) - (a.capacity_mw || 0),
    }[f.sort];
    return list.slice().sort(by);
  }
  function renderList(list) {
    const cur = list.filter((p) => !p.auto).length;
    $("#listCount").textContent = list.length + " sites" + (list.length !== cur ? " · " + cur + " curated" : "") + (f.st ? " in " + D.STATES[f.st] : "");
    if (!list.length) {
      $("#list").innerHTML = '<div class="empty-state">' + D.icon("map") + "<b>No projects match</b>Try another stage, company or capacity.</div>";
      return;
    }
    $("#list").innerHTML = sorted(list).map((p) => {
      const tone = p.auto ? "var(--st-detected)" : D.STATUS[p.status].tone;
      const who = p.auto ? (p.source || "News") + " · " + D.ago(p.published) : p.company;
      return '<button class="proj' + (sel === p.id ? " sel" : "") + '" data-id="' + p.id + '" style="--tone:' + tone + '">' +
        '<span class="sdot' + (p.auto ? " auto" : "") + '"></span><span><b>' + D.esc(p.auto ? shortTitle(p.name) : p.name) + "</b><small>" + D.esc(placeName(p)) + " · " + D.esc(p.status) + "</small><small>" + D.esc(who || "") + "</small></span>" +
        '<span class="cap">' + (p.capacity_mw ? D.fmtMW(p.capacity_mw) : "") + "</span></button>";
    }).join("");
  }
  function renderMarkers(list) {
    cluster.clearLayers();
    const ms = list.map((p) => { markers[p.id] = markers[p.id] || makeMarker(p); return markers[p.id]; });
    cluster.addLayers(ms);
  }
  function renderLegend() {
    $("#legend").innerHTML = STAGES.map((s) => '<span class="lg"><i style="--tone:' + D.STATUS[s].tone + '"></i>' + s + "</span>").join("") +
      '<span class="lg"><i class="auto" style="--tone:var(--st-detected)"></i>Detected from news</span>' +
      (f.shade ? '<span class="lg" style="margin-top:4px">' + (f.metric === "gw" ? "GW" : "Projects") + ' per state</span><span class="grad"></span>' : "") +
      '<span class="lg" style="color:var(--faint)">Pin size = capacity</span>';
    $("#shadeMode").innerHTML = [["count", "Projects"], ["gw", "GW"]].map((m) => '<button data-metric="' + m[0] + '" aria-pressed="' + (f.metric === m[0]) + '">' + m[1] + "</button>").join("");
    $("#shadeMode").hidden = !f.shade;
  }

  function update() {
    const list = all.filter((p) => visible(p));
    computeStateVals();
    statesLayer.setStyle(stateStyle);
    renderStageChips();
    renderSelects();
    renderStats(list);
    renderList(list);
    renderMarkers(list);
    renderLegend();
  }

  // ---------- Detail ----------
  function related(p) {
    const stop = new Set(["data", "center", "centers", "campus", "project", "the", "and", "of", "ai", "us", "new"]);
    const words = p.auto ? [] : p.name.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 2 && !stop.has(w));
    const town = placeName(p).split(",")[0].toLowerCase();
    return news.map((n) => {
      const t = n.title.toLowerCase();
      let s = 0;
      if (p.auto && n.id === p.id) s += 100;
      if (words.length && words.every((w) => t.includes(w))) s += 6;
      if (town && t.includes(town)) s += 4;
      if (n.states && n.states.includes(p.state)) s += 1;
      const nc = matchCos(n.title);
      if (p.companies.some((c) => nc.includes(c))) s += 2;
      return [s, n];
    }).filter((x) => x[0] >= 4).sort((a, b) => b[0] - a[0] || b[1].published.localeCompare(a[1].published)).slice(0, 5).map((x) => x[1]);
  }
  function detailHTML(p) {
    const tone = p.auto ? "var(--st-detected)" : D.STATUS[p.status].tone;
    const step = D.STATUS[p.status] ? D.STATUS[p.status].step : 1;
    const cos = p.companies.map((c) => coBySlug[c]).filter(Boolean);
    const kv = [
      ["Capacity", p.capacity_mw ? D.fmtMW(p.capacity_mw) : "—"],
      ["Investment", p.investment_usd_b ? D.fmtMoney(p.investment_usd_b) : "—"],
      [p.auto ? "Reported" : "Announced", p.auto ? D.fmtDate(p.published) : p.announced ? D.fmtDate(p.announced + "-15", { month: "short", year: "numeric" }) : "—"],
      ["State", D.STATES[p.state] || "—"],
    ];
    const rel = related(p);
    return '<div class="detail-head" style="--tone:' + tone + '">' +
      '<span class="pill" style="--tone:' + tone + '"><span class="dot"></span>' + (p.auto ? "Detected · " : "") + D.esc(p.status) + "</span>" +
      "<h2>" + D.esc(p.name) + '</h2><div class="loc">' + D.icon("pin") + D.esc(placeName(p)) + (p.auto && p.precision !== "city" ? " (approximate)" : "") + "</div>" +
      '<button class="icon-btn close" id="closeDetail" aria-label="Close">' + D.icon("x") + "</button></div>" +
      '<div class="detail-body">' +
      '<div class="stepper" style="--tone:' + tone + '">' + STAGES.map((s, i) => '<div class="' + (i < step ? "on" : "") + '">' + s + "</div>").join("") + "</div>" +
      '<div class="kv">' + kv.map((k) => "<div><span>" + k[0] + "</span><b>" + k[1] + "</b></div>").join("") + "</div>" +
      (cos.length ? '<div><h4>Companies</h4><div class="co-chips">' + cos.map((c) => '<a class="co-chip" href="companies.html#' + c.slug + '" style="--tone:' + D.TYPES[c.type].tone + '"><span class="av">' + D.esc(D.initials(c)) + "</span>" + D.esc(c.name) + "</a>").join("") + "</div></div>" : "") +
      (p.notes ? "<div><h4>About</h4><p style=\"margin:0;font-size:14.5px;color:var(--text-2)\">" + D.esc(p.notes) + "</p></div>" : "") +
      (rel.length ? '<div><h4>Related headlines</h4><div class="headlines">' + rel.map((n) => '<a href="' + D.esc(n.link) + '" target="_blank" rel="noopener">' + D.esc(n.title) + "<small>" + D.esc(n.source) + " · " + D.ago(n.published) + "</small></a>").join("") + "</div></div>" : "") +
      (p.auto ? '<div class="note">Picked up automatically from a headline and placed at the ' + (p.precision || "place") + ' mentioned. ' + (p.source_url ? '<a href="' + D.esc(p.source_url) + '" target="_blank" rel="noopener">Read the story →</a>' : "") + "</div>"
        : '<div class="note">' + (p.verified ? "Checked against public sources." : "From public reporting; not yet verified against current sources.") + (p.source_url ? ' <a href="' + D.esc(p.source_url) + '" target="_blank" rel="noopener">Source →</a>' : "") + "</div>") +
      '<div style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn sm" href="index.html#q=' + encodeURIComponent(p.auto ? placeName(p).split(",")[0] : p.name.split(" (")[0]) + '">' + D.icon("news") + "Search the news</a>" +
      '<button class="btn sm" id="copyLink">' + D.icon("link") + "Copy link</button></div>" +
      "</div>";
  }
  function select(id, fromList) {
    const p = all.find((x) => x.id === id);
    if (!p) return;
    if (sel && markers[sel]) { const el = markers[sel].getElement(); if (el) el.querySelector(".pin").classList.remove("sel"); }
    sel = id;
    const det = $("#detail");
    det.innerHTML = detailHTML(p);
    det.classList.add("open");
    det.querySelector("#closeDetail").addEventListener("click", closeDetail);
    det.querySelector("#copyLink").addEventListener("click", () => {
      const url = location.href.split("#")[0] + "#p=" + id;
      (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(() => D.toast("Link copied"), () => D.toast(url));
    });
    history.replaceState(null, "", "#p=" + id);
    document.querySelectorAll(".proj.sel").forEach((e) => e.classList.remove("sel"));
    const row = document.querySelector('.proj[data-id="' + id + '"]');
    if (row) { row.classList.add("sel"); if (!fromList) row.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
    const m = markers[id];
    const go = () => {
      const target = Math.max(map.getZoom(), p.auto && p.precision === "state" ? 6 : 8);
      const wide = window.innerWidth >= 980;
      const pt = map.project([p.lat, p.lon], target).add([wide ? 200 : 0, wide ? 0 : 140]);
      map.flyTo(map.unproject(pt, target), target, { duration: 0.9 });
      setTimeout(() => { const el = m && m.getElement(); if (el) el.querySelector(".pin").classList.add("sel"); }, 950);
    };
    if (m && cluster.hasLayer(m)) cluster.zoomToShowLayer(m, go); else go();
    if (window.innerWidth < 980 && fromList) $(".map-wrap").scrollIntoView({ behavior: "smooth" });
  }
  function closeDetail() {
    $("#detail").classList.remove("open");
    if (sel && markers[sel]) { const el = markers[sel].getElement(); if (el) el.querySelector(".pin").classList.remove("sel"); }
    document.querySelectorAll(".proj.sel").forEach((e) => e.classList.remove("sel"));
    sel = null;
    history.replaceState(null, "", location.pathname + location.search);
  }

  // ---------- Events ----------
  function bind() {
    $("#q").addEventListener("input", D.debounce((e) => { f.q = e.target.value.trim(); update(); }, 160));
    $("#company").addEventListener("change", (e) => { f.co = e.target.value; update(); });
    $("#stateSel").addEventListener("change", (e) => {
      f.st = e.target.value; update();
      if (f.st) statesLayer.eachLayer((l) => { if (l.feature.properties.code === f.st) map.flyToBounds(l.getBounds(), { padding: [40, 40], maxZoom: 7, duration: 0.8 }); });
      else map.flyToBounds(US_BOUNDS, { duration: 0.8 });
    });
    $("#sort").addEventListener("change", (e) => { f.sort = e.target.value; renderList(all.filter((p) => visible(p))); });
    const mw = $("#mw");
    mw.addEventListener("input", () => { f.mw = Number(mw.value); $("#mwVal").textContent = f.mw ? "≥ " + D.fmtMW(f.mw) : "Any"; update(); });
    [["#lyCurated", "curated"], ["#lyAuto", "auto"], ["#lyShade", "shade"]].forEach(([id, k]) => $(id).addEventListener("change", (e) => { f[k] = e.target.checked; update(); }));
    $("#lyLabels").addEventListener("change", (e) => { f.labels = e.target.checked; setLabels(); });
    $("#statusChips").addEventListener("click", (e) => {
      const b = e.target.closest("[data-stage]");
      if (!b) return;
      const s = b.dataset.stage;
      if (f.stages.has(s) && f.stages.size === 1) STAGES.forEach((x) => f.stages.add(x));
      else if (f.stages.size === STAGES.length) { f.stages.clear(); f.stages.add(s); }
      else if (f.stages.has(s)) f.stages.delete(s); else f.stages.add(s);
      update();
    });
    $("#shadeMode").addEventListener("click", (e) => { const b = e.target.closest("[data-metric]"); if (b) { f.metric = b.dataset.metric; update(); } });
    $("#list").addEventListener("click", (e) => { const b = e.target.closest(".proj"); if (b) select(b.dataset.id, true); });
    const fit = $("#fit");
    fit.innerHTML = D.icon("focus");
    fit.addEventListener("click", () => { closeDetail(); f.st = ""; update(); map.flyToBounds(US_BOUNDS, { duration: 0.8 }); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sel) closeDetail(); });
    document.addEventListener("dcw:theme", () => { statesLayer.setStyle(stateStyle); setLabels(); });
  }

  // ---------- Boot ----------
  Promise.all([
    D.loadJSON("data/projects.json"), D.loadJSON("data/project_candidates.json"), D.loadJSON("data/companies.json"),
    D.loadJSON("data/news.json").catch(() => ({ items: [] })), D.loadJSON("data/us-states.json"),
  ]).then(([pj, cand, cos, nw, topo]) => {
    cos.companies.forEach((c) => { coBySlug[c.slug] = c; });
    matchCos = D.companyMatcher(cos.companies);
    news = nw.items || [];
    all = pj.projects.map((p) => prep(p, false))
      .concat((cand.projects || []).filter((c) => c.state && D.STATES[c.state]).map((c) => prep(c, true)));
    const co = location.hash.match(/co=([\w-]+)/);
    if (co && coBySlug[co[1]]) f.co = co[1];
    initMap(topo);
    bind();
    update();
    if (f.co) {
      const pts = all.filter((p) => visible(p)).map((p) => [p.lat, p.lon]);
      if (pts.length) map.fitBounds(pts, { padding: [60, 60], maxZoom: 7 });
    }
    const m = location.hash.match(/p=([\w-]+)/);
    if (m) setTimeout(() => select(m[1], false), 400);
    D.ready();
  }).catch((err) => {
    console.error(err);
    D.fail("Couldn't load the map data. Try reloading.");
  });
})();
