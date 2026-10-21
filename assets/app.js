// The Rack Report: shared runtime. Shell (sidebar, top bar, tab bar, footer), loader,
// data loading and normalization, formatting, and small UI patterns used by every page.
window.RR = (function () {
  "use strict";
  const REPO = "https://github.com/awigaikwad02/datacenter-watch";
  const LINKEDIN = "https://www.linkedin.com/in/avishkar-gaikwad-/";
  const contact = (cls) => '<a class="contact' + (cls ? " " + cls : "") + '" href="' + LINKEDIN + '" target="_blank" rel="noopener" aria-label="Contact AG on LinkedIn"><span class="initials" aria-hidden="true">AG</span><span>Contact on LinkedIn</span></a>';
  const DAY = 864e5;

  // ---------- Icons (24px stroke) ----------
  const P = {
    overview: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    news: '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/>',
    map: '<path d="M14.1 6.3 9.9 4.2a2 2 0 0 0-1.8 0L3.6 6.5A1 1 0 0 0 3 7.4v12.1a1 1 0 0 0 1.4.9l3.7-1.9a2 2 0 0 1 1.8 0l4.2 2.1a2 2 0 0 0 1.8 0l4.5-2.3a1 1 0 0 0 .6-.9V5.3a1 1 0 0 0-1.4-.9l-3.7 1.9a2 2 0 0 1-1.8 0ZM15 6.6v14.2M9 3.2v14.2"/>',
    building: '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4"/>',
    learn: '<path d="M21.4 10.9a1 1 0 0 0 0-1.8L12.8 5.2a2 2 0 0 0-1.7 0L2.6 9.1a1 1 0 0 0 0 1.8l8.6 3.9a2 2 0 0 0 1.7 0ZM22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    method: '<path d="M9 3h6M10 3v6.3L4.7 18.5A1.7 1.7 0 0 0 6.2 21h11.6a1.7 1.7 0 0 0 1.5-2.5L14 9.3V3M7.5 15h9"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    bookmark: '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>',
    share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    external: '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    zap: '<path d="M4 14a1 1 0 0 1-.8-1.6l9.9-10.2a.5.5 0 0 1 .9.5l-1.9 6A1 1 0 0 0 13 10h7a1 1 0 0 1 .8 1.6l-9.9 10.2a.5.5 0 0 1-.9-.5l1.9-6A1 1 0 0 0 11 14z"/>',
    pin: '<path d="M20 10c0 5-5.5 10.2-7.4 11.8a1 1 0 0 1-1.2 0C9.5 20.2 4 15 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    dollar: '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    trend: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    layers: '<path d="m12.8 2.2 8.6 3.9a1 1 0 0 1 0 1.8l-8.6 3.9a2 2 0 0 1-1.7 0L2.6 7.9a1 1 0 0 1 0-1.8l8.6-3.9a2 2 0 0 1 1.7 0Z"/><path d="m2 12 9.2 4.2a2 2 0 0 0 1.6 0L22 12M2 17l9.2 4.2a2 2 0 0 0 1.6 0L22 17"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    filter: '<path d="M22 3H2l8 9.5V19l4 2v-8.5z"/>',
    focus: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/>',
    arrow: '<path d="M5 12h14M12 5l7 7-7 7"/>',
    arrowL: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3M12 9v4M12 17h.01"/>',
    spark: '<path d="M9.9 15.5A2 2 0 0 0 8.5 14l-6.1-1.6a.5.5 0 0 1 0-1L8.5 9.9A2 2 0 0 0 10 8.5l1.6-6.1a.5.5 0 0 1 1 0L14 8.5A2 2 0 0 0 15.5 10l6.1 1.6a.5.5 0 0 1 0 1L15.5 14a2 2 0 0 0-1.4 1.4l-1.6 6.1a.5.5 0 0 1-1 0Z"/>',
    cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
    plug: '<path d="M12 22v-5M9 8V2M15 8V2M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.7 9a1 1 0 0 1-.7 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.2-2.7a1.2 1.2 0 0 1 1.5 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/>',
    fan: '<path d="M10.8 9.9a3 3 0 0 1 1.2-.3c-1.6-4.2.8-7.6 4-7.6 3.8 0 4.2 4.5 1.8 7.3M14.1 10.8a3 3 0 0 1 .3 1.2c4.2-1.6 7.6.8 7.6 4 0 3.8-4.5 4.2-7.3 1.8M13.2 14.1a3 3 0 0 1-1.2.3c1.6 4.2-.8 7.6-4 7.6-3.8 0-4.2-4.5-1.8-7.3M9.9 13.2a3 3 0 0 1-.3-1.2C5.4 13.6 2 11.2 2 8c0-3.8 4.5-4.2 7.3-1.8"/><circle cx="12" cy="12" r="1"/>',
    battery: '<rect x="2" y="7" width="16" height="10" rx="2"/><path d="M22 11v2M6 11v2M10 11v2"/>',
    tower: '<path d="M4.9 16.1A9 9 0 0 1 4.9 3.9M7.8 13.2a5 5 0 0 1 0-7.1M12 9v13M16.2 6.1a5 5 0 0 1 0 7.1M19.1 3.9a9 9 0 0 1 0 12.2"/><circle cx="12" cy="9" r="1"/>',
    factory: '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2ZM17 18h1M12 18h1M7 18h1"/>',
    toggle: '<rect x="2" y="6" width="20" height="12" rx="6"/><circle cx="16" cy="12" r="2"/>',
    box: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18"/>',
    server: '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>',
    github: '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.1-1.3-.3-2.5-1-3.5.3-1.2.3-2.4 0-3.5 0 0-1 0-3 1.5-2.6-.5-5.4-.5-8 0C6 2 5 2 5 2c-.3 1.1-.3 2.3 0 3.5A5.4 5.4 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.4.5-.7 1-.8 1.6-.2.6-.2 1.2-.2 1.9v4M9 18c-4.5 2-5-2-7-2"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    acre: '<path d="M3 21h18M5 21V11l7-6 7 6v10M9 21v-6h6v6"/>',
    activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  };
  function icon(name, cls) {
    return '<svg class="ic' + (cls ? " " + cls : "") + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (P[name] || "") + "</svg>";
  }
  function mark(cls, label) {
    return '<svg class="mark' + (cls ? " " + cls : "") + '" viewBox="0 0 48 48"' + (label ? ' role="img" aria-label="' + label + '"' : ' aria-hidden="true"') + '>' +
      '<rect x="8" y="3.75" width="32" height="40.5" rx="7" fill="none" stroke="currentColor" stroke-width="3.5"/>' +
      '<rect x="14" y="11" width="20" height="4.5" rx="2.25" fill="#B9F542"/>' +
      '<rect x="14" y="18.5" width="20" height="4.5" rx="2.25" fill="currentColor"/>' +
      '<rect x="14" y="26" width="20" height="4.5" rx="2.25" fill="currentColor"/>' +
      '<rect x="14" y="33.5" width="20" height="4.5" rx="2.25" fill="currentColor"/></svg>';
  }
  const wordmark = () => mark() + "<span>The <b>Rack</b> Report</span>";

  // ---------- Formatting ----------
  const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  function ago(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const m = Math.round((Date.now() - d) / 6e4);
    if (m < 1) return "just now";
    if (m < 60) return m + "m ago";
    const h = Math.round(m / 60);
    if (h < 24) return h + "h ago";
    const dd = Math.round(h / 24);
    return dd === 1 ? "1 day ago" : dd + " days ago";
  }
  function fmtDate(iso, opts) {
    const d = typeof iso === "string" && /^\d{4}-\d{2}$/.test(iso) ? new Date(iso + "-15T12:00:00") : new Date(iso);
    return isNaN(d) ? "" : d.toLocaleDateString("en-US", opts || { month: "short", day: "numeric", year: "numeric" });
  }
  function dayKey(t) {
    const d = new Date(t);
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function dayLabel(key) {
    const now = new Date(), y = new Date(now - DAY);
    if (key === dayKey(now)) return "Today";
    if (key === dayKey(y)) return "Yesterday";
    const [Y, M, D] = key.split("-").map(Number);
    return new Date(Y, M - 1, D).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
  }
  const fmtMW = (mw) => (mw == null ? "" : mw >= 1000 ? (mw / 1000).toFixed(mw % 1000 === 0 ? 0 : 1) + " GW" : Math.round(mw).toLocaleString("en-US") + " MW");
  const fmtMoney = (b) => (b == null ? "" : b >= 1 ? "$" + (Math.round(b * 10) / 10) + "B" : "$" + Math.round(b * 1000) + "M");
  const fmtN = (n) => Math.round(n).toLocaleString("en-US");
  function debounce(fn, ms) { let t; return function () { const a = arguments; clearTimeout(t); t = setTimeout(() => fn.apply(this, a), ms); }; }
  function store(key, val) {
    try {
      if (val === undefined) return JSON.parse(localStorage.getItem("rr-" + key));
      localStorage.setItem("rr-" + key, JSON.stringify(val));
    } catch (e) { return null; }
  }
  const reducedMotion = () => window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Reference data ----------
  const STATES = {
    AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California", CO: "Colorado", CT: "Connecticut", DE: "Delaware",
    DC: "District of Columbia", FL: "Florida", GA: "Georgia", HI: "Hawaii", ID: "Idaho", IL: "Illinois", IN: "Indiana", IA: "Iowa",
    KS: "Kansas", KY: "Kentucky", LA: "Louisiana", ME: "Maine", MD: "Maryland", MA: "Massachusetts", MI: "Michigan", MN: "Minnesota",
    MS: "Mississippi", MO: "Missouri", MT: "Montana", NE: "Nebraska", NV: "Nevada", NH: "New Hampshire", NJ: "New Jersey",
    NM: "New Mexico", NY: "New York", NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma", OR: "Oregon",
    PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina", SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah",
    VT: "Vermont", VA: "Virginia", WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming",
  };
  const CATS = {
    "New Announcement": { tone: "var(--c-announce)", icon: "spark" },
    "Expansion": { tone: "var(--c-expansion)", icon: "trend" },
    "Construction": { tone: "var(--c-construct)", icon: "factory" },
    "Power / Utility": { tone: "var(--c-power)", icon: "zap" },
    "Land Acquisition": { tone: "var(--c-land)", icon: "acre" },
    "Policy / Permits": { tone: "var(--c-policy)", icon: "users" },
    "Deals / Investment": { tone: "var(--c-deals)", icon: "dollar" },
    "Operations": { tone: "var(--c-ops)", icon: "activity" },
    "AI Infrastructure": { tone: "var(--c-ai)", icon: "cpu" },
    "Cancelled / Blocked": { tone: "var(--c-cancel)", icon: "x" },
    "General": { tone: "var(--c-general)", icon: "news" },
  };
  const STATUS = {
    "Announced": { tone: "var(--st-announced)", hex: "#a78bfa", step: 1 },
    "Planned": { tone: "var(--st-planned)", hex: "#38bdf8", step: 1 },
    "Under construction": { tone: "var(--st-construction)", hex: "#fbbf24", step: 2 },
    "Operational": { tone: "var(--st-operational)", hex: "#34d399", step: 3 },
    "Expansion": { tone: "var(--st-expansion)", hex: "#f472b6", step: 3 },
    "Cancelled / Blocked": { tone: "var(--st-cancelled)", hex: "#6b7280", step: 0 },
  };
  const CANCELLED = "Cancelled / Blocked";
  const cat = (c) => CATS[c] || CATS.General;
  const status = (s) => STATUS[s] || STATUS.Announced;
  const companyInfo = (name) => (window.RR_COMPANIES && window.RR_COMPANIES[name]) || { type: "Company", desc: "" };
  const TYPE_TONE = { "Hyperscaler": "#38bdf8", "AI lab": "#c084fc", "GPU cloud": "#f472b6", "Developer": "#fbbf24", "Colocation": "#2dd4bf", "Investor": "#818cf8", "Energy": "#facc15", "Bitcoin and AI hosting": "#fb923c", "Company": "#94a3b8" };
  const companyTone = (name) => TYPE_TONE[companyInfo(name).type] || TYPE_TONE.Company;
  function letters(name) {
    const info = companyInfo(name);
    if (info.mark) return info.mark;
    const w = name.split(/\s+/);
    return w.length > 1 ? (w[0][0] + w[1][0]).toUpperCase() : name.slice(0, 2);
  }

  // ---------- Data ----------
  const cache = {};
  function json(path) {
    if (!cache[path]) {
      cache[path] = fetch(path + "?v=" + Math.floor(Date.now() / 3e5)).then((r) => {
        if (!r.ok) throw new Error(path + " returned " + r.status);
        return r.json();
      });
    }
    return cache[path];
  }
  function prepNews(it) {
    const t = new Date(it.published).getTime();
    return Object.assign({}, it, {
      t, day: dayKey(t),
      category: it.category || "General",
      companies: it.companies || [],
      utilities: it.utilities || [],
      states: it.states || (it.state ? [it.state] : []),
      state: it.state || (it.states && it.states[0]) || null,
    });
  }
  let newsP, projP;
  function news() {
    newsP = newsP || json("data/news.json").then((d) => {
      setUpdated(d.updated);
      return { updated: d.updated, items: (d.items || []).map(prepNews).sort((a, b) => b.t - a.t) };
    });
    return newsP;
  }
  // The permanent archive: every month file listed in data/archive/index.json, merged and de-duplicated.
  let archP;
  function archive() {
    archP = archP || json("data/archive/index.json").then((idx) =>
      Promise.all((idx.months || []).map((m) => json(m.file).catch(() => ({ items: [] })))).then((files) => {
        const seen = new Set(), items = [];
        // "filtered" marks archived headlines that today's rules reject (off topic or outside the U.S.).
        files.forEach((f) => (f.items || []).forEach((it) => { if (!it.filtered && !seen.has(it.id)) { seen.add(it.id); items.push(prepNews(it)); } }));
        items.sort((a, b) => b.t - a.t);
        return { index: idx, items, earliest: idx.earliest || (items.length ? items[items.length - 1].published : null) };
      }));
    return archP;
  }
  function placeName(loc) { return (loc || "").replace(/, US$/, ""); }
  function projects() {
    projP = projP || Promise.all([json("data/projects.json"), json("data/project_candidates.json").catch(() => ({ projects: [] }))]).then(([cur, cand]) => {
      const a = (cur.projects || []).map((p) => Object.assign({}, p, {
        curated: true, companies: p.companies || [], place: placeName(p.location),
        date: p.announced || null, t: p.announced ? new Date(p.announced + "-15T12:00:00").getTime() : 0,
        year: p.announced ? Number(p.announced.slice(0, 4)) : null,
      }));
      const b = (cand.projects || []).filter((p) => p.state && STATES[p.state]).map((p) => Object.assign({}, p, {
        curated: false, companies: p.companies || [], place: placeName(p.location),
        date: p.published, t: new Date(p.published).getTime(), year: new Date(p.published).getFullYear(),
      }));
      return a.concat(collapse(b));
    });
    return projP;
  }

  // Detected sites: one per story cluster, placed at the most precise location any of its headlines gave.
  const PRECISION = { city: 4, county: 3, state: 2, source: 1 };
  function collapse(list) {
    const groups = new Map();
    list.forEach((p) => { const k = p.cluster_id || p.id; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(p); });
    return [...groups.values()].map((g) => {
      g.sort((x, y) => (PRECISION[y.precision] || 0) - (PRECISION[x.precision] || 0) || x.t - y.t);
      const lead = g[0], first = g.reduce((m, p) => (p.t < m.t ? p : m), lead);
      return Object.assign({}, lead, {
        companies: [...new Set(g.flatMap((p) => p.companies))],
        stories: g.length, sources: g.map((p) => ({ source: p.source, url: p.source_url, published: p.published, name: p.name })),
        date: first.published, t: first.t, year: new Date(first.t).getFullYear(),
        approx: !PRECISION[lead.precision] || PRECISION[lead.precision] <= 2,
        capacity_mw: lead.capacity_mw || Math.max(0, ...g.map((p) => p.capacity_mw || 0)) || undefined,
        investment_usd_b: lead.investment_usd_b || Math.max(0, ...g.map((p) => p.investment_usd_b || 0)) || undefined,
      });
    });
  }
  // Headlines: one card per story cluster, with every matching headline kept as .members. The card shows
  // the cluster's display headline (most precise place, else earliest) when it is among the matches.
  function stories(list) {
    const groups = new Map();
    list.forEach((it) => {
      const k = it.cluster_id || it.id;
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(it);
    });
    return [...groups.values()].map((members) => {
      const lead = members.find((m) => m.cluster_title && m.title === m.cluster_title) || members[0];
      return Object.assign({}, lead, {
        members,
        companies: [...new Set(members.flatMap((m) => m.companies || []))],
        utilities: [...new Set(members.flatMap((m) => m.utilities || []))],
      });
    }).sort((a, b) => b.t - a.t);
  }

  // ---------- Shell ----------
  const NAV = [
    ["/", "Overview", "overview", "Overview"],
    ["/newsroom", "Newsroom", "news", "News"],
    ["/atlas", "Project Atlas", "map", "Atlas"],
    ["/companies", "Companies", "building", "Companies"],
    ["/learn", "Learn", "learn", "Learn"],
    ["/methodology", "Methodology", "method", "Method"],
  ];
  let updatedIso = null;
  function setUpdated(iso) {
    updatedIso = iso;
    const el = document.getElementById("livePill");
    if (el) el.innerHTML = '<span class="live-dot" aria-hidden="true"></span><span>Updated ' + esc(ago(iso)) + "</span>";
  }
  function shell(active, title) {
    document.body.classList.add("has-shell");
    const navLinks = (labelIdx) => NAV.map((n) => '<a href="' + n[0] + '"' + (n[0] === active ? ' aria-current="page"' : "") + ">" + icon(n[2]) + "<span>" + n[labelIdx] + "</span></a>").join("");
    const side = document.getElementById("sidebar");
    if (side) {
      side.innerHTML = '<a class="brand" href="/" aria-label="The Rack Report home">' + wordmark() + "</a>" +
        '<nav class="side-nav" aria-label="Main">' + navLinks(1) + "</nav>" +
        '<div class="side-foot">' + contact() +
        '<a href="' + REPO + '" rel="noopener">' + icon("github") + " Source on GitHub</a></div>";
    }
    const top = document.getElementById("topbar");
    if (top) {
      top.innerHTML = '<div class="page"><a class="brand" href="/" aria-label="The Rack Report home">' + wordmark() + "</a>" +
        '<span class="topbar-title">' + esc(title) + '</span><span class="live-pill" id="livePill"><span class="live-dot" aria-hidden="true"></span><span>Refreshed every 3 hours</span></span></div>';
      if (updatedIso) setUpdated(updatedIso);
    }
    const tab = document.getElementById("tabbar");
    if (tab) { tab.setAttribute("aria-label", "Main"); tab.innerHTML = navLinks(3); }
    const foot = document.getElementById("footer");
    if (foot) {
      foot.innerHTML = '<div class="page"><div><a class="brand" href="/">' + wordmark() + "</a>" +
        "<p>Independent tracking of the U.S. data center buildout: headlines, projects, companies and the infrastructure behind them. Headlines link to the original publishers; tags and locations are detected automatically and can be wrong.</p></div>" +
        '<div><h2>Explore</h2><ul>' + NAV.map((n) => '<li><a href="' + n[0] + '">' + n[1] + "</a></li>").join("") + "</ul></div>" +
        '<div><h2>Sources</h2><ul><li>Google News RSS (U.S. edition)</li><li>Google Alerts RSS</li><li>Map data and tiles © OpenStreetMap contributors</li><li><a href="' + REPO + '" rel="noopener">GitHub repository</a></li></ul><h2 style="margin-top:16px">Contact</h2>' + contact() + "</div></div>";
    }
  }

  // ---------- Loader ----------
  const T0 = performance.now();
  const loaderEl = document.getElementById("loader");
  let loaderTimer;
  if (loaderEl && !document.documentElement.classList.contains("no-loader")) {
    const msgs = ["Initializing The Rack Report…", "Scanning U.S. infrastructure signals…", "Loading data center intelligence…"];
    let i = 0;
    const txt = loaderEl.querySelector(".ld-text");
    loaderTimer = setInterval(() => { i = (i + 1) % msgs.length; if (txt) txt.textContent = msgs[i]; }, 380);
    setTimeout(hideLoader, 1150);
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-sources]");
    if (!b) return;
    const ul = document.getElementById("srcs-" + b.dataset.sources);
    if (!ul) return;
    ul.hidden = !ul.hidden;
    b.setAttribute("aria-expanded", String(!ul.hidden));
  });
  function hideLoader() {
    clearInterval(loaderTimer);
    if (!loaderEl || loaderEl.classList.contains("done")) return;
    loaderEl.classList.add("done");
    setTimeout(() => loaderEl.remove(), 300);
  }
  function ready() {
    setTimeout(hideLoader, Math.max(0, 450 - (performance.now() - T0)));
    reveal();
  }

  // ---------- UI helpers ----------
  let io;
  function reveal(root) {
    const els = (root || document).querySelectorAll(".reveal:not(.in)");
    if (reducedMotion() || !("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("in")); return; }
    io = io || new IntersectionObserver((ents) => ents.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } }), { rootMargin: "0px 0px -30px 0px" });
    els.forEach((e) => io.observe(e));
  }
  function countUp(el, to, fmt) {
    fmt = fmt || fmtN;
    if (reducedMotion() || !to) { el.innerHTML = fmt(to); return; }
    const t0 = performance.now(), dur = 900;
    (function step(t) {
      const k = Math.min(1, (t - t0) / dur);
      el.innerHTML = fmt(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(step);
    })(t0);
  }
  let toastEl, toastT;
  function toast(msg) {
    if (!toastEl) { toastEl = document.createElement("div"); toastEl.className = "toast"; toastEl.setAttribute("role", "status"); document.body.appendChild(toastEl); }
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastT);
    toastT = setTimeout(() => toastEl.classList.remove("show"), 1900);
  }
  let tipEl;
  function tip(html, x, y) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; tipEl.setAttribute("role", "tooltip"); document.body.appendChild(tipEl); }
    if (html == null) { tipEl.classList.remove("show"); return; }
    tipEl.innerHTML = html;
    tipEl.style.left = x + "px";
    tipEl.style.top = y + "px";
    tipEl.classList.add("show");
  }
  // Elements with data-tip show a tooltip on hover and focus.
  document.addEventListener("mouseover", (e) => { const t = e.target.closest("[data-tip]"); if (t) { const r = t.getBoundingClientRect(); tip(esc(t.dataset.tip), r.left + r.width / 2, r.top); } });
  document.addEventListener("mouseout", (e) => { if (e.target.closest("[data-tip]")) tip(null); });
  document.addEventListener("focusin", (e) => { const t = e.target.closest("[data-tip]"); if (t) { const r = t.getBoundingClientRect(); tip(esc(t.dataset.tip), r.left + r.width / 2, r.top); } });
  document.addEventListener("focusout", () => tip(null));

  function copy(text) {
    return (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(() => toast("Link copied"), () => toast("Couldn't copy the link"));
  }
  function share(title, url) {
    if (navigator.share) return navigator.share({ title, url }).catch(() => {});
    return copy(url);
  }
  // Saved headlines live in localStorage as {id: item}.
  const saved = {
    all: () => store("saved") || {},
    has: (id) => !!(store("saved") || {})[id],
    toggle(item) {
      const s = store("saved") || {};
      if (s[item.id]) delete s[item.id];
      else s[item.id] = { id: item.id, title: item.title, link: item.link, source: item.source, published: item.published, category: item.category, state: item.state, states: item.states, companies: item.companies, capacity_mw: item.capacity_mw, investment_usd_b: item.investment_usd_b };
      store("saved", s);
      return !!s[item.id];
    },
  };

  // Keeps focus inside a dialog while it is open; Escape calls onClose.
  function trapFocus(el, onClose) {
    const prev = document.activeElement;
    const sel = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea, [tabindex]:not([tabindex="-1"])';
    function key(e) {
      if (e.key === "Escape") { e.preventDefault(); onClose(); return; }
      if (e.key !== "Tab") return;
      const f = [...el.querySelectorAll(sel)].filter((x) => x.offsetParent !== null || x === document.activeElement);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (!el.contains(document.activeElement)) { e.preventDefault(); (e.shiftKey ? last : first).focus(); return; }
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", key);
    // The dialog may still be fading in (visibility: hidden), so retry until focus lands.
    const focusFirst = () => { const f = el.querySelector("[data-autofocus]") || el.querySelector(sel); if (f) f.focus(); return el.contains(document.activeElement); };
    [30, 120, 360].forEach((ms) => setTimeout(() => { if (!el.contains(document.activeElement)) focusFirst(); }, ms));
    return () => { document.removeEventListener("keydown", key); if (prev && prev.focus) prev.focus(); };
  }

  // Horizontal bar chart as inline SVG. rows: [{label, value, hi}]
  function miniBars(rows, opts) {
    opts = opts || {};
    // Draw at the container's real width so text stays at its natural size.
    const W = Math.max(280, Math.round(opts.width || 360)), rowH = 30, labelW = opts.labelW || 128, valW = 40, barW = W - labelW - valW - 8;
    const max = Math.max(1, ...rows.map((r) => r.value));
    const H = rows.length * rowH;
    let s = '<svg class="minibars" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc((opts.label || "Bar chart") + ": " + rows.map((r) => r.label + " " + r.value).join(", ")) + '">';
    rows.forEach((r, i) => {
      const y = i * rowH, w = Math.max(3, (r.value / max) * barW);
      s += '<text class="lbl" x="0" y="' + (y + 19) + '">' + esc(r.label.length > 16 ? r.label.slice(0, 15) + "…" : r.label) + "</text>";
      s += '<rect class="track" x="' + labelW + '" y="' + (y + 9) + '" width="' + barW + '" height="12" rx="4"/>';
      s += '<rect class="bar' + (r.hi ? " hi" : "") + '" x="' + labelW + '" y="' + (y + 9) + '" width="' + w.toFixed(1) + '" height="12" rx="4" style="animation-delay:' + i * 60 + 'ms"/>';
      s += '<text class="val" x="' + W + '" y="' + (y + 19) + '" text-anchor="end">' + fmtN(r.value) + "</text>";
    });
    return s + "</svg>";
  }

  // ---------- News card ----------
  function newsTags(it, opts) {
    opts = opts || {};
    let h = '<span class="tag" style="--tone:' + cat(it.category).tone + '"><span class="dot"></span>' + esc(it.category) + "</span>";
    if (it.state) h += (opts.buttons ? '<button class="tag plain" data-state="' + it.state + '">' : '<span class="tag plain">') + icon("pin") + esc(STATES[it.state] || it.state) + (opts.buttons ? "</button>" : "</span>");
    (it.companies || []).slice(0, 2).forEach((c) => { h += (opts.buttons ? '<button class="tag plain" data-company="' + esc(c) + '">' : '<span class="tag plain">') + icon("building") + esc(c) + (opts.buttons ? "</button>" : "</span>"); });
    if (it.capacity_mw) h += '<span class="tag num" style="--tone:var(--c-power)">' + icon("zap") + fmtMW(it.capacity_mw) + "</span>";
    if (it.investment_usd_b) h += '<span class="tag num" style="--tone:var(--c-deals)">' + fmtMoney(it.investment_usd_b) + "</span>";
    return h;
  }
  function newsCard(it, i) {
    const isNew = Date.now() - it.t < 12 * 36e5;
    return '<article class="card lift news-card" style="--tone:' + cat(it.category).tone + '">' +
      '<div class="news-meta"><span class="src">' + esc(it.source || "Unknown source") + '</span><span aria-hidden="true">·</span><time datetime="' + esc(it.published) + '" title="' + esc(fmtDate(it.published)) + '">' + esc(ago(it.published)) + "</time>" + (isNew ? '<span class="new">NEW</span>' : "") + "</div>" +
      '<h3><a href="' + esc(it.link) + '" target="_blank" rel="noopener">' + esc(it.title) + "</a></h3>" +
      '<div class="news-foot"><div class="news-tags">' + newsTags(it, { buttons: true }) + "</div>" +
      '<div class="news-actions">' + (it.members && it.members.length > 1 ? '<button class="link-btn srcs-btn" aria-expanded="false" data-sources="' + esc(it.id) + '">' + it.members.length + " sources</button>" : "") + '<button class="icon-btn" data-save="' + esc(it.id) + '" aria-pressed="' + saved.has(it.id) + '" aria-label="Save headline" data-tip="Save">' + icon("bookmark") + "</button>" +
      '<button class="icon-btn" data-share="' + esc(it.id) + '" aria-label="Share headline" data-tip="Share">' + icon("share") + "</button></div></div>" +
      (it.members && it.members.length > 1 ? '<ul class="srcs" id="srcs-' + esc(it.id) + '" hidden>' + it.members.map((m) =>
        '<li><a href="' + esc(m.link) + '" target="_blank" rel="noopener">' + esc(m.title) + "</a><small>" + esc(m.source || "Unknown source") + " · " + esc(ago(m.published)) + "</small></li>").join("") + "</ul>" : "") + "</article>";
  }

  // ---------- Ticker ----------
  function ticker(el, items) {
    const one = (aria) => items.map((it) => '<a href="' + esc(it.link) + '" target="_blank" rel="noopener" style="--tone:' + cat(it.category).tone + '"' + (aria ? ' aria-hidden="true" tabindex="-1"' : "") + ">" + esc(it.title) + " <span>" + esc(it.source) + "</span></a>").join("");
    el.innerHTML = '<div class="ticker-label"><span class="live-dot" aria-hidden="true"></span>LIVE</div><div class="ticker-viewport"><div class="ticker-track" style="--dur:' + Math.max(40, items.length * 9) + 's">' + one(false) + one(true) + "</div></div>";
  }

  // ---------- Maps ----------
  const LEAFLET = [
    ["css", "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", "sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H"],
    ["css", "https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css", "sha384-pmjIAcz2bAn0xukfxADbZIb3t8oRT9Sv0rvO+BR5Csr6Dhqq+nZs59P0pPKQJkEV"],
    ["js", "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js", "sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH"],
    ["js", "https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js", "sha384-eXVCORTRlv4FUUgS/xmOyr66XBVraen8ATNLMESp92FKXLAMiKkerixTiBvXriZr"],
  ];
  let leafletP;
  function loadLeaflet() {
    if (window.L && window.L.markerClusterGroup) return Promise.resolve(window.L);
    leafletP = leafletP || LEAFLET.reduce((p, [kind, url, sri]) => p.then(() => new Promise((res, rej) => {
      const el = document.createElement(kind === "css" ? "link" : "script");
      if (kind === "css") { el.rel = "stylesheet"; el.href = url; } else { el.src = url; }
      el.integrity = sri;
      el.crossOrigin = "anonymous";
      el.onload = res;
      el.onerror = () => rej(new Error("Could not load " + url));
      document.head.appendChild(el);
      if (kind === "css") res();
    })), Promise.resolve()).then(() => window.L);
    return leafletP;
  }
  const US = {
    view: [[24.4, -125], [49.5, -66.9]],
    max: [[15, -180], [72.5, -60]],
  };
  function baseMap(el, opts) {
    const L = window.L;
    const map = L.map(el, Object.assign({ zoomControl: false, minZoom: 3, maxZoom: 13, zoomSnap: 0.25, maxBounds: US.max, maxBoundsViscosity: 1, worldCopyJump: false }, opts || {}));
    // OpenStreetMap's standard tiles need no API key; the .rr-tiles CSS filter turns them dark.
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, bounds: US.max, className: "rr-tiles",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    map.attributionControl.setPrefix(false);
    map.fitBounds(US.view, { padding: [8, 8] });
    return map;
  }
  // Curated projects use the rack mark as their pin; detected ones are rings.
  function pinIcon(p, sel) {
    const L = window.L, tone = status(p.status).tone;
    if (!p.curated) return L.divIcon({ className: sel ? "pin-sel" : "", iconSize: [13, 13], html: '<div class="pin-auto" style="--tone:' + tone + '"></div>' });
    const w = p.capacity_mw ? Math.round(Math.min(26, 15 + Math.sqrt(p.capacity_mw) / 4)) : 15, h = Math.round(w * 1.25);
    return L.divIcon({
      className: sel ? "pin-sel" : "", iconSize: [w, h],
      html: '<svg class="pin-rack" viewBox="0 0 20 25" style="--tone:' + tone + '" aria-hidden="true"><rect class="body" x="1" y="1" width="18" height="23" rx="4"/><rect class="slot" x="5" y="6" width="10" height="2.4" rx="1.2"/><rect class="slot" x="5" y="11.3" width="10" height="2.4" rx="1.2"/><rect class="slot" x="5" y="16.6" width="10" height="2.4" rx="1.2"/></svg>',
    });
  }
  function clusterGroup() {
    return window.L.markerClusterGroup({
      showCoverageOnHover: false, maxClusterRadius: 44, spiderfyOnMaxZoom: true, disableClusteringAtZoom: 8,
      // Approximate (state-level) markers carry options.approx; their stories are shown as a small "~N" line.
      iconCreateFunction: (c) => {
        let n = 0, a = 0;
        c.getAllChildMarkers().forEach((m) => { if (m.options.approx) a += m.options.approx; else n++; });
        if (!n) { const s = Math.round(Math.min(56, 28 + Math.sqrt(a) * 5)); return window.L.divIcon({ className: "", iconSize: [s, s], html: '<div class="bubble" title="' + a + ' stories, location approximate">~' + a + "</div>" }); }
        const s = (n < 10 ? 34 : n < 30 ? 40 : 46) + (a ? 8 : 0);
        return window.L.divIcon({ className: "", iconSize: [s, s], html: '<div class="cluster' + (a ? " has-apx" : "") + '"' + (a ? ' title="' + n + " sites, plus " + a + ' stories with approximate location"' : "") + ">" + n + (a ? '<small class="apx" aria-label="plus ' + a + ' approximate">~' + a + "</small>" : "") + "</div>" });
      },
    });
  }
  function legendHTML() {
    return Object.keys(STATUS).map((s) => '<span class="lg"><i style="--tone:' + STATUS[s].tone + '"></i>' + s + "</span>").join("") +
      '<span class="lg"><i class="auto" style="--tone:var(--faint)"></i>Detected from news</span>' +
      '<span class="lg"><i class="bub"></i>~N: state level only, location approximate</span>';
  }
  // Detected sites known only to the state go into one translucent bubble per state, not pins.
  // With ghost true the markers are small and carry options.approx, for folding into cluster circles.
  function approxBubbles(list, onClick, ghost) {
    const L = window.L, by = {};
    list.filter((p) => !p.curated && p.approx).forEach((p) => {
      const b = by[p.state] || (by[p.state] = { state: p.state, lat: p.lat, lon: p.lon, n: 0 });
      if (p.precision === "state") { b.lat = p.lat; b.lon = p.lon; }
      b.n += p.stories || 1;
    });
    return Object.values(by).map((b) => {
      const s = ghost ? Math.round(Math.min(40, 24 + Math.sqrt(b.n) * 4)) : Math.round(Math.min(64, 30 + Math.sqrt(b.n) * 7)), label = b.n + (b.n === 1 ? " story" : " stories") + ", location approximate";
      const m = L.marker([b.lat, b.lon], { icon: L.divIcon({ className: "", iconSize: [s, s], html: '<div class="bubble">' + (ghost ? "~" : "") + b.n + "</div>" }), title: (STATES[b.state] || b.state) + ": " + label, keyboard: true, zIndexOffset: -500, approx: ghost ? b.n : 0 });
      m.bindTooltip("<b>" + esc(STATES[b.state] || b.state) + "</b><small>" + esc(label) + "</small>", { className: "rr-tip", direction: "top", offset: [0, -s / 2] });
      if (onClick) m.on("click", () => onClick(b.state));
      return m;
    });
  }
  // Approximate bubbles show from zoom 5 in; at country zoom (<= 4) they fold into the cluster circles.
  const APPROX_ZOOM = 4;
  function approxLayer(map, cl, onClick) {
    const layer = window.L.layerGroup().addTo(map);
    let list = [], ghosts = [], low = null;
    function draw() {
      low = map.getZoom() <= APPROX_ZOOM;
      layer.clearLayers();
      if (ghosts.length) cl.removeLayers(ghosts);
      ghosts = [];
      const ms = approxBubbles(list, onClick, low);
      if (low) { ghosts = ms; cl.addLayers(ghosts); } else ms.forEach((m) => layer.addLayer(m));
    }
    map.on("zoomend", () => { if ((map.getZoom() <= APPROX_ZOOM) !== low) draw(); });
    return { set(l) { list = l; draw(); }, refresh: draw };
  }
  // One sentence built only from the record's own fields.
  function summary(p) {
    const names = p.companies.length ? p.companies : p.company ? [p.company] : [];
    const who = names.length > 1 ? names.slice(0, -1).join(", ") + " and " + names[names.length - 1] : names[0] || "An unnamed developer";
    const many = names.length > 1;
    const what = { [CANCELLED]: many ? "were tied to" : "was tied to", "Announced": "announced", "Planned": many ? "are planning" : "is planning", "Under construction": many ? "are building" : "is building", "Operational": many ? "operate" : "operates", "Expansion": many ? "are expanding" : "is expanding" }[p.status] || "are tied to";
    const size = [p.capacity_mw ? fmtMW(p.capacity_mw) : "", p.investment_usd_b ? fmtMoney(p.investment_usd_b) : ""].filter(Boolean).join(", ");
    return p.curated
      ? who + " " + what + " this " + (size ? size + " " : "") + "data center project in " + p.place + "."
      : "Detected from a " + (p.source || "news") + " headline on " + fmtDate(p.published) + ": " + (p.status === CANCELLED ? "a data center project reported cancelled, blocked or paused" : "a " + p.status.toLowerCase() + " data center project") + " in " + p.place + (size ? " (" + size + " mentioned)" : "") + "." +
        (p.stories > 1 ? " " + p.stories + " headlines cover this story." : "");
  }

  return {
    REPO, DAY, icon, mark, esc, ago, fmtDate, dayKey, dayLabel, fmtMW, fmtMoney, fmtN, debounce, store, reducedMotion,
    STATES, CATS, STATUS, CANCELLED, PRECISION, stories, approxBubbles, approxLayer, cat, status, companyInfo, companyTone, letters,
    news, archive, projects, shell, ready, hideLoader, reveal, countUp, toast, tip, copy, share, saved, trapFocus, miniBars,
    newsTags, newsCard, ticker, loadLeaflet, baseMap, pinIcon, clusterGroup, legendHTML, summary, US,
  };
})();
