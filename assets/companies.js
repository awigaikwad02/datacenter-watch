// Companies page: role overview, searchable company cards and a detail drawer with projects and headlines.
(function () {
  const D = DCW, $ = (s) => document.querySelector(s);
  const DAY = 864e5;
  const f = { q: "", type: "", sort: "projects" };
  let cos = [], bySlug = {};

  D.chrome("companies.html");

  function build(companies, projects, news) {
    const match = D.companyMatcher(companies);
    const mentions = {};
    news.forEach((n) => match(n.title).forEach((s) => { (mentions[s] = mentions[s] || []).push(n); }));
    return companies.map((c) => {
      const ps = projects.filter((p) => p.companies.includes(c.slug));
      const ns = (mentions[c.slug] || []).sort((a, b) => b.published.localeCompare(a.published));
      return Object.assign({}, c, {
        projects: ps,
        mw: ps.reduce((a, p) => a + (p.capacity_mw || 0), 0),
        states: [...new Set(ps.map((p) => p.state))].sort(),
        news: ns,
        recent: ns.filter((n) => Date.now() - new Date(n.published).getTime() <= 30 * DAY).length,
        tone: (D.TYPES[c.type] || {}).tone || "#64748b",
        hay: [c.name, c.short, c.type, c.hq, c.summary, c.aliases.join(" "), ps.map((p) => p.name + " " + p.location).join(" ")].join(" ").toLowerCase(),
      });
    });
  }

  function renderStats(projects) {
    const linked = projects.filter((p) => p.companies.length).length;
    const mw = projects.reduce((a, p) => a + (p.capacity_mw || 0), 0);
    const mentions = cos.reduce((a, c) => a + c.recent, 0);
    const tiles = [
      ["building", "Companies tracked", cos.length, "", "var(--c-announce)", Object.keys(D.TYPES).length + " roles across the industry"],
      ["map", "Projects linked", linked, "", "var(--c-ai)", "on the projects map"],
      ["zap", "Capacity tracked", mw / 1000, "GW", "var(--c-power)", "announced, building or running"],
      ["news", "News mentions", mentions, "", "var(--c-deals)", "headlines in the last 30 days"],
    ];
    $("#stats").innerHTML = tiles.map((t, i) =>
      '<div class="stat reveal" style="--tone:color-mix(in srgb,' + t[4] + ' 30%,transparent);--tone-ink:' + t[4] + ";transition-delay:" + i * 60 + 'ms"><div class="label">' + D.icon(t[0]) + t[1] +
      '</div><div class="value" data-v="' + t[2] + '" data-u="' + t[3] + '">0</div><div class="hint">' + t[5] + "</div></div>").join("");
    $("#stats").querySelectorAll(".value").forEach((el) => {
      const u = el.dataset.u;
      D.countUp(el, Number(el.dataset.v), (x) => (u ? x.toFixed(1) : Math.round(x).toLocaleString()) + (u ? "<small>" + u + "</small>" : ""));
    });
    $("#eyebrow").textContent = cos.length + " companies · " + linked + " projects";
  }

  function renderRoles() {
    const n = {};
    cos.forEach((c) => { n[c.type] = (n[c.type] || 0) + 1; });
    $("#roles").innerHTML = Object.entries(D.TYPES).filter(([k]) => n[k]).map(([k, t]) =>
      '<button class="role reveal" data-type="' + k + '" style="--tone:' + t.tone + ';text-align:left;cursor:pointer;font:inherit;color:inherit"><b>' + k +
      ' <span class="pill" style="--tone:' + t.tone + '">' + n[k] + "</span></b><p>" + t.blurb + "</p></button>").join("");
  }

  function renderTypes() {
    const n = {};
    cos.forEach((c) => { n[c.type] = (n[c.type] || 0) + 1; });
    $("#types").innerHTML = '<button class="chip" data-type="" aria-pressed="' + !f.type + '">All <span class="n">' + cos.length + "</span></button>" +
      Object.entries(D.TYPES).filter(([k]) => n[k]).map(([k, t]) =>
        '<button class="chip" data-type="' + k + '" style="--tone:' + t.tone + '" aria-pressed="' + (f.type === k) + '"><span class="dot"></span>' + k + ' <span class="n">' + n[k] + "</span></button>").join("");
  }

  function renderGrid() {
    const words = f.q.toLowerCase().split(/\s+/).filter(Boolean);
    const list = cos.filter((c) => (!f.type || c.type === f.type) && words.every((w) => c.hay.includes(w)));
    const by = {
      projects: (a, b) => b.projects.length - a.projects.length || b.mw - a.mw || b.recent - a.recent,
      mw: (a, b) => b.mw - a.mw || b.projects.length - a.projects.length,
      news: (a, b) => b.recent - a.recent || b.news.length - a.news.length,
      name: (a, b) => a.name.localeCompare(b.name),
    }[f.sort];
    list.sort(by);
    $("#countLine").textContent = list.length === cos.length ? "Every company we track, with linked projects and news mentions." : list.length + " of " + cos.length + " companies";
    if (!list.length) {
      $("#grid").innerHTML = '<div class="empty-state card" style="grid-column:1/-1">' + D.icon("search") + "<b>No companies match</b>Try another search or role.</div>";
      return;
    }
    $("#grid").innerHTML = list.map((c, i) =>
      '<button class="co-card" data-slug="' + c.slug + '" style="--tone:' + c.tone + ";animation-delay:" + Math.min(i, 15) * 30 + 'ms">' +
      '<div class="co-top"><span class="co-av">' + D.esc(D.initials(c)) + "</span><div><h3>" + D.esc(c.name) + "</h3><small>" +
      '<span class="pill" style="--tone:' + c.tone + '">' + c.type + "</span>" + D.icon("pin") + D.esc(c.hq) + "</small></div></div>" +
      "<p>" + D.esc(c.summary) + "</p>" +
      (c.states.length ? '<div class="co-states">' + c.states.map((s) => '<span title="' + D.STATES[s] + '">' + s + "</span>").join("") + "</div>" : "") +
      '<div class="co-metrics"><div><b>' + c.projects.length + "</b><span>projects</span></div><div><b>" + (c.mw ? D.fmtMW(c.mw) : "—") + "</b><span>capacity</span></div><div><b>" + c.recent + "</b><span>news (30d)</span></div></div>" +
      "</button>").join("");
  }

  function miniTiles(states) {
    const cells = [];
    for (let r = 0; r < 8; r++) for (let c = 0; c < 11; c++) cells.push(null);
    Object.entries(D.TILES).forEach(([s, [c, r]]) => { cells[r * 11 + c] = s; });
    return '<div class="tilemap">' + cells.map((s) => {
      if (!s) return "<span></span>";
      const on = states.includes(s);
      return '<span class="tile' + (on ? " has" : "") + '" title="' + D.STATES[s] + '"' + (on ? ' style="background:var(--tone);color:#fff"' : "") + ">" + s + "</span>";
    }).join("") + "</div>";
  }

  function open(slug, push) {
    const c = bySlug[slug];
    if (!c) return;
    const dr = $("#drawer");
    dr.style.setProperty("--tone", c.tone);
    dr.innerHTML =
      '<div class="drawer-head"><div class="co-top"><span class="co-av lg">' + D.esc(D.initials(c)) + '</span><div><h2 id="drawerTitle" style="font-size:24px">' + D.esc(c.name) + "</h2><small>" +
      '<span class="pill" style="--tone:' + c.tone + '">' + c.type + "</span>" + D.icon("pin") + D.esc(c.hq) + "</small></div></div>" +
      '<button class="icon-btn close" id="closeDrawer" aria-label="Close">' + D.icon("x") + "</button></div>" +
      '<div class="drawer-body">' +
      '<p style="margin:0;font-size:15.5px;color:var(--text-2)">' + D.esc(c.summary) + "</p>" +
      '<div class="kv" style="grid-template-columns:repeat(4,1fr)">' +
      [["Projects", c.projects.length], ["Capacity", c.mw ? D.fmtMW(c.mw) : "—"], ["States", c.states.length], ["News (30d)", c.recent]].map((k) => "<div><span>" + k[0] + "</span><b>" + k[1] + "</b></div>").join("") + "</div>" +
      '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
      (c.projects.length ? '<a class="btn sm primary" href="projects.html#co=' + c.slug + '">' + D.icon("map") + "Show on map</a>" : "") +
      '<a class="btn sm" href="index.html#company=' + c.slug + '">' + D.icon("news") + "All headlines</a>" +
      (c.website ? '<a class="btn sm" href="' + D.esc(c.website) + '" target="_blank" rel="noopener">' + D.icon("external") + "Website</a>" : "") + "</div>" +
      (c.states.length ? "<div><h4 style=\"font-family:var(--font);font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:10px\">Where they're building</h4>" + miniTiles(c.states) + "</div>" : "") +
      (c.projects.length ? '<div><h4 style="font-family:var(--font);font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:6px">Projects</h4><table class="ptable"><thead><tr><th>Project</th><th>Stage</th><th>Capacity</th></tr></thead><tbody>' +
        c.projects.slice().sort((a, b) => (b.capacity_mw || 0) - (a.capacity_mw || 0)).map((p) =>
          '<tr><td><a href="projects.html#p=' + p.id + '">' + D.esc(p.name) + "</a><small>" + D.esc(p.location.replace(/, US$/, "")) + "</small></td>" +
          '<td><span class="pill" style="--tone:' + D.STATUS[p.status].tone + '"><span class="dot"></span>' + p.status + "</span></td><td>" + (p.capacity_mw ? D.fmtMW(p.capacity_mw) : "—") + "</td></tr>").join("") +
        "</tbody></table></div>" : "") +
      '<div><h4 style="font-family:var(--font);font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:6px">Latest headlines</h4>' +
      (c.news.length ? '<div class="headlines">' + c.news.slice(0, 8).map((n) => '<a href="' + D.esc(n.link) + '" target="_blank" rel="noopener">' + D.esc(n.title) + "<small>" + D.esc(n.source) + " · " + D.ago(n.published) + "</small></a>").join("") + "</div>"
        : '<p class="muted" style="font-size:14px;margin:0">No recent headlines mention ' + D.esc(c.name) + ".</p>") + "</div>" +
      "</div>";
    dr.classList.add("open");
    $("#back").classList.add("open");
    document.body.style.overflow = "hidden";
    dr.querySelector("#closeDrawer").addEventListener("click", close);
    dr.querySelector("#closeDrawer").focus();
    if (push !== false) history.replaceState(null, "", "#" + slug);
  }
  function close() {
    $("#drawer").classList.remove("open");
    $("#back").classList.remove("open");
    document.body.style.overflow = "";
    history.replaceState(null, "", location.pathname + location.search);
  }

  function bind() {
    $("#q").addEventListener("input", D.debounce((e) => { f.q = e.target.value.trim(); renderGrid(); }, 150));
    $("#sort").addEventListener("change", (e) => { f.sort = e.target.value; renderGrid(); });
    document.addEventListener("click", (e) => {
      const t = e.target.closest("[data-type]");
      if (t) {
        f.type = f.type === t.dataset.type ? "" : t.dataset.type;
        renderTypes(); renderGrid();
        if (t.classList.contains("role")) $("#toolbar").scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      const card = e.target.closest(".co-card");
      if (card) open(card.dataset.slug);
    });
    $("#back").addEventListener("click", close);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && $("#drawer").classList.contains("open")) close(); });
    window.addEventListener("hashchange", () => { const s = location.hash.slice(1); if (bySlug[s]) open(s, false); });
  }

  Promise.all([D.loadJSON("data/companies.json"), D.loadJSON("data/projects.json"), D.loadJSON("data/news.json").catch(() => ({ items: [] }))])
    .then(([c, p, n]) => {
      cos = build(c.companies, p.projects, n.items || []);
      cos.forEach((x) => { bySlug[x.slug] = x; });
      renderStats(p.projects);
      renderRoles();
      renderTypes();
      renderGrid();
      bind();
      const s = location.hash.slice(1);
      if (bySlug[s]) open(s, false);
      D.ready();
    })
    .catch((err) => { console.error(err); D.fail("Couldn't load company data. Try reloading."); });
})();
