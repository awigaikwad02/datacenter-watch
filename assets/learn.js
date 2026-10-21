// Learn page: course outline and progress, quizzes, and the interactive tools inside each lesson.
(function () {
  const D = DCW, $ = (s) => document.querySelector(s);
  const LEVELS = {
    1: { name: "Foundations", tone: "var(--st-operational)", blurb: "What a data center is, what's inside, and the units of scale." },
    2: { name: "Core systems", tone: "var(--accent)", blurb: "Power, cooling, racks, networking and redundancy." },
    3: { name: "Advanced", tone: "var(--accent-2)", blurb: "Efficiency, AI clusters, the grid, building one, and policy." },
  };
  const HOME_KWH = 10800; // average U.S. household use per year
  const fmt = (n, d) => Number(n).toLocaleString(undefined, { maximumFractionDigits: d || 0 });

  D.chrome("learn.html");

  // ---------- Course outline and progress ----------
  const lessons = [...document.querySelectorAll("article.lesson")];
  let done = new Set(D.store("learn-done") || []);

  lessons.forEach((a, i) => {
    const lv = LEVELS[a.dataset.level];
    const inLevel = lessons.filter((x) => x.dataset.level === a.dataset.level);
    const head = document.createElement("div");
    head.className = "lesson-head";
    head.innerHTML = '<span class="pill" style="--tone:' + lv.tone + '"><span class="dot"></span>' + lv.name + " · Lesson " + (inLevel.indexOf(a) + 1) + " of " + inLevel.length + "</span><span>" + D.icon("calendar") + " " + a.dataset.mins + " min read</span>";
    a.prepend(head);
    const next = lessons[i + 1];
    const foot = document.createElement("div");
    foot.className = "lesson-foot";
    foot.innerHTML = '<button class="btn" data-done="' + a.id + '">' + D.icon("check") + "<span>Mark complete</span></button>" +
      (next ? '<a class="btn primary" href="#' + next.id + '" data-advance="' + a.id + '">Next: ' + D.esc(next.querySelector("h2").textContent) + " " + D.icon("arrow") + "</a>"
        : '<a class="btn primary" href="#glossary" data-advance="' + a.id + '">Finish: glossary ' + D.icon("arrow") + "</a>");
    a.appendChild(foot);
  });

  function renderOutline() {
    $("#outline").innerHTML = Object.entries(LEVELS).map(([k, lv]) =>
      '<div class="level-block" style="--tone:' + lv.tone + '"><div class="lvl"><i></i>Level ' + k + " · " + lv.name + "</div>" +
      lessons.filter((a) => a.dataset.level === k).map((a) =>
        '<a class="lesson-link' + (done.has(a.id) ? " done" : "") + '" href="#' + a.id + '" data-id="' + a.id + '"><span class="ck"><span>' + (lessons.indexOf(a) + 1) + "</span></span>" + D.esc(a.querySelector("h2").textContent) + "</a>").join("") + "</div>").join("") +
      '<div class="level-block"><a class="lesson-link" href="#glossary"><span class="ck">' + D.icon("list") + "</span>Glossary</a></div>";
    $("#levelCards").innerHTML = Object.entries(LEVELS).map(([k, lv]) => {
      const ls = lessons.filter((a) => a.dataset.level === k), n = ls.filter((a) => done.has(a.id)).length;
      const mins = ls.reduce((s, a) => s + Number(a.dataset.mins), 0);
      return '<a class="level-card" href="#' + ls[0].id + '" style="--tone:' + lv.tone + '"><div class="lvl">Level ' + k + "</div><b>" + lv.name + "</b><span>" + lv.blurb + "</span>" +
        '<div style="display:flex;justify-content:space-between;font-size:12px;color:var(--faint);margin-top:10px"><span>' + ls.length + " lessons · " + mins + " min</span><span>" + n + "/" + ls.length + "</span></div>" +
        '<div class="lbar"><i style="width:' + (n / ls.length) * 100 + '%"></i></div></a>';
    }).join("");
    const pct = Math.round((done.size / lessons.length) * 100);
    $("#ringFg").style.strokeDashoffset = 163.4 * (1 - pct / 100);
    $("#ringText").textContent = pct + "%";
    $("#progTitle").textContent = pct === 100 ? "Course complete 🎉" : done.size ? "Keep going" : "Start learning";
    $("#progSub").textContent = done.size + " of " + lessons.length + " lessons complete";
    document.querySelectorAll("[data-done]").forEach((b) => {
      const on = done.has(b.dataset.done);
      b.classList.toggle("done-on", on);
      b.querySelector("span").textContent = on ? "Completed" : "Mark complete";
    });
    markCurrent();
  }
  function setDone(id, on) {
    if (on) done.add(id); else done.delete(id);
    D.store("learn-done", [...done]);
    renderOutline();
  }
  let current = null;
  function markCurrent() {
    document.querySelectorAll(".lesson-link").forEach((l) => l.classList.toggle("current", l.dataset.id === current));
  }
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((ents) => {
      ents.forEach((e) => { if (e.isIntersecting) { current = e.target.id; markCurrent(); } });
    }, { rootMargin: "-30% 0px -60% 0px" });
    lessons.forEach((a) => io.observe(a));
  }

  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-done]");
    if (b) { const id = b.dataset.done; setDone(id, !done.has(id)); if (done.has(id)) D.toast("Lesson complete"); return; }
    const adv = e.target.closest("[data-advance]");
    if (adv && !done.has(adv.dataset.advance)) setDone(adv.dataset.advance, true);
  });
  $("#resetProg").addEventListener("click", () => {
    if (!confirm("Reset your course progress?")) return;
    done = new Set(); D.store("learn-done", []);
    document.querySelectorAll(".quiz").forEach(resetQuiz);
    renderOutline();
  });

  // ---------- Quizzes ----------
  function resetQuiz(q) {
    q.querySelectorAll(".opt").forEach((o) => { o.disabled = false; o.classList.remove("right", "wrong"); });
    const w = q.querySelector(".why"); if (w) w.remove();
  }
  document.querySelectorAll(".quiz").forEach((q) => {
    q.querySelector("b").insertAdjacentHTML("afterbegin", D.icon("spark"));
    q.querySelectorAll(".opt").forEach((o, i) => o.addEventListener("click", () => {
      const right = i === Number(q.dataset.answer);
      q.querySelectorAll(".opt").forEach((x, j) => { x.disabled = true; if (j === Number(q.dataset.answer)) x.classList.add("right"); });
      if (!right) o.classList.add("wrong");
      const w = document.createElement("div");
      w.className = "why";
      w.innerHTML = "<b>" + (right ? "Correct. " : "Not quite. ") + "</b>" + D.esc(q.dataset.why) + ' <button class="link-btn" type="button">Try again</button>';
      w.querySelector("button").addEventListener("click", () => resetQuiz(q));
      q.appendChild(w);
    }));
  });
  document.querySelectorAll(".takeaways b").forEach((b) => b.insertAdjacentHTML("afterbegin", D.icon("check")));

  // ---------- Lesson 2: cutaway ----------
  const ZONES = {
    substation: ["Substation", "Where high-voltage power from the grid is stepped down for the campus. Large campuses often get a dedicated substation, which can take years to permit and build."],
    generators: ["Generators", "Rows of diesel or natural gas generators that start within seconds of a grid outage, with fuel stored on site for a day or more. They are tested regularly, which neighbors can hear."],
    security: ["Security & loading dock", "Mantraps, badge readers, cameras and guards control who gets in. Equipment arrives through a secure loading dock and staging area."],
    electrical: ["Electrical room", "Switchgear routes power; the UPS (uninterruptible power supply) and its batteries bridge the seconds between a grid failure and generators taking over."],
    hall: ["Data hall", "The reason the building exists. Rows of racks full of servers, storage and network switches, arranged so cold air goes in the front and hot air comes out the back."],
    mmr: ["Meet-me room", "Where fiber from internet carriers and customers meets and is cross-connected. It is why some buildings in Ashburn, Virginia are among the most connected places on Earth."],
    noc: ["Network operations center", "Staff monitor power, cooling, security and network alarms 24 hours a day, often with remote sites watched from here too."],
    cooling: ["Cooling plant", "Chillers, pumps and heat exchangers that carry heat away from the data hall. Liquid-cooled AI halls add coolant distribution units close to the racks."],
    roof: ["Rooftop heat rejection", "Cooling towers, dry coolers or condensers that dump the heat into the outside air. Evaporative towers use water; dry coolers use more electricity instead."],
    fiber: ["Fiber entrances", "At least two separate underground routes bring fiber into the building, so one accidental cut can't take the site offline."],
  };
  const cut = $("#cutaway");
  function showZone(z) {
    cut.querySelectorAll(".zone").forEach((g) => g.classList.toggle("on", g.dataset.z === z));
    $("#cutawayInfo").innerHTML = "<b>" + ZONES[z][0] + ".</b> " + ZONES[z][1];
  }
  cut.querySelectorAll(".zone").forEach((g) => {
    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    g.setAttribute("aria-label", ZONES[g.dataset.z][0]);
    g.addEventListener("mouseenter", () => showZone(g.dataset.z));
    g.addEventListener("click", () => showZone(g.dataset.z));
    g.addEventListener("focus", () => showZone(g.dataset.z));
  });
  showZone("hall");

  // ---------- Lesson 4: scale ----------
  const scMW = $("#scMW");
  const sliderToMW = (v) => Math.round(Math.pow(10, 0 + (v / 100) * 3.7)); // 1 MW to ~5 GW, log scale
  const mwToSlider = (mw) => (Math.log10(mw) / 3.7) * 100;
  function scaleUpdate(mw) {
    $("#scMWv").textContent = D.fmtMW(mw);
    const mwh = mw * 8760;
    const cells = [
      ["Homes' worth of electricity", fmt((mwh * 1000) / HOME_KWH)],
      ["Energy per year if run flat out", mwh >= 1e6 ? fmt(mwh / 1e6, 1) + " TWh" : fmt(mwh / 1000, 0) + " GWh"],
      ["Traditional racks at 10 kW", fmt((mw * 1000) / 10)],
      ["AI racks at 130 kW", fmt((mw * 1000) / 130)],
    ];
    $("#scOut").innerHTML = cells.map((c) => "<div><span>" + c[0] + "</span><b>" + c[1] + "</b></div>").join("");
  }
  scMW.addEventListener("input", () => scaleUpdate(sliderToMW(scMW.value)));
  document.querySelectorAll("[data-mw]").forEach((b) => b.addEventListener("click", () => { const mw = Number(b.dataset.mw); scMW.value = mwToSlider(mw); scaleUpdate(mw); }));
  scMW.value = mwToSlider(100); scaleUpdate(100);

  // ---------- Lesson 5: power chain ----------
  const CHAIN = [
    ["tower", "Grid", "High-voltage transmission lines bring power from power plants, often at 138 kV to 500 kV. Big campuses want two separate feeds."],
    ["factory", "Substation", "Transformers step the voltage down to medium voltage for the campus. A 1 GW campus may need several large transformers, which have long manufacturing lead times."],
    ["switchI", "Switchgear", "Heavy-duty breakers and the automatic transfer switch route power and can flip the load to generators when the grid fails."],
    ["battery", "UPS", "The uninterruptible power supply conditions the power and keeps batteries charged. If the input drops, the batteries take over with no gap at all."],
    ["box", "PDU", "Power distribution units step power down to rack voltage and split it into many circuits for the data hall."],
    ["plug", "Rack PDU", "The power strips in each rack. Two of them, A and B, are fed from separate upstream paths."],
    ["server", "Server", "Power supplies in each server convert AC to the low DC voltages that chips use. Almost all of it ends up as heat."],
  ];
  const OUTAGE = [
    [0, "Normal operation", "Grid power flows through the whole chain. UPS batteries sit fully charged."],
    [3, "0 s · Grid fails", "A storm knocks out the utility feed. The UPS batteries take over instantly; the servers see no interruption."],
    [2, "~10 s · Generators start", "The generators start and come up to speed. The automatic transfer switch moves the load onto generator power."],
    [3, "~1 min · Running on generators", "Generators carry the whole site and the UPS recharges its batteries. Fuel on site lasts a day or more, with refueling contracts after that."],
    [0, "Grid restored", "When utility power is stable again, the switch transfers back and the generators cool down. Nobody online noticed a thing."],
  ];
  let ci = 0, outage = null, outT;
  function renderChain() {
    $("#chain").innerHTML = CHAIN.map((c, i) => '<button data-ci="' + i + '" class="' + (i === ci ? "on" : "") + (i < ci ? " passed" : "") + '" aria-label="' + c[1] + '"><span class="node">' + D.icon(c[0]) + "</span>" + c[1] + "</button>").join("");
    if (outage == null) $("#chainInfo").innerHTML = "<b>" + (ci + 1) + ". " + CHAIN[ci][1] + "</b>" + CHAIN[ci][2];
  }
  $("#chain").addEventListener("click", (e) => { const b = e.target.closest("[data-ci]"); if (b) { stopOutage(); ci = Number(b.dataset.ci); renderChain(); } });
  $("#chainPrev").addEventListener("click", () => { stopOutage(); ci = Math.max(0, ci - 1); renderChain(); });
  $("#chainNext").addEventListener("click", () => { stopOutage(); ci = Math.min(CHAIN.length - 1, ci + 1); renderChain(); });
  function stopOutage() { clearTimeout(outT); outage = null; $("#outageBtn").textContent = "Simulate a utility outage"; }
  function outageStep() {
    const s = OUTAGE[outage];
    ci = s[0];
    renderChain();
    $("#chainInfo").innerHTML = "<b>" + s[1] + "</b>" + s[2];
    $("#chain").querySelectorAll("button").forEach((b, i) => {
      if (outage === 1 || outage === 2) b.classList.toggle("passed", i >= 3), b.classList.toggle("on", i === s[0]);
      if (outage >= 1 && outage <= 3 && i < 2) b.style.opacity = ".35"; else b.style.opacity = "";
    });
    outage++;
    if (outage < OUTAGE.length) outT = setTimeout(outageStep, 2600);
    else { outage = null; $("#outageBtn").textContent = "Run it again"; }
  }
  $("#outageBtn").addEventListener("click", () => { clearTimeout(outT); outage = 0; $("#outageBtn").textContent = "Simulating…"; outageStep(); });
  renderChain();

  // ---------- Lesson 6: density ----------
  const dn = $("#dn");
  function density() {
    const kw = Number(dn.value);
    $("#dnV").textContent = kw + " kW";
    $("#dnNeedle").style.left = "calc(" + ((kw - 2) / 198) * 100 + "% - 1.5px)";
    let v;
    if (kw <= 25) v = ["Air cooling", "Typical for web servers, storage and enterprise IT. Raised floors or overhead ducts with cold and hot aisles are enough. The U.S. average rack is in this range."];
    else if (kw <= 50) v = ["Air with containment or rear-door coolers", "Dense CPU or early GPU racks. Hot-aisle containment and rear-door heat exchangers (radiators on the back of the rack) stretch air cooling further."];
    else if (kw <= 150) v = ["Direct-to-chip liquid cooling", "Rack-scale AI systems. Coolant runs through cold plates on GPUs and CPUs; air still handles the leftover heat from memory, drives and power supplies."];
    else v = ["Immersion or advanced liquid", "Extreme density. Servers sit in tanks of dielectric fluid, or next-generation racks use full liquid designs. Still a small share of deployments."];
    $("#dnVerdict").innerHTML = "<b>" + v[0] + ".</b> " + v[1] + " At " + kw + " kW, one rack uses about as much power as " + fmt((kw * 8760) / HOME_KWH) + " homes.";
  }
  dn.addEventListener("input", density);
  density();

  // ---------- Lesson 7: rack diagram ----------
  (function rack() {
    const svg = $("#rackSvg"), x = 280, w = 200, top = 24, u = 8.2;
    const units = [
      [1, "sw", "Top-of-rack switch"], [1, "pp", "Patch panel"], [1, "blank"],
      [1, "srv"], [1, "srv"], [1, "srv"], [1, "srv"], [2, "srv2", "1U and 2U servers"], [2, "srv2"],
      [1, "blank", "Blanking panel"], [6, "gpu", "GPU server (8 GPUs)"], [6, "gpu"],
      [1, "blank"], [2, "sto", "Storage shelf"], [2, "sto"], [2, "sto"], [1, "blank"], [2, "srv2"], [2, "srv2"], [2, "blank"],
    ];
    let h = '<rect x="' + (x - 14) + '" y="' + (top - 10) + '" width="' + (w + 28) + '" height="' + (42 * u + 20) + '" rx="8" class="bx"/>';
    h += '<rect x="' + (x - 10) + '" y="' + top + '" width="6" height="' + 42 * u + '" rx="2" style="fill:var(--c-power);opacity:.8"/><rect x="' + (x + w + 4) + '" y="' + top + '" width="6" height="' + 42 * u + '" rx="2" style="fill:var(--c-power);opacity:.8"/>';
    let y = top;
    const labels = [];
    units.forEach(([n, kind, label]) => {
      const hh = n * u - 1.2;
      const cls = { sw: "acc", pp: "bx", blank: "bx2", srv: "srv", srv2: "srv", gpu: "gpu", sto: "srv" }[kind];
      h += '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + hh + '" rx="2" class="' + cls + '"/>';
      if (kind === "srv" || kind === "srv2" || kind === "sw") h += '<circle cx="' + (x + w - 10) + '" cy="' + (y + hh / 2) + '" r="1.8" class="ledg"/>';
      if (kind === "gpu") for (let i = 0; i < 8; i++) h += '<rect x="' + (x + 12 + i * 23) + '" y="' + (y + 10) + '" width="17" height="' + (hh - 20) + '" rx="2" style="fill:var(--accent-2);opacity:.35"/>';
      if (kind === "sto") for (let i = 0; i < 12; i++) h += '<rect x="' + (x + 8 + i * 15.5) + '" y="' + (y + 3) + '" width="12" height="' + (hh - 6) + '" rx="1" style="fill:var(--surface);opacity:.8"/>';
      if (label) labels.push([y + hh / 2, label]);
      y += n * u;
    });
    labels.forEach(([ly, t], i) => {
      const right = i % 2 === 0, lx = right ? x + w + 40 : x - 40;
      h += '<path d="M' + (right ? x + w + 12 : x - 12) + " " + ly + " H" + lx + '" class="ln"/>';
      h += '<text x="' + (right ? lx + 6 : lx - 6) + '" y="' + (ly + 4) + '" text-anchor="' + (right ? "start" : "end") + '" class="t">' + t + "</text>";
    });
    h += '<text x="' + (x + w + 40) + '" y="' + (top + 42 * u - 2) + '" class="s">Rack PDUs (A and B) run down both sides</text>';
    h += '<text x="' + (x - 40) + '" y="' + (top + 42 * u - 2) + '" text-anchor="end" class="s">42U ≈ 6 feet of mounting space</text>';
    svg.innerHTML = h;
  })();

  // ---------- Lesson 8: network diagram ----------
  (function net() {
    const svg = $("#netSvg");
    let h = "";
    const box = (x, y, w, hh, t, s, cls) => '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + hh + '" rx="8" class="' + (cls || "bx") + '"/><text x="' + (x + w / 2) + '" y="' + (y + hh / 2 + (s ? -2 : 4)) + '" text-anchor="middle" class="t">' + t + "</text>" + (s ? '<text x="' + (x + w / 2) + '" y="' + (y + hh / 2 + 13) + '" text-anchor="middle" class="s">' + s + "</text>" : "");
    const spines = [150, 300, 450, 600].map((cx) => [cx, 130]);
    const leaves = [90, 206, 322, 438, 554, 670].map((cx) => [cx, 220]);
    spines.forEach(([sx, sy]) => leaves.forEach(([lx, ly]) => { h += '<path d="M' + sx + " " + (sy + 16) + " L" + lx + " " + (ly - 14) + '" class="ln" style="opacity:.45"/>'; }));
    h += '<path d="M380 60 L150 114 M380 60 L300 114 M380 60 L450 114 M380 60 L600 114" class="ln"/>';
    h += '<path d="M206 236 V266 M206 206 L300 146 M300 114 L380 60" class="ln-acc flow"/>';
    h += box(265, 12, 230, 48, "Core routers + meet-me room", "carriers · internet", "acc");
    spines.forEach(([x, y], i) => { h += box(x - 50, y - 16, 100, 32, "Spine " + (i + 1)); });
    leaves.forEach(([x, y], i) => { h += box(x - 46, y - 14, 92, 28, "Leaf " + (i + 1)); });
    leaves.forEach(([x]) => { h += '<path d="M' + x + " 234 V266" + '" class="ln"/>'; for (let r = 0; r < 3; r++) h += '<rect x="' + (x - 40 + r * 28) + '" y="266" width="22" height="48" rx="3" class="srv"/>'; });
    h += '<text x="20" y="134" class="s">Spine layer</text><text x="380" y="326" text-anchor="middle" class="s">Racks (each leaf is a top-of-rack switch)</text>';
    svg.innerHTML = h;
  })();

  // ---------- Lesson 9: redundancy ----------
  let redMode = "N+1", failed = new Set();
  function redRender() {
    document.querySelectorAll("#redMode button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.m === redMode));
    const paths = redMode === "2N" ? [["A", 3], ["B", 3]] : [["", redMode === "N" ? 3 : 4]];
    $("#redUnits").innerHTML = paths.map(([p, n]) => '<div class="path-row">' + (p ? "<span>Path " + p + "</span>" : "") + '<div class="units">' +
      Array.from({ length: n }, (_, i) => {
        const id = p + i, f = failed.has(id), spare = redMode === "N+1" && i === 3;
        return '<button class="unit' + (f ? " failed" : "") + (spare ? " spare" : "") + '" data-u="' + id + '" aria-pressed="' + f + '" aria-label="Unit ' + (i + 1) + (p ? " path " + p : "") + (f ? " failed" : " running") + '">' + D.icon(f ? "x" : "fan") + (spare ? "spare" : f ? "failed" : "ok") + "</button>";
      }).join("") + "</div></div>").join("");
    let ok, msg;
    if (redMode === "2N") {
      const a = [0, 1, 2].every((i) => !failed.has("A" + i)), b = [0, 1, 2].every((i) => !failed.has("B" + i));
      ok = a || b;
      msg = ok ? (a && b ? "Load is up on both paths. An entire path can fail and nothing goes down." : "Load is up: path " + (a ? "A" : "B") + " is carrying everything.") : "Outage. Both paths have lost a unit, so neither can carry the full load.";
    } else {
      const healthy = (redMode === "N" ? 3 : 4) - failed.size;
      ok = healthy >= 3;
      msg = ok ? (healthy > 3 ? "Load is up with one spare in reserve." : redMode === "N" ? "Load is up, but with zero margin. Any failure or maintenance means an outage." : "Load is up, but the spare is in use. One more failure means an outage.") : "Outage. Only " + healthy + " of the 3 required units are running.";
    }
    const st = $("#redStatus");
    st.className = "load-status " + (ok ? "ok" : "bad");
    st.innerHTML = D.icon(ok ? "check" : "alert") + msg;
  }
  $("#redMode").addEventListener("click", (e) => { const b = e.target.closest("[data-m]"); if (b) { redMode = b.dataset.m; failed.clear(); redRender(); } });
  $("#redUnits").addEventListener("click", (e) => { const b = e.target.closest("[data-u]"); if (b) { const id = b.dataset.u; failed.has(id) ? failed.delete(id) : failed.add(id); redRender(); } });
  redRender();

  // ---------- Lesson 10: PUE ----------
  function pue() {
    const it = Number($("#peIT").value), p = Number($("#pePUE").value), wue = Number($("#peWUE").value);
    $("#peITv").textContent = D.fmtMW(it);
    $("#pePUEv").textContent = p.toFixed(2);
    $("#peWUEv").textContent = wue.toFixed(2);
    const total = it * p, over = total - it, gwh = (total * 8760) / 1000;
    const waterGal = (it * 1000 * 8760 * wue) / 3.785; // liters to gallons
    const ms = $("#peMeter").children;
    ms[0].style.width = (it / total) * 100 + "%";
    ms[1].style.width = (over / total) * 100 + "%";
    const cells = [
      ["Total facility power", D.fmtMW(total)],
      ["Overhead (cooling, losses)", D.fmtMW(over)],
      ["Energy per year", fmt(gwh) + " GWh"],
      ["Homes' worth of electricity", fmt((gwh * 1e6) / HOME_KWH)],
      ["Water consumed per year", waterGal >= 1e9 ? fmt(waterGal / 1e9, 2) + " billion gal" : fmt(waterGal / 1e6, 0) + " million gal"],
      ["Rating", p <= 1.2 ? "Best in class" : p <= 1.4 ? "Efficient" : p <= 1.6 ? "Industry average" : "Older or inefficient"],
    ];
    $("#peOut").innerHTML = cells.map((c) => "<div><span>" + c[0] + "</span><b>" + c[1] + "</b></div>").join("");
  }
  ["#peIT", "#pePUE", "#peWUE"].forEach((id) => $(id).addEventListener("input", pue));
  pue();

  // ---------- Lesson 11: AI cluster ----------
  const gpusFromSlider = (v) => Math.round(Math.pow(10, 3 + (v / 100) * 3) / 1000) * 1000; // 1k to 1M
  function ai() {
    const n = gpusFromSlider($("#aiN").value);
    const [kw, perRack] = $("#aiGen").value.split("|").map(Number);
    const p = Number($("#aiP").value);
    $("#aiNv").textContent = fmt(n);
    $("#aiPv").textContent = p.toFixed(2);
    const itMW = (n * kw) / 1000, fac = itMW * p;
    const cells = [
      ["IT power", D.fmtMW(itMW)],
      ["At the meter (with PUE)", D.fmtMW(fac)],
      ["Racks", fmt(Math.ceil(n / perRack))],
      ["Per-rack power", fmt(kw * perRack) + " kW"],
      ["Homes' worth of electricity", fmt((fac * 8760 * 1000) / HOME_KWH)],
      ["Scale", fac < 50 ? "One data hall" : fac < 300 ? "A large building or small campus" : fac < 1500 ? "A hyperscale AI campus" : "Multi-gigawatt mega-campus"],
    ];
    $("#aiOut").innerHTML = cells.map((c) => "<div><span>" + c[0] + "</span><b>" + c[1] + "</b></div>").join("");
  }
  ["#aiN", "#aiGen", "#aiP"].forEach((id) => $(id).addEventListener("input", ai));
  ai();

  // ---------- Lesson 13: timeline ----------
  const TL = [
    ["Site search & land", 0, 12, "var(--st-operational)"],
    ["Power & interconnection", 3, 36, "var(--c-power)"],
    ["Zoning & permits", 6, 15, "var(--c-policy)"],
    ["Design", 8, 10, "var(--accent-2)"],
    ["Construction", 18, 20, "var(--c-construct)"],
    ["Commissioning", 36, 4, "var(--accent)"],
    ["Operations", 40, 20, "var(--st-operational)"],
  ];
  const MAX = 60;
  $("#timeline").innerHTML = TL.map(([name, s, d, tone]) =>
    '<div class="tl-row"><span>' + name + '</span><div class="tl-track"><i style="--tone:' + tone + ";left:" + (s / MAX) * 100 + "%;width:" + (Math.min(d, MAX - s) / MAX) * 100 + '%">' + (name === "Operations" ? "15–20+ years" : "~" + d + " mo") + "</i></div></div>").join("") +
    '<div class="tl-row"><span></span><div style="display:flex;justify-content:space-between;font-size:11px;color:var(--faint);font-family:var(--font-mono)">' + [0, 12, 24, 36, 48, 60].map((m) => "<span>" + (m ? "yr " + m / 12 : "start") + "</span>").join("") + "</div></div>";

  // ---------- Glossary ----------
  const GLOSSARY = [
    ["Behind-the-meter", "Power generated on site and used directly, without passing through the utility grid."],
    ["Campus", "Several data center buildings on one site sharing power and fiber infrastructure."],
    ["Colocation", "A facility that rents space, power and cooling to many customers."],
    ["CRAH / CRAC", "Computer room air handler or air conditioner: the units that cool and circulate air in a data hall."],
    ["Cross-connect", "A direct cable between two customers' equipment in the same building, usually in the meet-me room."],
    ["Direct-to-chip cooling", "Liquid coolant piped through cold plates mounted on processors."],
    ["Edge data center", "A small facility close to users to reduce delay."],
    ["ERCOT", "Electric Reliability Council of Texas, which runs most of the Texas grid."],
    ["GPU", "Graphics processing unit; the chip that powers most AI training and inference."],
    ["Hot / cold aisle", "Alternating rows where racks face each other so cold intake air and hot exhaust stay separate."],
    ["Hyperscaler", "A cloud company operating at huge scale, such as AWS, Microsoft, Google, Meta or Oracle."],
    ["Immersion cooling", "Submerging servers in a non-conductive liquid that absorbs heat."],
    ["Inference", "Running a trained AI model to answer requests."],
    ["Interconnection queue", "The line of projects waiting for a grid operator to study and approve their connection."],
    ["kW / MW / GW", "Units of power: 1 GW = 1,000 MW = 1,000,000 kW."],
    ["Meet-me room", "The room where carriers and customers interconnect their networks."],
    ["Moratorium", "A temporary pause on new approvals while a government studies impacts or writes rules."],
    ["N, N+1, 2N", "Redundancy levels: exactly enough, one spare, or two full independent systems."],
    ["PDU", "Power distribution unit: distributes power to racks; a rack PDU is the power strip inside the rack."],
    ["PJM", "The grid operator for 13 Mid-Atlantic and Midwest states plus D.C., including Northern Virginia."],
    ["Powered shell", "A building with power and fiber delivered but without the tenant's IT fit-out."],
    ["PPA", "Power purchase agreement: a long-term contract to buy electricity from a specific source."],
    ["PUE", "Power usage effectiveness: total facility power divided by IT power."],
    ["Rack unit (U)", "Standard height unit for rack equipment: 1.75 inches."],
    ["SMR", "Small modular reactor: a compact nuclear reactor design that some data center operators have signed deals for."],
    ["Spine-leaf", "A network design where every leaf switch connects to every spine switch."],
    ["Substation", "A facility that transforms high-voltage grid power to lower voltages."],
    ["Tier I–IV", "Uptime Institute's ratings for data center redundancy and maintainability."],
    ["Training", "Building an AI model by processing huge datasets on large GPU clusters."],
    ["UPS", "Uninterruptible power supply: batteries and electronics that bridge power interruptions."],
    ["WUE", "Water usage effectiveness: liters of water consumed per kWh of IT energy."],
    ["Wholesale data center", "A building or campus leased in large blocks to one or a few big tenants."],
  ];
  function glossary() {
    const q = $("#glq").value.trim().toLowerCase();
    const list = GLOSSARY.filter((g) => !q || (g[0] + " " + g[1]).toLowerCase().includes(q));
    $("#glossaryGrid").innerHTML = list.length ? list.map((g) => '<div class="gl"><b>' + g[0] + "</b><span>" + g[1] + "</span></div>").join("") : '<p class="muted">No terms match.</p>';
  }
  $("#glq").addEventListener("input", glossary);
  glossary();

  renderOutline();
  D.ready();
})();
