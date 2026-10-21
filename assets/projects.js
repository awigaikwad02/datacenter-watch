// Projects page: Leaflet map + list from data/projects.json (curated) and data/project_candidates.json (auto)
(function () {
  const { esc, fmtDate, ago, fmtMW, fmtMoney, loadJSON } = window.DCW;
  const el = {
    updated: document.getElementById("updated"),
    counts: document.getElementById("counts"),
    q: document.getElementById("q"),
    status: document.getElementById("status"),
    kind: document.getElementById("kind"),
    list: document.getElementById("list"),
    empty: document.getElementById("empty"),
  };

  const hasMap = typeof L !== "undefined";
  let map = null, layer = null;
  if (hasMap) {
    map = L.map("map", { scrollWheelZoom: false }).setView([38, -96], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    layer = L.layerGroup().addTo(map);
  } else {
    document.getElementById("map").innerHTML = '<p class="empty">The map library could not load (no internet access to unpkg.com). The project list below still works.</p>';
  }

  let all = [];
  let markers = new Map();
  const state = { q: "", status: "", kind: "" };

  function statusWeight(s) { return s === "Operational" ? 2 : s === "Under construction" ? 1 : 0; }

  function popupHtml(p) {
    const bits = [];
    if (p.company) bits.push(esc(p.company));
    if (p.capacity_mw) bits.push(fmtMW(p.capacity_mw));
    if (p.investment_usd_b) bits.push(fmtMoney(p.investment_usd_b));
    const link = p.source_url ? `<br><a href="${esc(p.source_url)}" target="_blank" rel="noopener">${p.kind === "auto" ? "Read the story" : "Source"}</a>` : "";
    return `<b>${esc(p.name)}</b>${esc(p.location || "")}<br><span class="meta">${esc(p.status)}${bits.length ? " · " + bits.join(" · ") : ""}</span>${link}`;
  }

  function filtered() {
    const q = state.q.trim().toLowerCase();
    return all.filter(p => {
      if (state.status && p.status !== state.status) return false;
      if (state.kind && p.kind !== state.kind) return false;
      if (q && !(p.name + " " + (p.company || "") + " " + (p.location || "")).toLowerCase().includes(q)) return false;
      return true;
    });
  }

  function render() {
    const list = filtered();
    markers = new Map();
    if (hasMap) {
      layer.clearLayers();
      const pts = [];
      list.forEach(p => {
        const m = L.circleMarker([p.lat, p.lon], {
          radius: p.kind === "curated" ? 8 : 6,
          color: "#1f3a93", weight: 2,
          fillColor: p.kind === "curated" ? "#1f3a93" : "#fff",
          fillOpacity: p.kind === "curated" ? 0.9 : 1,
        }).bindPopup(popupHtml(p));
        m.addTo(layer); markers.set(p.id, m); pts.push([p.lat, p.lon]);
      });
      if (pts.length) map.fitBounds(L.latLngBounds(pts), { padding: [24, 24], maxZoom: 6 });
    }

    el.list.innerHTML = "";
    el.empty.hidden = list.length > 0;
    if (!list.length) { el.empty.textContent = all.length ? "Nothing matches these filters." : "No projects yet."; return; }
    el.counts.textContent = `${list.length} shown`;

    const frag = document.createDocumentFragment();
    list.forEach(p => {
      const div = document.createElement("div");
      div.className = "proj"; div.dataset.id = p.id;
      const bits = [];
      if (p.company) bits.push(`<span>${esc(p.company)}</span>`);
      if (p.location) bits.push(`<span class="tag loc">${esc(p.location)}</span>`);
      bits.push(`<span class="status">${esc(p.status)}</span>`);
      if (p.capacity_mw) bits.push(`<span class="num">${esc(fmtMW(p.capacity_mw))}</span>`);
      if (p.investment_usd_b) bits.push(`<span class="num">${esc(fmtMoney(p.investment_usd_b))}</span>`);
      if (p.kind === "auto") bits.push(`<span>${esc(p.source || "")} · ${esc(ago(p.published))}</span>`);
      else if (p.announced) bits.push(`<span>Announced ${esc(p.announced)}</span>`);
      const title = p.source_url ? `<a href="${esc(p.source_url)}" target="_blank" rel="noopener">${esc(p.name)}</a>` : esc(p.name);
      div.innerHTML = `<h3>${title}</h3><div class="sub">${bits.join("")}</div>${p.notes ? `<p class="notes">${esc(p.notes)}</p>` : ""}`;
      div.addEventListener("click", e => {
        if (e.target.closest("a")) return;
        const m = markers.get(p.id); if (!m) return;
        map.setView(m.getLatLng(), Math.max(map.getZoom(), 7), { animate: true });
        m.openPopup();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      frag.appendChild(div);
    });
    el.list.appendChild(frag);
  }

  el.q.addEventListener("input", () => { state.q = el.q.value; render(); });
  el.status.addEventListener("change", () => { state.status = el.status.value; render(); });
  el.kind.addEventListener("change", () => { state.kind = el.kind.value; render(); });

  Promise.all([
    loadJSON("data/projects.json").catch(() => ({ projects: [] })),
    loadJSON("data/project_candidates.json").catch(() => ({ projects: [] })),
  ]).then(([cur, auto]) => {
    const curated = (cur.projects || []).filter(p => p.lat != null && p.lon != null).map((p, i) => ({ ...p, id: "c" + i, kind: "curated" }));
    const detected = (auto.projects || []).filter(p => p.lat != null && p.lon != null).map(p => ({ ...p, kind: "auto" }));
    // curated first by stage, then detected newest first
    curated.sort((a, b) => statusWeight(a.status) - statusWeight(b.status) || (b.announced || "").localeCompare(a.announced || ""));
    detected.sort((a, b) => new Date(b.published) - new Date(a.published));
    all = curated.concat(detected);
    el.updated.textContent = `${curated.length} curated projects, ${detected.length} detected from news` +
      (auto.updated ? ` (news scan ${ago(auto.updated)}, ${fmtDate(auto.updated)})` : "") + ".";
    render();
  });
})();
