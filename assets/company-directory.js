// Companies: directory cards for the operators (assets/companies.js), computed from projects and
// headlines, with a profile modal; plus "Who builds and equips them": the investors, builders and
// suppliers named in recent stories, each linking to the Newsroom filtered to it.
(function () {
  "use strict";
  const R = RR, $ = (s) => document.querySelector(s), DAY = R.DAY;
  const f = { q: "", type: "", sort: "projects" };
  // days: how many days of headlines data/news.json holds (30 or 90), for the labels.
  let cos = [], release = null, days = 30;
  R.shell("/companies", "Companies");

  function build(projects, items) {
    return Object.keys(window.RR_COMPANIES).map((name) => {
      const info = R.companyInfo(name);
      const ps = projects.filter((p) => p.companies.includes(name));
      const ns = items.filter((n) => n.companies.includes(name));
      const states = new Set(ps.map((p) => p.state).concat(ns.map((n) => n.state).filter(Boolean)));
      const latest = Math.max(0, ...ns.map((n) => n.t), ...ps.filter((p) => !p.curated).map((p) => p.t));
      // Registry records per company (hidden ones never arrive here), split by status.
      const byStatus = {};
      ps.forEach((p) => { byStatus[p.status] = (byStatus[p.status] || 0) + 1; });
      return {
        name, info, tone: R.companyTone(name), projects: ps, byStatus, news: ns, states: [...states].sort(), latest,
        major: ps.filter((p) => p.curated).sort((a, b) => (b.capacity_mw || 0) - (a.capacity_mw || 0)).slice(0, 3),
        hay: (name + " " + info.type + " " + info.desc + " " + [...states].map((s) => R.STATES[s] + " " + s).join(" ")).toLowerCase(),
      };
    });
  }

  // Investors, builders and suppliers: story counts in the news window, most-mentioned first.
  const VENDOR_GROUPS = [["investors", "investor", "Investors", "dollar"], ["builders", "builder", "Builders", "factory"], ["suppliers", "supplier", "Suppliers", "plug"]];
  function vendors(stories) {
    $("#vendorCols").innerHTML = VENDOR_GROUPS.map(([field, key, label, icon]) => {
      const n = {};
      stories.forEach((s) => (s[field] || []).forEach((v) => { n[v] = (n[v] || 0) + 1; }));
      const rows = Object.entries(n).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
      return '<div class="card vendor-col"><h3 class="sub-h">' + R.icon(icon) + label + "</h3>" + (rows.length
        ? "<ul>" + rows.map(([v, c]) => '<li><a href="/newsroom#' + key + "=" + encodeURIComponent(v) + '&range=90">' + R.esc(v) + '</a><span class="n">' + c + " stor" + (c === 1 ? "y" : "ies") + "</span></li>").join("") + "</ul>"
        : '<p class="co-empty">None named in the last ' + days + " days.</p>") + "</div>";
    }).join("");
  }

  const SPLIT = [["Operational", "operational"], ["Under construction", "building"], ["Announced", "announced"], ["Planned", "planned"], [R.CANCELLED, "cancelled"]];
  function statusSplit(c) {
    const parts = SPLIT.filter(([s]) => c.byStatus[s]).map(([s, label]) => c.byStatus[s] + " " + label);
    return parts.length ? '<p class="co-status">' + R.esc(parts.join(" · ")) + "</p>" : "";
  }

  function stats(projects) {
    const active = cos.filter((c) => c.projects.length || c.news.length).length;
    const linked = projects.filter((p) => p.companies.length).length;
    const mentions = cos.reduce((a, c) => a + c.news.length, 0);
    const tiles = [["building", "Companies tracked", cos.length, "var(--cyan)", "across " + new Set(cos.map((c) => c.info.type)).size + " roles"],
      ["activity", "Active in the data", active, "var(--accent)", "with projects or headlines"],
      ["map", "Projects linked", linked, "var(--st-announced)", "curated and detected"],
      ["news", "Story mentions", mentions, "var(--c-deals)", "news stories in the last " + days + " days"]];
    $("#stats").innerHTML = tiles.map((t) => '<div class="card stat" style="--tone:' + t[3] + ";--glow:color-mix(in srgb," + t[3] + ' 22%,transparent)"><div class="stat-label">' + R.icon(t[0]) + t[1] + '</div><div class="stat-value" data-v="' + t[2] + '">0</div><div class="stat-hint">' + t[4] + "</div></div>").join("");
    $("#stats").querySelectorAll(".stat-value").forEach((el) => R.countUp(el, Number(el.dataset.v)));
  }

  function types() {
    const n = {};
    cos.forEach((c) => { n[c.info.type] = (n[c.info.type] || 0) + 1; });
    $("#types").innerHTML = '<button class="chip" data-type="" aria-pressed="' + !f.type + '">All <span class="n">' + cos.length + "</span></button>" +
      Object.keys(n).sort().map((t) => '<button class="chip" data-type="' + R.esc(t) + '" style="--tone:' + R.companyTone(cos.find((c) => c.info.type === t).name) + '" aria-pressed="' + (f.type === t) + '"><span class="dot"></span>' + R.esc(t) + ' <span class="n">' + n[t] + "</span></button>").join("");
  }

  function grid() {
    const words = f.q.toLowerCase().split(/\s+/).filter(Boolean);
    const list = cos.filter((c) => (!f.type || c.info.type === f.type) && words.every((w) => c.hay.includes(w)));
    const by = {
      projects: (a, b) => b.projects.length - a.projects.length || b.news.length - a.news.length || a.name.localeCompare(b.name),
      latest: (a, b) => b.latest - a.latest || a.name.localeCompare(b.name),
      news: (a, b) => b.news.length - a.news.length || a.name.localeCompare(b.name),
      name: (a, b) => a.name.localeCompare(b.name),
    }[f.sort];
    list.sort(by);
    $("#count").textContent = list.length + " of " + cos.length + " companies";
    if (!list.length) { $("#grid").innerHTML = '<div class="card empty" style="grid-column:1/-1">' + R.icon("search") + "<b>No companies match</b>Try another search or role.</div>"; return; }
    $("#grid").innerHTML = list.map((c) => {
      const last = c.news[0];
      return '<article class="card lift co-card reveal" style="--tone:' + c.tone + '">' +
        '<div class="co-head"><span class="lettermark" aria-hidden="true">' + R.esc(R.letters(c.name)) + '</span><div><h3><button class="stretch" data-co="' + R.esc(c.name) + '" aria-haspopup="dialog">' + R.esc(c.name) + "</button></h3><small>" + R.esc(c.info.type) + (c.latest ? " · active " + R.ago(new Date(c.latest).toISOString()) : "") + "</small></div></div>" +
        '<p class="co-desc">' + R.esc(c.info.desc) + "</p>" +
        (c.major.length ? '<p class="co-latest"><b>Major projects:</b> ' + c.major.map((p) => R.esc(p.name)).join(", ") + "</p>" : "") +
        (last ? '<p class="co-latest"><b>Latest:</b> ' + R.esc(last.title) + "</p>" : '<p class="co-latest co-empty">No tracked headlines yet.</p>') +
        '<span class="co-metrics"><span><b>' + c.projects.length + "</b><span>projects</span></span><span><b>" + c.states.length + "</b><span>states</span></span><span><b>" + c.news.length + "</b><span>stories</span></span></span>" + statusSplit(c) + "</article>";
    }).join("");
    R.reveal($("#grid"));
  }

  function profile(name) {
    const c = cos.find((x) => x.name === name);
    if (!c) return;
    const m = $("#modal");
    m.style.setProperty("--tone", c.tone);
    const projects = c.projects.slice().sort((a, b) => b.curated - a.curated || (b.capacity_mw || 0) - (a.capacity_mw || 0) || b.t - a.t);
    m.innerHTML = '<div class="modal-head"><div class="co-head"><span class="lettermark lg" aria-hidden="true">' + R.esc(R.letters(c.name)) + '</span><span><h2 id="modalTitle" style="font-size:24px">' + R.esc(c.name) + "</h2><small>" + R.esc(c.info.type) + "</small></span></div>" +
      '<button class="icon-btn close" id="modalClose" aria-label="Close company profile">' + R.icon("x") + "</button></div>" +
      '<div class="modal-body"><p style="margin:0;color:var(--text-2)">' + R.esc(c.info.desc) + "</p>" +
      '<div class="kv four">' + [["Tracked projects", c.projects.length], ["Curated", c.projects.filter((p) => p.curated).length], ["Active states", c.states.length], ["Stories (" + days + " days)", c.news.length]].map((k) => "<div><span>" + k[0] + "</span><b>" + k[1] + "</b></div>").join("") + "</div>" +
      (c.states.length ? '<div><h3 class="sub-h">Active states</h3><div class="news-tags">' + c.states.map((s) => '<span class="tag plain">' + R.esc(R.STATES[s] || s) + "</span>").join("") + "</div></div>" : "") +
      '<div style="display:flex;gap:8px;flex-wrap:wrap">' + (c.projects.length ? '<a class="btn sm primary" href="/radar#company=' + encodeURIComponent(c.name) + '">' + R.icon("map") + "View on Rack Radar</a>" : "") +
      '<a class="btn sm" href="/newsroom#company=' + encodeURIComponent(c.name) + '&range=90">' + R.icon("news") + "All headlines</a></div>" +
      '<div><h3 class="sub-h">Projects</h3>' + (projects.length ? '<table class="ptable"><thead><tr><th scope="col">Project</th><th scope="col">Status</th><th scope="col">Capacity</th></tr></thead><tbody>' +
        projects.map((p) => '<tr><td><a href="/radar#project=' + encodeURIComponent(p.id) + '">' + R.esc(p.curated ? p.name : p.name.length > 70 ? p.name.slice(0, 68) + "…" : p.name) + "</a><small>" + R.esc(p.place) + (p.curated ? " · curated" : " · detected") + "</small></td>" +
          '<td><span class="tag" style="--tone:' + R.status(p.status).tone + '"><span class="dot"></span>' + R.esc(p.status) + "</span></td><td>" + (p.capacity_mw ? R.fmtMW(p.capacity_mw) : "—") + "</td></tr>").join("") + "</tbody></table>"
        : '<p class="co-empty">No projects tracked for ' + R.esc(c.name) + " yet.</p>") + "</div>" +
      '<div><h3 class="sub-h">Latest headlines</h3>' + (c.news.length ? '<div class="headlines">' + c.news.slice(0, 10).map((n) => '<a href="' + R.esc(n.link) + '" target="_blank" rel="noopener">' + R.esc(n.title) + "<small>" + R.esc(n.source) + " · " + R.ago(n.published) + "</small></a>").join("") + "</div>"
        : '<p class="co-empty">No headlines mention ' + R.esc(c.name) + " in the last " + days + " days.</p>") + "</div></div>";
    m.hidden = false;
    requestAnimationFrame(() => { m.classList.add("open"); $("#back").classList.add("open"); });
    document.body.style.overflow = "hidden";
    $("#modalClose").addEventListener("click", close);
    release = R.trapFocus(m, close);
    history.replaceState(null, "", "#" + encodeURIComponent(c.name));
  }
  function close() {
    const m = $("#modal");
    if (!m.classList.contains("open")) return;
    m.classList.remove("open");
    $("#back").classList.remove("open");
    document.body.style.overflow = "";
    if (release) { release(); release = null; }
    setTimeout(() => { m.hidden = true; }, 300);
    history.replaceState(null, "", location.pathname);
  }

  function bind() {
    $("#q").addEventListener("input", R.debounce((e) => { f.q = e.target.value.trim(); grid(); }, 150));
    $("#sort").addEventListener("change", (e) => { f.sort = e.target.value; grid(); });
    $("#types").addEventListener("click", (e) => {
      const b = e.target.closest("[data-type]");
      if (!b) return;
      f.type = b.dataset.type;
      types(); grid();
      const nb = document.querySelector('#types [data-type="' + CSS.escape(f.type) + '"]');
      if (nb) { nb.classList.add("pop"); nb.focus(); }
    });
    $("#grid").addEventListener("click", (e) => { const b = e.target.closest("[data-co]"); if (b) profile(b.dataset.co); });
    $("#back").addEventListener("click", close);
    window.addEventListener("hashchange", openFromHash);
  }
  function openFromHash() { const n = decodeURIComponent(location.hash.slice(1)); if (n && window.RR_COMPANIES[n]) profile(n); }

  Promise.all([R.projects(), R.news()]).then(([projects, n]) => {
    days = n.windowDays;
    // Count stories, not headlines: several outlets covering one event count once.
    cos = build(projects, R.stories(n.items));
    stats(projects);
    types();
    grid();
    vendors(R.stories(n.items));
    bind();
    openFromHash();
    R.live((n, projects) => { cos = build(projects, R.stories(n.items)); stats(projects); types(); grid(); vendors(R.stories(n.items)); });
    R.ready();
  }).catch((err) => {
    console.error(err);
    $("#grid").innerHTML = '<div class="card empty" style="grid-column:1/-1">' + R.icon("alert") + "<b>Couldn't load company data</b>Try reloading in a minute.</div>";
    R.ready();
  });
})();
