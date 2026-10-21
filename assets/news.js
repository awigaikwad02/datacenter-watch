// News page: loads data/news.json and renders a filterable feed
(function () {
  const { esc, fmtDate, dayKey, ago, fmtMW, fmtMoney, loadJSON } = window.DCW;
  const CATS = ["Announcements", "Construction", "Power & Energy", "Policy & Community", "Deals & Investment", "AI & Hyperscale", "General"];
  const PAGE = 60;

  const el = {
    updated: document.getElementById("updated"),
    stats: document.getElementById("stats"),
    q: document.getElementById("q"),
    chips: document.getElementById("chips"),
    loc: document.getElementById("loc"),
    range: document.getElementById("range"),
    feed: document.getElementById("feed"),
    empty: document.getElementById("empty"),
    more: document.getElementById("more"),
  };

  let items = [];
  let state = { cat: "", q: "", loc: "", days: 7, shown: PAGE };

  function render() {
    const q = state.q.trim().toLowerCase();
    const cutoff = Date.now() - state.days * 864e5;
    const list = items.filter(it => {
      if (new Date(it.published).getTime() < cutoff) return false;
      if (state.cat && it.category !== state.cat) return false;
      if (state.loc && !(it.locations || []).some(l => l.name === state.loc || l.name.endsWith(state.loc))) return false;
      if (q && !(it.title + " " + it.source + " " + (it.locations || []).map(l => l.name).join(" ")).toLowerCase().includes(q)) return false;
      return true;
    });

    el.feed.innerHTML = "";
    if (!list.length) {
      el.empty.hidden = false;
      el.empty.textContent = items.length
        ? "Nothing matches these filters."
        : "No news yet. The first update runs automatically on the schedule; you can also start it from the Actions tab in GitHub.";
      el.more.hidden = true;
      return;
    }
    el.empty.hidden = true;

    let lastDay = "";
    const frag = document.createDocumentFragment();
    list.slice(0, state.shown).forEach(it => {
      const dk = dayKey(it.published);
      if (dk !== lastDay) {
        const h = document.createElement("div");
        h.className = "day";
        h.textContent = fmtDate(it.published);
        frag.appendChild(h);
        lastDay = dk;
      }
      const div = document.createElement("div");
      div.className = "item";
      // show the most specific place only; the rest still work for filtering
      const locs = (it.locations || []).slice(0, 1).map(l => `<span class="tag loc">${esc(l.name)}</span>`).join("");
      const nums = [it.capacity_mw != null ? fmtMW(it.capacity_mw) : "", it.investment_usd_b != null ? fmtMoney(it.investment_usd_b) : ""]
        .filter(Boolean).map(n => `<span class="num">${esc(n)}</span>`).join("");
      div.innerHTML = `
        <h3><a href="${esc(it.link)}" target="_blank" rel="noopener">${esc(it.title)}</a></h3>
        <div class="sub">
          ${it.source ? `<span>${esc(it.source)}</span>` : ""}
          <span>${esc(ago(it.published))}</span>
          <span class="tag">${esc(it.category)}</span>
          ${locs}${nums}
        </div>`;
      frag.appendChild(div);
    });
    el.feed.appendChild(frag);
    el.more.hidden = list.length <= state.shown;
  }

  function buildChips() {
    const counts = {};
    items.forEach(it => { counts[it.category] = (counts[it.category] || 0) + 1; });
    const all = document.createElement("button");
    all.className = "chip on"; all.dataset.cat = ""; all.innerHTML = `All <small>${items.length}</small>`;
    el.chips.appendChild(all);
    CATS.filter(c => counts[c]).forEach(c => {
      const b = document.createElement("button");
      b.className = "chip"; b.dataset.cat = c; b.innerHTML = `${esc(c)} <small>${counts[c]}</small>`;
      el.chips.appendChild(b);
    });
    el.chips.addEventListener("click", e => {
      const b = e.target.closest(".chip"); if (!b) return;
      el.chips.querySelectorAll(".chip").forEach(x => x.classList.toggle("on", x === b));
      state.cat = b.dataset.cat; state.shown = PAGE; render();
    });
  }

  function buildLocations() {
    const counts = {};
    items.forEach(it => (it.locations || []).forEach(l => { counts[l.name] = (counts[l.name] || 0) + 1; }));
    Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 80).forEach(([name, n]) => {
      const o = document.createElement("option");
      o.value = name; o.textContent = `${name} (${n})`;
      el.loc.appendChild(o);
    });
  }

  function buildStats() {
    if (!items.length) return;
    const week = Date.now() - 7 * 864e5;
    const recent = items.filter(it => new Date(it.published).getTime() >= week);
    const ann = recent.filter(it => it.category === "Announcements" || it.category === "Construction").length;
    const mw = recent.reduce((s, it) => s + (it.capacity_mw || 0), 0);
    const stateCounts = {};
    recent.forEach(it => (it.locations || []).forEach(l => {
      const parts = l.name.split(", ");
      const key = parts.length >= 2 ? parts[parts.length - 2] : parts[0];
      stateCounts[key] = (stateCounts[key] || 0) + 1;
    }));
    const top = Object.entries(stateCounts).sort((a, b) => b[1] - a[1])[0];
    el.stats.innerHTML = `
      <div class="stat"><b>${recent.length}</b><span>headlines, last 7 days</span></div>
      <div class="stat"><b>${ann}</b><span>announcements and builds</span></div>
      <div class="stat"><b>${mw ? fmtMW(mw) : "–"}</b><span>capacity mentioned this week</span></div>
      <div class="stat"><b>${top ? esc(top[0]) : "–"}</b><span>most mentioned place</span></div>`;
    el.stats.hidden = false;
  }

  el.q.addEventListener("input", () => { state.q = el.q.value; state.shown = PAGE; render(); });
  el.loc.addEventListener("change", () => { state.loc = el.loc.value; state.shown = PAGE; render(); });
  el.range.addEventListener("change", () => { state.days = +el.range.value; state.shown = PAGE; render(); });
  el.more.addEventListener("click", () => { state.shown += PAGE; render(); });

  loadJSON("data/news.json").then(d => {
    items = (d.items || []).slice().sort((a, b) => new Date(b.published) - new Date(a.published));
    el.updated.textContent = d.updated ? `Updated ${ago(d.updated)} (${fmtDate(d.updated)}). ${items.length} headlines in the last 60 days.` : "Not updated yet.";
    buildChips(); buildLocations(); buildStats(); render();
  }).catch(err => {
    el.updated.textContent = "Could not load news data.";
    el.empty.hidden = false; el.empty.textContent = String(err);
  });
})();
