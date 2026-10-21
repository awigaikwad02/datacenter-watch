// News page: featured story, filters, day-grouped feed, state tile map, volume chart and company mentions.
(function () {
  const D = DCW, $ = (s) => document.querySelector(s);
  const PAGE = 40;
  const DAY = 864e5;

  const state = {
    q: "", cat: "", st: "", co: "", day: "", saved: false,
    range: Number(D.store("range")) || 30,
    view: D.store("view") || "list",
    shown: PAGE,
  };
  let items = [], companies = [], coBySlug = {}, saved = D.store("saved") || {};

  D.chrome("index.html");

  // ---------- URL hash <-> filters ----------
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    state.q = h.get("q") || "";
    state.cat = h.get("cat") || "";
    state.st = h.get("state") || "";
    state.co = h.get("company") || "";
    state.day = h.get("day") || "";
    state.saved = h.get("saved") === "1";
  }
  function writeHash() {
    const h = new URLSearchParams();
    if (state.q) h.set("q", state.q);
    if (state.cat) h.set("cat", state.cat);
    if (state.st) h.set("state", state.st);
    if (state.co) h.set("company", state.co);
    if (state.day) h.set("day", state.day);
    if (state.saved) h.set("saved", "1");
    const s = h.toString();
    history.replaceState(null, "", s ? "#" + s : location.pathname + location.search);
  }

  // ---------- Filtering ----------
  function pool() {
    if (!state.saved) return items;
    const ids = new Set(items.map((i) => i.id));
    const extra = Object.values(saved).filter((s) => !ids.has(s.id)).map(prep);
    return items.filter((i) => saved[i.id]).concat(extra);
  }
  // skip: a filter name (or list of names) to ignore, used for facet counts.
  function match(it, skip) {
    const sk = [].concat(skip || []);
    if (!sk.includes("range") && !state.day && !state.saved && Date.now() - it.t > state.range * DAY) return false;
    if (!sk.includes("day") && state.day && it.day !== state.day) return false;
    if (!sk.includes("cat") && state.cat && it.category !== state.cat) return false;
    if (!sk.includes("st") && state.st && !it.states.includes(state.st)) return false;
    if (!sk.includes("co") && state.co && !it.cos.includes(state.co)) return false;
    if (state.q) {
      const words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
      if (!words.every((w) => it.hay.includes(w))) return false;
    }
    return true;
  }
  const filtered = (skip) => pool().filter((it) => match(it, skip));

  let matchCos = () => [];
  function prep(it) {
    const t = new Date(it.published).getTime();
    const states = it.states || [];
    const cos = matchCos(it.title);
    return Object.assign({}, it, {
      t, states, cos,
      day: D.dayKey(it.published),
      category: it.category || "General",
      hay: (it.title + " " + (it.source || "") + " " + states.map((s) => D.STATES[s]).join(" ") + " " + cos.map((c) => coBySlug[c].name).join(" ")).toLowerCase(),
    });
  }

  // ---------- Rendering: stats ----------
  function renderStats(d) {
    const now = Date.now();
    const wk = items.filter((i) => now - i.t <= 7 * DAY);
    const mo = items.filter((i) => now - i.t <= 30 * DAY);
    const ann = wk.filter((i) => i.category === "Announcements" || i.category === "Construction").length;
    const sts = new Set(mo.flatMap((i) => i.states)).size;
    const mw = mo.reduce((a, i) => a + (i.capacity_mw || 0), 0);
    const tiles = [
      ["news", "Stories this week", wk.length, "", "var(--c-announce)", "across " + new Set(wk.map((i) => i.source)).size + " outlets"],
      ["spark", "Announcement & build stories", ann, "", "var(--c-ai)", "in the last 7 days"],
      ["pin", "States in the news", sts, "", "var(--c-deals)", "in the last 30 days"],
      ["zap", "Capacity in headlines", mw / 1000, "GW", "var(--c-power)", "mentioned in the last 30 days"],
    ];
    $("#stats").innerHTML = tiles.map((t, i) =>
      '<div class="stat reveal" style="--tone:color-mix(in srgb,' + t[4] + ' 30%,transparent);--tone-ink:' + t[4] + ';transition-delay:' + i * 60 + 'ms">' +
      '<div class="label">' + D.icon(t[0]) + t[1] + '</div><div class="value" data-v="' + t[2] + '" data-u="' + t[3] + '">0</div><div class="hint">' + t[5] + "</div></div>").join("");
    $("#stats").querySelectorAll(".value").forEach((el) => {
      const v = Number(el.dataset.v), u = el.dataset.u;
      D.countUp(el, v, (x) => (u ? x.toFixed(1) : Math.round(x).toLocaleString()) + (u ? "<small>" + u + "</small>" : ""));
    });
    const upd = new Date(d.updated);
    $("#updated").textContent = "Updated " + D.ago(d.updated) + " · " + upd.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  }

  // ---------- Rendering: featured ----------
  function renderFeatured() {
    const now = Date.now();
    const recent = items.filter((i) => now - i.t <= 3 * DAY);
    const score = (i) => (i.category === "Announcements" || i.category === "Construction" ? 3 : 0) + (i.capacity_mw ? 2 : 0) + (i.investment_usd_b ? 2 : 0) + (i.states.length ? 1 : 0) + Math.min(2, i.cos.length) - (now - i.t) / DAY;
    const top = recent.slice().sort((a, b) => score(b) - score(a)).slice(0, 4);
    if (!top.length) { $("#featured").innerHTML = ""; return; }
    const f = top[0], c = D.CATS[f.category] || D.CATS.General;
    $("#featured").innerHTML =
      '<article class="featured reveal" style="--tone:' + c.tone + '">' +
      '<div class="kicker">' + D.icon("star") + "Top story" + '<span class="pill" style="--tone:' + c.tone + '"><span class="dot"></span>' + D.esc(f.category) + "</span></div>" +
      '<h2><a href="' + D.esc(f.link) + '" target="_blank" rel="noopener">' + D.esc(f.title) + "</a></h2>" +
      '<div class="meta"><b>' + D.esc(f.source) + "</b><span>·</span><span>" + D.ago(f.published) + "</span>" + tagsHTML(f) + "</div>" +
      (top.length > 1 ? '<div class="more-top">' + top.slice(1).map((i) =>
        "<div><small>" + D.esc(i.source) + " · " + D.ago(i.published) + '</small><a href="' + D.esc(i.link) + '" target="_blank" rel="noopener">' + D.esc(i.title) + "</a></div>").join("") + "</div>" : "") +
      "</article>";
  }

  function tagsHTML(it) {
    let h = "";
    if (it.capacity_mw) h += '<span class="tag num" style="--tone:var(--c-power)">⚡ ' + D.fmtMW(it.capacity_mw) + "</span>";
    if (it.investment_usd_b) h += '<span class="tag num" style="--tone:var(--c-deals)">' + D.fmtMoney(it.investment_usd_b) + "</span>";
    it.states.forEach((s) => { h += '<button class="tag" data-st="' + s + '" title="Filter to ' + D.STATES[s] + '">' + D.icon("pin") + D.STATES[s] + "</button>"; });
    it.cos.slice(0, 3).forEach((s) => { h += '<button class="tag" data-co="' + s + '">' + D.icon("building") + D.esc(coBySlug[s].name) + "</button>"; });
    return h;
  }

  // ---------- Rendering: chips, selects ----------
  function renderChips() {
    const base = filtered("cat");
    const counts = {};
    base.forEach((i) => { counts[i.category] = (counts[i.category] || 0) + 1; });
    const nSaved = Object.keys(saved).length;
    let h = '<button class="chip" data-cat="" aria-pressed="' + (!state.cat && !state.saved) + '">All <span class="n">' + base.length + "</span></button>";
    Object.keys(D.CATS).forEach((k) => {
      h += '<button class="chip" data-cat="' + D.esc(k) + '" style="--tone:' + D.CATS[k].tone + '" aria-pressed="' + (state.cat === k) + '"><span class="dot"></span>' + k + ' <span class="n">' + (counts[k] || 0) + "</span></button>";
    });
    h += '<button class="chip" data-saved="1" aria-pressed="' + state.saved + '">' + D.icon("bookmark") + 'Saved <span class="n">' + nSaved + "</span></button>";
    $("#chips").innerHTML = h;
  }
  function renderSelects() {
    const stCounts = {}, coCounts = {};
    filtered("st").forEach((i) => i.states.forEach((s) => { stCounts[s] = (stCounts[s] || 0) + 1; }));
    filtered("co").forEach((i) => i.cos.forEach((s) => { coCounts[s] = (coCounts[s] || 0) + 1; }));
    $("#state").innerHTML = '<option value="">All states</option>' + Object.keys(D.STATES).sort((a, b) => D.STATES[a].localeCompare(D.STATES[b]))
      .filter((s) => stCounts[s] || s === state.st)
      .map((s) => '<option value="' + s + '"' + (s === state.st ? " selected" : "") + ">" + D.STATES[s] + " (" + (stCounts[s] || 0) + ")</option>").join("");
    $("#company").innerHTML = '<option value="">All companies</option>' + companies.slice().sort((a, b) => a.name.localeCompare(b.name))
      .filter((c) => coCounts[c.slug] || c.slug === state.co)
      .map((c) => '<option value="' + c.slug + '"' + (c.slug === state.co ? " selected" : "") + ">" + D.esc(c.name) + " (" + (coCounts[c.slug] || 0) + ")</option>").join("");
    $("#range").value = String(state.range);
    $("#range").disabled = !!state.day || state.saved;
  }
  function renderActive() {
    const parts = [];
    if (state.q) parts.push(["q", "“" + state.q + "”"]);
    if (state.st) parts.push(["st", D.STATES[state.st]]);
    if (state.co) parts.push(["co", coBySlug[state.co] ? coBySlug[state.co].name : state.co]);
    if (state.day) parts.push(["day", D.dayLabel(state.day)]);
    const el = $("#active");
    el.hidden = !parts.length;
    el.innerHTML = "Filtering by " + parts.map((p) => '<button class="tag" data-clear="' + p[0] + '">' + D.esc(p[1]) + D.icon("x") + "</button>").join("") + ' <button class="link-btn" data-clear="all">Clear all</button>';
  }

  // ---------- Rendering: feed ----------
  function storyHTML(it, i) {
    const c = D.CATS[it.category] || D.CATS.General;
    const isNew = Date.now() - it.t < 12 * 36e5;
    return '<article class="story' + (isNew ? " is-new" : "") + '" style="--tone:' + c.tone + ";animation-delay:" + Math.min(i, 12) * 25 + 'ms">' +
      '<div class="body"><div class="meta"><span class="pill" style="--tone:' + c.tone + '"><span class="dot"></span>' + D.esc(it.category) + '</span><span class="src">' + D.esc(it.source || "Unknown source") + '</span><span class="sep">·</span><time datetime="' + it.published + '" title="' + D.fmtDate(it.published, { dateStyle: "medium" }) + '">' + D.ago(it.published) + "</time></div>" +
      '<h3><a href="' + D.esc(it.link) + '" target="_blank" rel="noopener">' + D.esc(it.title) + "</a></h3>" +
      '<div class="tags">' + tagsHTML(it) + "</div></div>" +
      '<div class="actions"><button class="icon-btn" data-save="' + it.id + '" aria-pressed="' + !!saved[it.id] + '" aria-label="Save story" title="Save">' + D.icon("bookmark") + "</button>" +
      '<button class="icon-btn" data-copy="' + D.esc(it.link) + '" aria-label="Copy link" title="Copy link">' + D.icon("link") + "</button></div></article>";
  }
  function renderFeed() {
    const list = filtered().sort((a, b) => b.t - a.t);
    const page = list.slice(0, state.shown);
    const feed = $("#feed");
    if (!list.length) {
      feed.innerHTML = '<div class="empty-state card">' + D.icon(state.saved ? "bookmark" : "search") + "<b>" + (state.saved ? "No saved stories yet" : "No stories match") + "</b>" +
        (state.saved ? "Tap the bookmark on any story to keep it here." : "Try a wider time range or clear a filter.") + "</div>";
      $("#more").hidden = true;
      return;
    }
    let h = "", cur = "", n = 0;
    page.forEach((it) => {
      if (it.day !== cur) {
        if (cur) h += "</div>";
        cur = it.day;
        const cnt = list.filter((x) => x.day === cur).length;
        h += '<div class="day-head">' + D.dayLabel(cur) + " <span>" + cnt + " " + (cnt === 1 ? "story" : "stories") + '</span></div><div class="feed ' + state.view + '">';
      }
      h += storyHTML(it, n++);
    });
    feed.innerHTML = h + "</div>";
    const more = $("#more");
    more.hidden = list.length <= state.shown;
    more.textContent = "Show more stories (" + (list.length - state.shown) + " left)";
  }

  // ---------- Rendering: sidebar ----------
  function renderTiles() {
    const counts = {};
    filtered("st").forEach((i) => i.states.forEach((s) => { counts[s] = (counts[s] || 0) + 1; }));
    const max = Math.max(1, ...Object.values(counts));
    const cells = [];
    for (let r = 0; r < 8; r++) for (let c = 0; c < 11; c++) cells.push(null);
    Object.entries(D.TILES).forEach(([s, [c, r]]) => { cells[r * 11 + c] = s; });
    $("#tiles").innerHTML = cells.map((s) => {
      if (!s) return "<span></span>";
      const n = counts[s] || 0, k = n ? 18 + Math.round((n / max) * 82) : 0;
      const bg = n ? "color-mix(in srgb, var(--accent) " + k + "%, var(--surface-2))" : "";
      return '<button class="tile' + (n ? " has" : "") + '" data-st="' + s + '" data-n="' + n + '" aria-pressed="' + (state.st === s) + '"' + (bg ? ' style="background:' + bg + (k > 55 ? ";color:var(--accent-ink)" : "") + '"' : "") + (n || state.st === s ? "" : " disabled") + ' aria-label="' + D.STATES[s] + ": " + n + ' stories">' + s + "</button>";
    }).join("");
  }
  function renderSpark() {
    // The chart always spans 30 days, so it ignores the range and day filters.
    const counts = {};
    pool().forEach((it) => { if (match(it, ["range", "day"])) counts[it.day] = (counts[it.day] || 0) + 1; });
    const days = [];
    for (let i = 29; i >= 0; i--) { const d = new Date(); d.setDate(d.getDate() - i); days.push(D.dayKey(d.toISOString())); }
    const max = Math.max(1, ...days.map((k) => counts[k] || 0));
    $("#spark").innerHTML = days.map((k, i) => {
      const n = counts[k] || 0;
      return '<button data-day="' + k + '" data-n="' + n + '" class="' + (n ? "" : "zero") + '" aria-pressed="' + (state.day === k) + '" style="height:' + Math.max(4, (n / max) * 100) + "%;animation-delay:" + i * 15 + 'ms" aria-label="' + D.dayLabel(k) + ": " + n + ' stories"></button>';
    }).join("");
    $("#sparkAxis").innerHTML = "<span>" + D.fmtDate(days[0], { month: "short", day: "numeric" }) + "</span><span>Today</span>";
  }
  function renderCos() {
    const counts = {};
    filtered("co").forEach((i) => i.cos.forEach((s) => { counts[s] = (counts[s] || 0) + 1; }));
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
    const max = top.length ? top[0][1] : 1;
    $("#cos").innerHTML = top.length ? top.map(([s, n], i) => {
      const c = coBySlug[s], tone = (D.TYPES[c.type] || {}).tone;
      return '<button class="bar-row" data-co="' + s + '" style="--tone:' + tone + '"><span class="av">' + D.esc(D.initials(c)) + '</span><span><span class="bar-label">' + D.esc(c.name) + (state.co === s ? " ✓" : "") +
        '</span><span class="bar-track"><i style="width:' + (n / max) * 100 + "%;animation-delay:" + i * 50 + 'ms"></i></span></span><span class="n">' + n + "</span></button>";
    }).join("") : '<p class="muted" style="font-size:13.5px;margin:0">No company mentions for these filters.</p>';
  }

  function render(resetPage) {
    if (resetPage) state.shown = PAGE;
    renderChips();
    renderSelects();
    renderActive();
    renderFeed();
    renderTiles();
    renderSpark();
    renderCos();
    renderView();
    writeHash();
  }
  function renderView() {
    $("#view").innerHTML = [["list", "list", "List view"], ["grid", "grid", "Grid view"]].map((v) =>
      '<button data-v="' + v[0] + '" aria-pressed="' + (state.view === v[0]) + '" aria-label="' + v[2] + '" title="' + v[2] + '">' + D.icon(v[1]) + "</button>").join("");
  }

  // ---------- Events ----------
  function bind() {
    const q = $("#q");
    q.value = state.q;
    q.addEventListener("input", D.debounce(() => { state.q = q.value.trim(); render(true); }, 180));
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement.tagName !== "INPUT") { e.preventDefault(); q.focus(); }
      if (e.key === "Escape" && document.activeElement === q) { q.value = ""; state.q = ""; render(true); q.blur(); }
    });
    $("#state").addEventListener("change", (e) => { state.st = e.target.value; render(true); });
    $("#company").addEventListener("change", (e) => { state.co = e.target.value; render(true); });
    $("#range").addEventListener("change", (e) => { state.range = Number(e.target.value); D.store("range", state.range); render(true); });
    $("#more").addEventListener("click", () => { state.shown += PAGE; renderFeed(); });

    document.addEventListener("click", (e) => {
      const t = e.target.closest("button");
      if (!t) return;
      if (t.dataset.cat !== undefined) { state.cat = t.dataset.cat; state.saved = false; render(true); }
      else if (t.dataset.saved) { state.saved = !state.saved; state.cat = ""; render(true); }
      else if (t.dataset.st) { state.st = state.st === t.dataset.st ? "" : t.dataset.st; render(true); if (t.classList.contains("tag")) scrollToFeed(); }
      else if (t.dataset.co) { state.co = state.co === t.dataset.co ? "" : t.dataset.co; render(true); if (t.classList.contains("tag")) scrollToFeed(); }
      else if (t.dataset.day) { state.day = state.day === t.dataset.day ? "" : t.dataset.day; render(true); }
      else if (t.dataset.v) { state.view = t.dataset.v; D.store("view", state.view); renderView(); renderFeed(); }
      else if (t.dataset.clear) {
        const k = t.dataset.clear;
        if (k === "all") { Object.assign(state, { q: "", cat: "", st: "", co: "", day: "", saved: false }); q.value = ""; }
        else { state[k] = ""; if (k === "q") q.value = ""; }
        render(true);
      } else if (t.dataset.save) {
        const id = t.dataset.save, it = items.find((x) => x.id === id) || saved[id];
        if (saved[id]) { delete saved[id]; D.toast("Removed from saved"); }
        else { saved[id] = { id, title: it.title, link: it.link, source: it.source, published: it.published, category: it.category, states: it.states, capacity_mw: it.capacity_mw, investment_usd_b: it.investment_usd_b }; D.toast("Saved — find it under the Saved chip"); }
        D.store("saved", saved);
        t.setAttribute("aria-pressed", !!saved[id]);
        renderChips();
        if (state.saved) renderFeed();
      } else if (t.dataset.copy) {
        (navigator.clipboard ? navigator.clipboard.writeText(t.dataset.copy) : Promise.reject()).then(() => D.toast("Link copied"), () => D.toast("Couldn't copy link"));
      }
    });

    const spark = $("#spark");
    spark.addEventListener("mousemove", (e) => {
      const b = e.target.closest("button");
      if (!b) return D.tip(null);
      const r = b.getBoundingClientRect();
      D.tip("<b>" + b.dataset.n + "</b> stories · " + D.dayLabel(b.dataset.day), r.left + r.width / 2, r.top);
    });
    spark.addEventListener("mouseleave", () => D.tip(null));
    const tiles = $("#tiles");
    tiles.addEventListener("mousemove", (e) => {
      const b = e.target.closest(".tile");
      if (!b) return D.tip(null);
      const r = b.getBoundingClientRect();
      D.tip("<b>" + D.STATES[b.dataset.st] + "</b> · " + b.dataset.n + " stories", r.left + r.width / 2, r.top);
    });
    tiles.addEventListener("mouseleave", () => D.tip(null));

    const tb = $("#toolbar");
    const onScroll = () => tb.classList.toggle("stuck", tb.getBoundingClientRect().top <= parseInt(getComputedStyle(document.documentElement).getPropertyValue("--header-h")) + 1);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("hashchange", () => { readHash(); q.value = state.q; render(true); });
  }
  function scrollToFeed() {
    const tb = $("#toolbar");
    const y = tb.getBoundingClientRect().top + scrollY - 70;
    if (scrollY > y) window.scrollTo({ top: y, behavior: "smooth" });
  }

  // ---------- Boot ----------
  readHash();
  Promise.all([D.loadJSON("data/news.json"), D.loadJSON("data/companies.json")])
    .then(([news, cos]) => {
      companies = cos.companies;
      companies.forEach((c) => { coBySlug[c.slug] = c; });
      matchCos = D.companyMatcher(companies);
      items = (news.items || []).map(prep);
      renderStats(news);
      renderFeatured();
      bind();
      render(true);
      D.ready();
    })
    .catch((err) => {
      console.error(err);
      $("#feed").innerHTML = '<div class="empty-state card">' + D.icon("alert") + "<b>Couldn't load the news feed</b>Try reloading the page in a minute.</div>";
      D.fail("Couldn't load data. Retrying won't hurt.");
    });
})();
