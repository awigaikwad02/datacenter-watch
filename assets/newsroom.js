// Newsroom: featured story, instant filters (company, state, source, topic, time, saved, search), day-grouped cards.
(function () {
  "use strict";
  const R = RR, $ = (s) => document.querySelector(s), DAY = R.DAY, PAGE = 30;
  const f = { q: "", company: "", utility: "", state: "", source: "", topic: "", range: 7, saved: false, archive: false, view: R.store("view") || "list", shown: PAGE };
  // items: data/news.json (the last windowDays days). archived: the whole archive, loaded by the
  // "Include archive" switch. older: archive months needed when the time range is longer than news.json.
  let items = [], archived = null, older = null, windowDays = 90;
  R.shell("/newsroom", "Newsroom");

  // ---------- URL hash <-> filters, so a filtered view can be shared ----------
  const KEYS = ["q", "company", "utility", "state", "source", "topic", "range", "saved", "archive"];
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    KEYS.forEach((k) => { if (h.has(k)) f[k] = k === "range" ? Number(h.get(k)) || 7 : k === "saved" || k === "archive" ? h.get(k) === "1" : h.get(k); });
  }
  function writeHash() {
    const h = new URLSearchParams();
    KEYS.forEach((k) => { const v = f[k]; if (v && !(k === "range" && v === 7)) h.set(k, k === "saved" || k === "archive" ? "1" : v); });
    const s = h.toString();
    history.replaceState(null, "", s ? "#" + s : location.pathname);
  }

  // ---------- Filtering ----------
  // Recent headlines, plus every archived headline when "Include archive" is on.
  function base() {
    const extra = f.archive ? (archived && archived.items) : (f.range > windowDays && older);
    if (!extra) return items;
    const ids = new Set(items.map((i) => i.id));
    return items.concat(extra.filter((i) => !ids.has(i.id)));
  }
  /** When the chosen range reaches past what news.json holds, load just those archive months once. */
  function loadOlder() {
    if (f.archive || f.range <= windowDays || older) return;
    older = [];
    R.archiveSince(Date.now() - 90 * DAY).then((list) => { older = list; render(false); })
      .catch((err) => { console.error(err); older = null; R.toast("Couldn't load older headlines"); });
  }
  function pool() {
    const items = base();
    if (!f.saved) return items;
    const s = R.saved.all(), ids = new Set(items.map((i) => i.id));
    const gone = Object.values(s).filter((x) => !ids.has(x.id)).map((x) => Object.assign({}, x, { t: new Date(x.published).getTime(), companies: x.companies || [], utilities: x.utilities || [], states: x.states || [], category: x.category || "General" }));
    return items.filter((i) => s[i.id]).concat(gone);
  }
  function match(it, skip) {
    if (skip !== "range" && !f.saved && !f.archive && Date.now() - it.t > f.range * DAY) return false;
    if (skip !== "company" && f.company && !it.companies.includes(f.company)) return false;
    if (skip !== "utility" && f.utility && !(it.utilities || []).includes(f.utility)) return false;
    if (skip !== "state" && f.state && it.state !== f.state && !(it.states || []).includes(f.state)) return false;
    if (skip !== "source" && f.source && it.source !== f.source) return false;
    if (skip !== "topic" && f.topic && it.category !== f.topic) return false;
    if (f.q) {
      const hay = (it.title + " " + it.source + " " + (it.state ? R.STATES[it.state] : "") + " " + it.companies.join(" ") + " " + (it.utilities || []).join(" ")).toLowerCase();
      if (!f.q.toLowerCase().split(/\s+/).every((w) => hay.includes(w))) return false;
    }
    return true;
  }
  const filtered = (skip) => pool().filter((it) => match(it, skip)).sort((a, b) => b.t - a.t);

  // ---------- Rendering ----------
  function featured() {
    const now = Date.now();
    const score = (i) => (i.category === "New Announcement" || i.category === "Construction" || i.category === "Expansion" ? 3 : 0) + (i.capacity_mw ? 2 : 0) + (i.investment_usd_b ? 2 : 0) + (i.state ? 1 : 0) + Math.min(2, i.companies.length) - (now - i.t) / DAY;
    const top = items.filter((i) => now - i.t <= 3 * DAY).sort((a, b) => score(b) - score(a))[0] || items[0];
    if (!top) { $("#featured").innerHTML = ""; return; }
    const c = R.cat(top.category);
    $("#featured").innerHTML = '<article class="card lift feature" style="--tone:' + c.tone + '"><span class="eyebrow">' + R.icon("spark") + "Top story · " + R.esc(top.category) + "</span>" +
      '<h2><a href="' + R.esc(top.link) + '" target="_blank" rel="noopener">' + R.esc(top.title) + "</a></h2>" +
      '<div class="news-foot"><div class="news-meta"><span class="src">' + R.esc(top.source) + "</span><span>·</span><span>" + R.ago(top.published) + '</span></div></div><div class="news-tags" style="margin-top:12px">' + R.newsTags(top, { buttons: true }) + "</div></article>";
  }
  function options(sel, values, label, current, fmt) {
    const opts = Object.entries(values).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    if (current && !values[current]) opts.unshift([current, 0]);
    sel.innerHTML = '<option value="">' + label + "</option>" + opts.map(([v, n]) => '<option value="' + R.esc(v) + '"' + (v === current ? " selected" : "") + ">" + R.esc(fmt ? fmt(v) : v) + " (" + n + ")</option>").join("");
  }
  function counts(skip, key) {
    const c = {};
    filtered(skip).forEach((i) => [].concat(key(i)).forEach((v) => { if (v) c[v] = (c[v] || 0) + 1; }));
    return c;
  }
  function controls() {
    options($("#company"), counts("company", (i) => i.companies), "All companies", f.company);
    options($("#utility"), counts("utility", (i) => i.utilities || []), "All utilities", f.utility);
    options($("#state"), counts("state", (i) => i.state), "All states", f.state, (s) => R.STATES[s] || s);
    const src = counts("source", (i) => i.source), top = Object.fromEntries(Object.entries(src).sort((a, b) => b[1] - a[1]).slice(0, 40));
    options($("#source"), top, "All sources", f.source);
    $("#saved").value = f.saved ? "1" : "";
    document.querySelectorAll("#range button").forEach((b) => { b.setAttribute("aria-pressed", String(Number(b.dataset.range) === f.range && !f.saved && !f.archive)); b.disabled = f.saved || f.archive; });
    $("#archiveBtn").setAttribute("aria-checked", String(f.archive));
    const note = $("#archiveNote");
    note.hidden = !f.archive;
    if (f.archive) note.innerHTML = R.icon("layers") + (archived
      ? "<span>Searching the full archive: <b>" + base().length.toLocaleString("en-US") + "</b> headlines going back to <b>" + R.esc(R.fmtDate(archived.earliest, { month: "long", day: "numeric", year: "numeric" })) + "</b>. Time range filters are off while the archive is included.</span>"
      : "<span>Loading the archive…</span>");
    const tc = counts("topic", (i) => i.category), all = filtered("topic").length;
    $("#topics").innerHTML = '<button class="chip" data-topic="" aria-pressed="' + !f.topic + '">All topics <span class="n">' + all + "</span></button>" +
      Object.keys(R.CATS).filter((k) => tc[k] || f.topic === k).map((k) => '<button class="chip" data-topic="' + R.esc(k) + '" style="--tone:' + R.CATS[k].tone + '" aria-pressed="' + (f.topic === k) + '"><span class="dot"></span>' + k + ' <span class="n">' + (tc[k] || 0) + "</span></button>").join("");
    $("#view").innerHTML = [["list", "list", "List view"], ["grid", "grid", "Grid view"]].map((v) => '<button data-view="' + v[0] + '" aria-pressed="' + (f.view === v[0]) + '" aria-label="' + v[2] + '" data-tip="' + v[2] + '">' + R.icon(v[1]) + "</button>").join("");
    const act = [];
    if (f.q) act.push(["q", "“" + f.q + "”"]);
    if (f.company) act.push(["company", f.company]);
    if (f.utility) act.push(["utility", f.utility]);
    if (f.state) act.push(["state", R.STATES[f.state] || f.state]);
    if (f.source) act.push(["source", f.source]);
    if (f.topic) act.push(["topic", f.topic]);
    if (f.saved) act.push(["saved", "Saved only"]);
    $("#active").innerHTML = act.length ? act.map((a) => '<button class="tag" data-clear="' + a[0] + '" aria-label="Remove filter ' + R.esc(a[1]) + '">' + R.esc(a[1]) + R.icon("x") + "</button>").join("") + '<button class="link-btn" data-clear="all">Clear all</button>' : "";
  }
  function feed() {
    const raw = filtered(), list = R.stories(raw);
    const rangeLabel = f.saved ? "saved" : f.archive ? "in the archive" : { 1: "today", 7: "this week", 31: "this month", 90: "in the last 90 days" }[f.range];
    $("#count").textContent = list.length.toLocaleString("en-US") + " stor" + (list.length === 1 ? "y" : "ies") + (raw.length !== list.length ? " (" + raw.length.toLocaleString("en-US") + " headlines)" : "") + " " + rangeLabel;
    if (!list.length) {
      $("#feed").innerHTML = '<div class="card empty" style="margin-top:20px">' + R.icon(f.saved ? "bookmark" : "search") + "<b>" + (f.saved ? "Nothing saved yet" : "No headlines match these filters") + "</b>" +
        (f.saved ? "Use the bookmark on any headline to keep it here. Saved items stay in this browser." : "Try a longer time range, another topic, or clear a filter.") + "</div>";
      $("#more").hidden = true;
      return;
    }
    let h = "", cur = "";
    list.slice(0, f.shown).forEach((it) => {
      const d = R.dayKey(it.t);
      if (d !== cur) {
        if (cur) h += "</div>";
        cur = d;
        const n = list.filter((x) => R.dayKey(x.t) === d).length;
        h += '<h2 class="day-label">' + R.dayLabel(d) + " <span>" + n + " stor" + (n === 1 ? "y" : "ies") + '</span></h2><div class="news-list ' + f.view + '">';
      }
      h += R.newsCard(it);
    });
    $("#feed").innerHTML = h + "</div>";
    $("#more").hidden = list.length <= f.shown;
    $("#more").textContent = "Show more stories (" + (list.length - f.shown) + " more)";
  }
  function render(reset) {
    if (reset) f.shown = PAGE;
    controls();
    feed();
    writeHash();
  }

  // ---------- Events ----------
  function bind() {
    const q = $("#q");
    q.value = f.q;
    q.addEventListener("input", R.debounce(() => { f.q = q.value.trim(); render(true); }, 150));
    ["company", "utility", "state", "source"].forEach((k) => $("#" + k).addEventListener("change", (e) => { f[k] = e.target.value; render(true); }));
    $("#saved").addEventListener("change", (e) => { f.saved = e.target.value === "1"; render(true); });
    $("#archiveBtn").addEventListener("click", () => { f.archive = !f.archive; loadArchive(); render(true); });
    $("#more").addEventListener("click", () => { f.shown += PAGE; feed(); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && !/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) { e.preventDefault(); q.focus(); }
    });
    document.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      const d = b.dataset;
      if (d.range) { f.range = Number(d.range); loadOlder(); render(true); }
      else if (d.topic !== undefined) { f.topic = d.topic; render(true); const c = document.querySelector('#topics [data-topic="' + CSS.escape(d.topic) + '"]'); if (c) c.classList.add("pop"); }
      else if (d.view) { f.view = d.view; R.store("view", f.view); controls(); feed(); }
      else if (d.state) { f.state = d.state; render(true); $("#filters").scrollIntoView({ behavior: R.reducedMotion() ? "auto" : "smooth" }); }
      else if (d.company) { f.company = d.company; render(true); $("#filters").scrollIntoView({ behavior: R.reducedMotion() ? "auto" : "smooth" }); }
      else if (d.clear) {
        if (d.clear === "all") Object.assign(f, { q: "", company: "", utility: "", state: "", source: "", topic: "", saved: false });
        else f[d.clear] = d.clear === "saved" ? false : "";
        q.value = f.q;
        render(true);
      } else if (d.save) {
        const it = pool().find((x) => x.id === d.save);
        if (!it) return;
        const on = R.saved.toggle(it);
        b.setAttribute("aria-pressed", String(on));
        R.toast(on ? "Saved. Find it under Show: Saved only" : "Removed from saved");
        if (f.saved) render(false);
      } else if (d.share) {
        const it = pool().find((x) => x.id === d.share);
        if (it) R.share(it.title, it.link);
      }
    });
    window.addEventListener("hashchange", () => { readHash(); q.value = f.q; loadOlder(); render(true); });
  }

  function loadArchive() {
    if (!f.archive || archived) return;
    R.archive().then((a) => { archived = a; render(false); }).catch((err) => {
      console.error(err);
      f.archive = false;
      R.toast("Couldn't load the archive");
      render(true);
    });
  }

  readHash();
  R.news().then((n) => {
    items = n.items;
    windowDays = n.windowDays;
    loadOlder();
    featured();
    bind();
    render(true);
    loadArchive();
    // New data: keep every filter, the view and how far the reader has scrolled the list.
    R.live((n) => { items = n.items; featured(); render(false); });
    R.ready();
  }).catch((err) => {
    console.error(err);
    $("#feed").innerHTML = '<div class="card empty" style="margin-top:20px">' + R.icon("alert") + "<b>Couldn't load headlines</b>Try reloading the page in a minute.</div>";
    $("#featured").innerHTML = "";
    R.ready();
  });
})();
