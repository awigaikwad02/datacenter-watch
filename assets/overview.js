// Overview: metrics, major story, ticker, latest headlines, project pulse map, active companies and topics.
// Loaded by index.html (/), after assets/companies.js and assets/app.js.
// Reads data/news.json (RR.news) and data/registry.json (RR.projects). Leaflet loads only when the
// pulse map nears the viewport. Uses window.RR (and window.L once loaded); exports nothing.
// Everything is redrawn when live refresh brings new data (RR.live).
(function () {
  "use strict";
  // R is window.RR; $ is a querySelector shorthand.
  const R = RR, $ = (s) => document.querySelector(s), DAY = R.DAY;
  R.shell("/", "Overview");
  document.querySelectorAll("[data-icon]").forEach((a) => a.insertAdjacentHTML("afterbegin", R.icon(a.dataset.icon)));

  /**
   * Fills #stats with four count-up tiles: headlines this week, projects announced this month,
   * states with activity (30 days) and MW mentioned this week.
   * @param {object[]} raw every headline  @param {object[]} items headlines grouped into stories
   * @param {object[]} projects registry projects
   */
  function stats(raw, items, projects) {
    const now = Date.now(), d = new Date();
    const week = raw.filter((i) => now - i.t <= 7 * DAY);
    const monthStart = new Date(d.getFullYear(), d.getMonth(), 1).getTime();
    // Projects are already one per story cluster; cancelled or blocked sites never count as announced.
    // Registry records first seen this month, as shown on the map by default: not cancelled,
    // not low confidence, and pinned to a place (umbrellas without a named site are left out).
    const announced = projects.filter((p) => (p.status === "Announced" || p.status === "Planned") && !p.approx && p.confidence !== "low" && p.t >= monthStart).length;
    const states = new Set(items.filter((i) => now - i.t <= 30 * DAY && i.state).map((i) => i.state)
      .concat(projects.filter((p) => !p.curated && now - p.t <= 30 * DAY).map((p) => p.state))).size;
    const mw = items.filter((i) => now - i.t <= 7 * DAY && i.category !== R.CANCELLED).reduce((a, i) => a + (i.capacity_mw || 0), 0);
    const tiles = [
      ["news", "Headlines this week", week.length, "", "var(--cyan)", "from " + new Set(week.map((i) => i.source)).size + " outlets"],
      ["spark", "Projects announced this month", announced, "", "var(--st-announced)", "curated and detected, since " + new Date(monthStart).toLocaleDateString("en-US", { month: "short", day: "numeric" })],
      ["pin", "States with activity", states, "", "var(--accent)", "in headlines or projects, last 30 days"],
      ["zap", "MW mentioned this week", mw, "MW", "var(--c-power)", "capacity figures in headlines"],
    ];
    $("#stats").innerHTML = tiles.map((t) =>
      '<div class="card stat" style="--tone:' + t[4] + ";--glow:color-mix(in srgb," + t[4] + ' 22%,transparent)"><div class="stat-label">' + R.icon(t[0]) + t[1] +
      '</div><div class="stat-value" data-v="' + t[2] + '" data-u="' + t[3] + '">0</div><div class="stat-hint">' + t[5] + "</div></div>").join("");
    $("#stats").querySelectorAll(".stat-value").forEach((el) => {
      const v = Number(el.dataset.v), u = el.dataset.u;
      R.countUp(el, v, (x) => (u && v >= 1000 ? (x / 1000).toFixed(1) + "<small>GW</small>" : R.fmtN(x) + (u ? "<small>" + u + "</small>" : "")));
    });
  }

  /**
   * Fills #major with the latest major story (an announcement or construction story with a state and
   * a size figure, else the newest) and up to four "Also moving" stories. Cancelled stories are skipped.
   */
  function major(items) {
    const live = items.filter((i) => i.category !== R.CANCELLED);
    const pick = live.find((i) => (i.category === "New Announcement" || i.category === "Construction") && i.state && (i.capacity_mw || i.investment_usd_b)) || live[0];
    if (!pick) { $("#major").innerHTML = '<div class="card empty">' + R.icon("news") + "<b>No headlines yet</b>The feed refreshes every hour.</div>"; return; }
    const c = R.cat(pick.category);
    // Other recent stories that name a place or a company, newest first.
    const also = live.filter((i) => i !== pick && i.category !== "General" && i.category !== "Policy / Permits" && (i.state || i.companies.length)).slice(0, 4);
    const figs = [];
    if (pick.capacity_mw) figs.push(["Capacity", R.fmtMW(pick.capacity_mw)]);
    if (pick.investment_usd_b) figs.push(["Investment", R.fmtMoney(pick.investment_usd_b)]);
    if (pick.state) figs.push(["State", R.STATES[pick.state]]);
    $("#major").innerHTML = '<article class="card lift feature" style="--tone:' + c.tone + ';height:100%">' +
      '<span class="eyebrow">' + R.icon(c.icon) + "Latest major story · " + R.esc(pick.category) + "</span>" +
      '<h3><a href="' + R.esc(pick.link) + '" target="_blank" rel="noopener">' + R.esc(pick.title) + "</a></h3>" +
      '<div class="news-meta"><span class="src">' + R.esc(pick.source) + "</span><span>·</span><span>" + R.ago(pick.published) + "</span></div>" +
      '<div class="news-tags" style="margin-top:12px">' + R.newsTags(pick) + "</div>" +
      (figs.length ? '<div class="figures">' + figs.map((f) => "<div><span>" + f[0] + "</span><b>" + R.esc(f[1]) + "</b></div>").join("") + "</div>" : "") +
      (also.length ? '<h4 class="sub-h" style="margin-top:26px">Also moving</h4><div class="headline-mini">' + also.map((i) =>
        '<a href="' + R.esc(i.link) + '" target="_blank" rel="noopener" style="--tone:' + R.cat(i.category).tone + '"><span class="k"><i></i>' + R.esc(i.category) + " · " + R.esc(i.source) + " · " + R.ago(i.published) + "</span>" + R.esc(i.title) + "</a>").join("") + "</div>" : "") +
      "</article>";
  }

  /** Fills #latest with the eight newest stories. */
  function latest(items) {
    $("#latest").innerHTML = items.slice(0, 8).map((i) =>
      '<a href="' + R.esc(i.link) + '" target="_blank" rel="noopener" style="--tone:' + R.cat(i.category).tone + '"><span class="k"><i></i>' + R.esc(i.source) + " · " + R.ago(i.published) + (i.state ? " · " + R.esc(i.state) : "") + "</span>" + R.esc(i.title) + "</a>").join("") ||
      '<p class="muted">No headlines yet.</p>';
  }

  /** Fills #topCos with a bar chart of the most-named companies in the last 30 days. */
  function companies(items) {
    const now = Date.now(), counts = {};
    items.filter((i) => now - i.t <= 30 * DAY).forEach((i) => i.companies.forEach((c) => { counts[c] = (counts[c] || 0) + 1; }));
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
    $("#topCos").innerHTML = top.length ? R.miniBars(top.map(([c, n], i) => ({ label: c, value: n, hi: i === 0 })), { label: "Company headline mentions, last 30 days", width: $("#topCos").clientWidth })
      : '<p class="co-empty">No tracked companies were named in headlines in the last 30 days.</p>';
  }
  /** Fills #topics with a bar chart of headline topics in the last 7 days. */
  function topics(items) {
    const now = Date.now(), counts = {};
    items.filter((i) => now - i.t <= 7 * DAY).forEach((i) => { counts[i.category] = (counts[i.category] || 0) + 1; });
    const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
    $("#topics").innerHTML = rows.length ? R.miniBars(rows.map(([c, n], i) => ({ label: c, value: n, hi: i === 0 })), { label: "Headlines by topic, last 7 days", labelW: 140, width: $("#topics").clientWidth })
      : '<p class="co-empty">No headlines in the last 7 days.</p>';
  }

  // The pulse map loads Leaflet only when it scrolls near the viewport. Live refreshes
  // call pulse() again, which only swaps the markers once the map exists.
  let pulseProjects = [], pulseLayers = null;
  /**
   * Updates the site count and, once the map exists, replaces its pins and bubbles with the
   * projects shown by default. Clicking a pin opens it on /radar#project=<id>.
   */
  function drawPulse() {
    const now = Date.now();
    const recent = pulseProjects.filter(R.defaultVisible);
    $("#pulseCount").innerHTML = '<span class="live-dot" aria-hidden="true"></span>' + recent.length + " sites on the map";
    if (!pulseLayers) return;
    const { cl, approx } = pulseLayers;
    cl.clearLayers();
    cl.addLayers(recent.filter((p) => p.curated || !p.approx).map((p) => {
      const m = window.L.marker([p.lat, p.lon], { icon: R.pinIcon(p), title: p.curated ? p.name : p.place, keyboard: true });
      m.bindTooltip("<b>" + R.esc(p.curated ? p.name : p.place) + "</b><small>" + R.esc(R.statusSince(p)) + (p.capacity_mw ? " · " + R.fmtMW(p.capacity_mw) : "") + "</small>", { className: "rr-tip", direction: "top", offset: [0, -10] });
      m.on("click", () => { location.href = "/radar#project=" + encodeURIComponent(p.id); });
      return m;
    }));
    approx.set(recent);
  }
  /** Stores the projects and redraws. The first call also adds the legend and builds the map when #pulseMap nears the viewport. */
  function pulse(projects) {
    const first = !pulseProjects.length;
    pulseProjects = projects;
    drawPulse();
    if (!first) return;
    $("#pulseLegend").innerHTML = R.legendHTML();
    const el = $("#pulseMap");
    // Loads Leaflet and builds the map; shows a message if that fails.
    const start = () => R.loadLeaflet().then(() => {
      const map = R.baseMap(el, { scrollWheelZoom: false });
      window.L.control.zoom({ position: "topright" }).addTo(map);
      const cl = R.clusterGroup();
      map.addLayer(cl);
      pulseLayers = { cl, approx: R.approxLayer(map, cl, null) };
      drawPulse();
      $("#pulsePh").remove();
    }).catch(() => { $("#pulsePh").textContent = "The map couldn't load. Open Rack Radar instead."; });
    if (!("IntersectionObserver" in window)) return start();
    const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) { io.disconnect(); start(); } }, { rootMargin: "300px" });
    io.observe(el);
  }

  /** Draws the whole page from the news and projects; also the callback for live refresh. */
  function render(n, projects) {
    // One entry per story: duplicate coverage of the same event is folded into one card.
    const items = R.stories(n.items);
    stats(n.items, items, projects);
    R.ticker($("#ticker"), items.slice(0, 10));
    major(items);
    latest(items);
    companies(items);
    topics(items);
    pulse(projects);
  }
  // Start-up: load news and projects, render, then follow live refreshes.
  Promise.all([R.news(), R.projects()]).then(([n, projects]) => {
    render(n, projects);
    R.live(render);
    R.ready();
  }).catch((err) => {
    console.error(err);
    $("#stats").innerHTML = '<div class="card empty" style="grid-column:1/-1">' + R.icon("alert") + "<b>Couldn't load the data</b>Try reloading in a minute.</div>";
    R.ready();
  });
})();
