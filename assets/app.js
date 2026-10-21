// Shared runtime for Data Center Watch: icons, logo, theme, chrome, loader and helpers.
window.DCW = (function () {
  const START = performance.now();

  // ---------- Icons (24px stroke icons) ----------
  const P = {
    news: '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/>',
    map: '<path d="M14.1 6.3 9.9 4.2a2 2 0 0 0-1.8 0L3.6 6.5A1 1 0 0 0 3 7.4v12.1a1 1 0 0 0 1.4.9l3.7-1.9a2 2 0 0 1 1.8 0l4.2 2.1a2 2 0 0 0 1.8 0l4.5-2.3a1 1 0 0 0 .6-.9V5.3a1 1 0 0 0-1.4-.9l-3.7 1.9a2 2 0 0 1-1.8 0ZM15 6.6v14.2M9 3.2v14.2"/>',
    building: '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4"/>',
    learn: '<path d="M21.4 10.9a1 1 0 0 0 0-1.8L12.8 5.2a2 2 0 0 0-1.7 0L2.6 9.1a1 1 0 0 0 0 1.8l8.6 3.9a2 2 0 0 0 1.7 0ZM22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M6.3 17.7l-1.4 1.4M19.1 4.9l-1.4 1.4"/>',
    moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    bookmark: '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    external: '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    zap: '<path d="M4 14a1 1 0 0 1-.8-1.6l9.9-10.2a.5.5 0 0 1 .9.5l-1.9 6A1 1 0 0 0 13 10h7a1 1 0 0 1 .8 1.6l-9.9 10.2a.5.5 0 0 1-.9-.5l1.9-6A1 1 0 0 0 11 14z"/>',
    trend: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    layers: '<path d="m12.8 2.2 8.6 3.9a1 1 0 0 1 0 1.8l-8.6 3.9a2 2 0 0 1-1.7 0L2.6 7.9a1 1 0 0 1 0-1.8l8.6-3.9a2 2 0 0 1 1.7 0Z"/><path d="m2 12 9.2 4.2a2 2 0 0 0 1.6 0L22 12M2 17l9.2 4.2a2 2 0 0 0 1.6 0L22 17"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    focus: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/>',
    pin: '<path d="M20 10c0 5-5.5 10.2-7.4 11.8a1 1 0 0 1-1.2 0C9.5 20.2 4 15 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    dollar: '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    server: '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>',
    cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
    snow: '<path d="M2 12h20M12 2v20M20 16l-4-4 4-4M4 8l4 4-4 4M16 4l-4 4-4-4M8 20l4-4 4 4"/>',
    plug: '<path d="M12 22v-5M9 8V2M15 8V2M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.7 9a1 1 0 0 1-.7 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.2-2.7a1.2 1.2 0 0 1 1.5 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/>',
    gauge: '<path d="m12 14 4-4M3.3 19a10 10 0 1 1 17.4 0"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3M12 9v4M12 17h.01"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    arrow: '<path d="M5 12h14M12 5l7 7-7 7"/>',
    spark: '<path d="M9.9 15.5A2 2 0 0 0 8.5 14l-6.1-1.6a.5.5 0 0 1 0-1L8.5 9.9A2 2 0 0 0 10 8.5l1.6-6.1a.5.5 0 0 1 1 0L14 8.5A2 2 0 0 0 15.5 10l6.1 1.6a.5.5 0 0 1 0 1L15.5 14a2 2 0 0 0-1.4 1.4l-1.6 6.1a.5.5 0 0 1-1 0Z"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20"/>',
    fan: '<path d="M10.8 9.9a3 3 0 0 1 1.2-.3c-1.6-4.2.8-7.6 4-7.6 3.8 0 4.2 4.5 1.8 7.3M14.1 10.8a3 3 0 0 1 .3 1.2c4.2-1.6 7.6.8 7.6 4 0 3.8-4.5 4.2-7.3 1.8M13.2 14.1a3 3 0 0 1-1.2.3c1.6 4.2-.8 7.6-4 7.6-3.8 0-4.2-4.5-1.8-7.3M9.9 13.2a3 3 0 0 1-.3-1.2C5.4 13.6 2 11.2 2 8c0-3.8 4.5-4.2 7.3-1.8"/><circle cx="12" cy="12" r="1"/>',
    battery: '<rect x="2" y="7" width="16" height="10" rx="2"/><path d="M22 11v2M6 11v2M10 11v2"/>',
    tower: '<path d="M4.9 16.1A9 9 0 0 1 4.9 3.9M7.8 13.2a5 5 0 0 1 0-7.1M12 9v13M16.2 6.1a5 5 0 0 1 0 7.1M19.1 3.9a9 9 0 0 1 0 12.2"/><circle cx="12" cy="9" r="1"/>',
    factory: '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2ZM17 18h1M12 18h1M7 18h1"/>',
    switchI: '<rect x="2" y="6" width="20" height="12" rx="6"/><circle cx="16" cy="12" r="2"/>',
    box: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    water: '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5S5 13 5 15a7 7 0 0 0 7 7z"/>',
    star: '<path d="M11.5 2.3a.5.5 0 0 1 1 0l2.3 4.7a2 2 0 0 0 1.5 1.1l5.2.8a.5.5 0 0 1 .3.9l-3.8 3.7a2 2 0 0 0-.6 1.8l.9 5.2a.5.5 0 0 1-.8.6l-4.6-2.5a2 2 0 0 0-1.9 0l-4.6 2.5a.5.5 0 0 1-.8-.6l.9-5.2a2 2 0 0 0-.6-1.8L1.7 9.8a.5.5 0 0 1 .3-.9l5.2-.8a2 2 0 0 0 1.5-1.1z"/>',
  };
  function icon(name, cls) {
    return '<svg class="ic' + (cls ? " " + cls : "") + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (P[name] || "") + "</svg>";
  }

  // ---------- Logo: a server stack with status lights ----------
  let logoN = 0;
  function logo(cls) {
    const id = "lg" + (++logoN);
    const slab = (y, d) =>
      '<g class="slab"><rect x="14" y="' + y + '" width="36" height="10" rx="3" fill="#fff" fill-opacity=".95"/>' +
      '<rect x="19" y="' + (y + 4) + '" width="14" height="2" rx="1" fill="#0b1324" fill-opacity=".18"/>' +
      '<circle class="led d' + d + '" cx="40" cy="' + (y + 5) + '" r="1.8" fill="#10b981"/>' +
      '<circle class="led d' + (d + 1) + '" cx="45" cy="' + (y + 5) + '" r="1.8" fill="#0ea5e9"/></g>';
    return '<svg class="' + (cls || "") + '" viewBox="0 0 64 64" aria-hidden="true"><defs><linearGradient id="' + id + '" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0" stop-color="#0ea5e9"/><stop offset="1" stop-color="#7c3aed"/></linearGradient></defs>' +
      '<rect x="2" y="2" width="60" height="60" rx="16" fill="url(#' + id + ')"/>' +
      '<path d="M2 40 Q32 30 62 40 V46 Q62 62 46 62 H18 Q2 62 2 46Z" fill="#fff" fill-opacity=".08"/>' +
      slab(14, 1) + slab(27, 2) + slab(40, 3) + "</svg>";
  }

  // ---------- Formatting helpers ----------
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmtDate(iso, opts) {
    const d = new Date(iso);
    return isNaN(d) ? "" : d.toLocaleDateString(undefined, opts || { month: "short", day: "numeric", year: "numeric" });
  }
  function dayKey(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function dayLabel(key) {
    const today = dayKey(new Date().toISOString());
    const y = new Date(); y.setDate(y.getDate() - 1);
    if (key === today) return "Today";
    if (key === dayKey(y.toISOString())) return "Yesterday";
    const [Y, M, D] = key.split("-").map(Number);
    return new Date(Y, M - 1, D).toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
  }
  function ago(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const m = Math.round((Date.now() - d.getTime()) / 6e4);
    if (m < 1) return "just now";
    if (m < 60) return m + "m ago";
    const h = Math.round(m / 60);
    if (h < 24) return h + "h ago";
    const days = Math.round(h / 24);
    return days === 1 ? "1 day ago" : days + " days ago";
  }
  function fmtMW(mw) {
    if (mw == null) return "";
    return mw >= 1000 ? (mw / 1000).toFixed(mw % 1000 === 0 ? 0 : 1) + " GW" : Math.round(mw) + " MW";
  }
  function fmtMoney(b) {
    if (b == null) return "";
    return b >= 1 ? "$" + (Math.round(b * 10) / 10) + "B" : "$" + Math.round(b * 1000) + "M";
  }
  function debounce(fn, ms) {
    let t;
    return function () { clearTimeout(t); const a = arguments; t = setTimeout(() => fn.apply(this, a), ms); };
  }
  async function loadJSON(path) {
    const r = await fetch(path + "?v=" + Math.floor(Date.now() / 600000));
    if (!r.ok) throw new Error(path + " " + r.status);
    return r.json();
  }
  function store(key, val) {
    try {
      if (val === undefined) return JSON.parse(localStorage.getItem("dcw-" + key));
      localStorage.setItem("dcw-" + key, JSON.stringify(val));
    } catch (e) { return null; }
  }

  // ---------- Reference data ----------
  const STATES = {
    AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California", CO: "Colorado", CT: "Connecticut",
    DE: "Delaware", DC: "District of Columbia", FL: "Florida", GA: "Georgia", HI: "Hawaii", ID: "Idaho", IL: "Illinois",
    IN: "Indiana", IA: "Iowa", KS: "Kansas", KY: "Kentucky", LA: "Louisiana", ME: "Maine", MD: "Maryland",
    MA: "Massachusetts", MI: "Michigan", MN: "Minnesota", MS: "Mississippi", MO: "Missouri", MT: "Montana",
    NE: "Nebraska", NV: "Nevada", NH: "New Hampshire", NJ: "New Jersey", NM: "New Mexico", NY: "New York",
    NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma", OR: "Oregon", PA: "Pennsylvania",
    RI: "Rhode Island", SC: "South Carolina", SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah",
    VT: "Vermont", VA: "Virginia", WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming",
  };
  // Tile-grid cartogram positions [col, row]
  const TILES = {
    AK: [0, 0], ME: [10, 0], VT: [9, 1], NH: [10, 1],
    WA: [0, 2], ID: [1, 2], MT: [2, 2], ND: [3, 2], MN: [4, 2], IL: [5, 2], WI: [6, 2], MI: [7, 2], NY: [8, 2], RI: [9, 2], MA: [10, 2],
    OR: [0, 3], NV: [1, 3], WY: [2, 3], SD: [3, 3], IA: [4, 3], IN: [5, 3], OH: [6, 3], PA: [7, 3], NJ: [8, 3], CT: [9, 3],
    CA: [0, 4], UT: [1, 4], CO: [2, 4], NE: [3, 4], MO: [4, 4], KY: [5, 4], WV: [6, 4], VA: [7, 4], MD: [8, 4], DE: [9, 4],
    AZ: [1, 5], NM: [2, 5], KS: [3, 5], AR: [4, 5], TN: [5, 5], NC: [6, 5], SC: [7, 5], DC: [8, 5],
    OK: [3, 6], LA: [4, 6], MS: [5, 6], AL: [6, 6], GA: [7, 6],
    HI: [0, 7], TX: [3, 7], FL: [8, 7],
  };
  const CATS = {
    "Announcements": { tone: "var(--c-announce)", icon: "spark" },
    "Construction": { tone: "var(--c-construct)", icon: "factory" },
    "Power & Energy": { tone: "var(--c-power)", icon: "zap" },
    "Policy & Community": { tone: "var(--c-policy)", icon: "users" },
    "Deals & Investment": { tone: "var(--c-deals)", icon: "dollar" },
    "AI & Hyperscale": { tone: "var(--c-ai)", icon: "cpu" },
    "General": { tone: "var(--c-general)", icon: "news" },
  };
  const STATUS = {
    "Announced": { tone: "var(--st-announced)", step: 1 },
    "Under construction": { tone: "var(--st-construction)", step: 2 },
    "Operational": { tone: "var(--st-operational)", step: 3 },
  };
  const TYPES = {
    "Hyperscaler": { tone: "#0ea5e9", blurb: "Cloud giants that build and run their own campuses." },
    "AI Lab": { tone: "#8b5cf6", blurb: "Model builders anchoring gigawatt-scale training sites." },
    "GPU Cloud": { tone: "#ec4899", blurb: "Neoclouds renting GPU capacity, often in leased halls." },
    "Developer": { tone: "#f59e0b", blurb: "Build powered shells and campuses to lease to tenants." },
    "Colocation": { tone: "#14b8a6", blurb: "Rent racks, cages and halls to many customers." },
    "Investor": { tone: "#6366f1", blurb: "Capital behind the build-out." },
    "Energy": { tone: "#ca8a04", blurb: "Utilities and power developers supplying campuses." },
    "Hardware": { tone: "#22c55e", blurb: "Chips and systems that set density." },
  };

  // Build a matcher that returns company slugs mentioned in a headline.
  function companyMatcher(companies) {
    const rules = companies.map((c) => ({
      slug: c.slug,
      rx: new RegExp("(^|[^\\w])(" + c.aliases.map((a) => a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")(?![\\w])"),
    }));
    return (text) => rules.filter((r) => r.rx.test(text)).map((r) => r.slug);
  }
  function initials(c) {
    const s = c.short || c.name;
    return s.length <= 4 ? s : s.split(/\s+/).map((w) => w[0]).join("").slice(0, 3).toUpperCase();
  }

  // ---------- Theme ----------
  function currentTheme() {
    const t = document.documentElement.dataset.theme;
    if (t) return t;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function toggleTheme() {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    store("theme", next);
    document.dispatchEvent(new CustomEvent("dcw:theme", { detail: next }));
  }

  // ---------- Chrome ----------
  const NAV = [
    ["index.html", "News", "news"],
    ["projects.html", "Projects map", "map"],
    ["companies.html", "Companies", "building"],
    ["learn.html", "Learn", "learn"],
  ];
  function chrome(active) {
    const h = document.getElementById("site-header");
    if (h) {
      h.className = "site-header";
      h.innerHTML = '<div class="wrap">' +
        '<a class="brand" href="index.html" aria-label="Data Center Watch home">' + logo() + '<span>Data Center Watch<small>U.S. edition</small></span></a>' +
        '<nav class="nav" id="nav">' + NAV.map((n) => '<a href="' + n[0] + '"' + (n[0] === active ? ' class="active" aria-current="page"' : "") + ">" + icon(n[2]) + n[1] + "</a>").join("") + "</nav>" +
        '<div class="header-actions">' +
        '<button class="icon-btn theme-toggle" id="themeBtn" aria-label="Toggle dark mode" title="Toggle theme">' + icon("moon", "moon") + icon("sun", "sun") + "</button>" +
        '<button class="icon-btn menu-btn" id="menuBtn" aria-label="Open menu" aria-expanded="false">' + icon("menu") + "</button>" +
        "</div></div>";
      h.querySelector("#themeBtn").addEventListener("click", toggleTheme);
      const nav = h.querySelector("#nav"), mb = h.querySelector("#menuBtn");
      mb.addEventListener("click", () => { const o = nav.classList.toggle("open"); mb.setAttribute("aria-expanded", o); });
    }
    const f = document.getElementById("site-footer");
    if (f) {
      f.className = "site-footer";
      f.innerHTML = '<div class="wrap">' +
        '<div><div class="footer-brand">' + logo() + 'Data Center Watch</div>' +
        "<p>Tracking America's data center build-out: new announcements, construction, power deals and local decisions. Headlines link to the original publishers and refresh twice a day.</p>" +
        '<p class="muted" style="font-size:12.5px">Categories, places and companies are detected automatically from headlines and can be wrong. Project details come from public reporting and may be out of date.</p></div>' +
        "<div><h4>Explore</h4><ul>" + NAV.map((n) => '<li><a href="' + n[0] + '">' + n[1] + "</a></li>").join("") + "</ul></div>" +
        '<div><h4>Sources</h4><ul><li>Google News RSS (U.S. edition)</li><li>Google Alerts</li><li>Map: U.S. Census boundaries via us-atlas, © OpenStreetMap, © CARTO</li><li>Built with Leaflet</li></ul></div>' +
        "</div>";
    }
    document.querySelectorAll("[data-logo]").forEach((el) => { el.innerHTML = logo(el.dataset.logo); });
  }

  // ---------- Loader ----------
  function ready() {
    const el = document.getElementById("loader");
    const wait = Math.max(0, 750 - (performance.now() - START));
    setTimeout(() => {
      document.body.classList.remove("is-loading");
      if (el) { el.classList.add("done"); setTimeout(() => el.remove(), 600); }
      revealAll();
    }, wait);
  }
  function fail(msg) {
    const el = document.getElementById("loader");
    if (el) el.querySelector(".loader-sub").textContent = msg;
    setTimeout(ready, 1200);
  }

  // ---------- Small UI helpers ----------
  let toastEl, toastT;
  function toast(msg) {
    if (!toastEl) { toastEl = document.createElement("div"); toastEl.className = "toast"; toastEl.setAttribute("role", "status"); document.body.appendChild(toastEl); }
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastT);
    toastT = setTimeout(() => toastEl.classList.remove("show"), 1800);
  }
  let tipEl;
  function tip(html, x, y) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; document.body.appendChild(tipEl); }
    if (html == null) { tipEl.classList.remove("show"); return; }
    tipEl.innerHTML = html;
    tipEl.style.left = x + "px";
    tipEl.style.top = y + "px";
    tipEl.classList.add("show");
  }
  function countUp(el, to, fmt) {
    fmt = fmt || ((v) => Math.round(v).toLocaleString());
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { el.innerHTML = fmt(to); return; }
    const t0 = performance.now(), dur = 900;
    function step(t) {
      const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      el.innerHTML = fmt(to * e);
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  let io;
  function revealAll() {
    const els = document.querySelectorAll(".reveal:not(.in)");
    if (!("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("in")); return; }
    io = io || new IntersectionObserver((ents) => ents.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } }), { rootMargin: "0px 0px -40px 0px" });
    els.forEach((e) => io.observe(e));
  }

  return {
    icon, logo, esc, fmtDate, dayKey, dayLabel, ago, fmtMW, fmtMoney, debounce, loadJSON, store,
    STATES, TILES, CATS, STATUS, TYPES, companyMatcher, initials,
    currentTheme, chrome, ready, fail, toast, tip, countUp, revealAll,
  };
})();
