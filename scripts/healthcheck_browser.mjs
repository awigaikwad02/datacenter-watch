#!/usr/bin/env node
// Browser health check for The Rack Report (Playwright + axe-core).
//
//   npm install --no-save playwright @axe-core/playwright && npx playwright install chromium
//   node scripts/healthcheck_browser.mjs
//
// Serves the repo the way GitHub Pages does (/newsroom -> newsroom.html, unknown paths -> 404.html),
// then loads the six pages plus a missing path at 390px and 1280px. Checks console errors, CSP
// violations, failed requests, rendered links, sitemap entries, the freshness badge, the Overview
// "announced" number, the Atlas map and axe-core (serious and critical issues). Results are merged
// into data/health.json; exits 1 on any failure. Run scripts/healthcheck.py first.
//
// Offline use (no CDN access): RR_VENDOR_DIR=<dir with leaflet/ and leaflet.markercluster/ packages>
// serves Leaflet locally, and map tiles and web fonts are stubbed.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PAGES = ["/", "/newsroom", "/atlas", "/companies", "/learn", "/methodology"];
const MISSING = "/this-page-does-not-exist";
const WIDTHS = [390, 1280];
const VENDOR = process.env.RR_VENDOR_DIR;
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "application/javascript", ".css": "text/css", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".xml": "application/xml", ".txt": "text/plain" };

const checks = [];
const check = (name, ok, value = "", detail = "") => checks.push({ name: "Browser: " + name, status: ok ? "pass" : "fail", value: String(value), detail: String(detail) });

// ---------- A static server that behaves like GitHub Pages ----------
function serve() {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split("?")[0].split("#")[0]);
    let file = path.join(ROOT, url === "/" ? "index.html" : url);
    if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = fs.existsSync(file + ".html") ? file + ".html" : null;
    if (!file) { res.writeHead(404, { "content-type": TYPES[".html"] }).end(fs.readFileSync(path.join(ROOT, "404.html"))); return; }
    res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" }).end(fs.readFileSync(file));
  });
  return new Promise((ok) => server.listen(0, "127.0.0.1", () => ok(server)));
}

async function offline(ctx) {
  if (!VENDOR) return;
  await ctx.route(/unpkg\.com\/(leaflet(?:\.markercluster)?)@[\d.]+\/(.*)$/, (route) => {
    const m = route.request().url().match(/unpkg\.com\/(leaflet(?:\.markercluster)?)@[\d.]+\/(.*)$/);
    const f = path.join(VENDOR, m[1], m[2]);
    route.fulfill({ status: 200, body: fs.readFileSync(f), headers: { "content-type": f.endsWith(".css") ? "text/css" : "application/javascript", "access-control-allow-origin": "*" } });
  });
  const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
  await ctx.route(/tile\.openstreetmap\.org/, (r) => r.fulfill({ status: 200, body: png, headers: { "content-type": "image/png" } }));
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.fulfill({ status: 200, body: "", headers: { "content-type": "text/css" } }));
}

function sitemap() {
  const xml = fs.readFileSync(path.join(ROOT, "sitemap.xml"), "utf8");
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]).pathname);
}

async function main() {
  const server = await serve();
  const base = "http://127.0.0.1:" + server.address().port;
  const browser = await chromium.launch();
  const links = new Map();
  const a11y = [];
  const news = JSON.parse(fs.readFileSync(path.join(ROOT, "data/news.json"), "utf8"));

  for (const width of WIDTHS) {
    for (const page of [...PAGES, MISSING]) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 } });
      await offline(ctx);
      const p = await ctx.newPage();
      const errors = [], failed = [];
      await p.addInitScript(() => {
        window.__csp = [];
        document.addEventListener("securitypolicyviolation", (e) => window.__csp.push(e.violatedDirective + " " + e.blockedURI));
        try { sessionStorage.setItem("rr-intro", "1"); } catch (e) { /* storage blocked */ }
      });
      p.on("pageerror", (e) => errors.push("pageerror: " + e.message));
      p.on("console", (m) => {
        if (m.type() !== "error") return;
        // The missing-path test asks for a 404 on purpose; the browser logs that response.
        if (page === MISSING && /404/.test(m.text()) && (m.location().url || "").endsWith(MISSING)) return;
        errors.push("console: " + m.text());
      });
      p.on("response", (r) => {
        if (r.status() >= 400 && r.url().startsWith(base) && !r.url().endsWith(MISSING)) failed.push(r.status() + " " + r.url().replace(base, ""));
      });
      await p.goto(base + page, { waitUntil: "load" });
      await p.waitForTimeout(page === "/atlas" || page === "/" ? 2500 : 1500);
      const csp = await p.evaluate(() => window.__csp);
      const label = `${page === MISSING ? "404 page" : page} @${width}px`;
      check(`${label} loads cleanly`, !errors.length && !csp.length && !failed.length,
        `${errors.length} console errors, ${csp.length} CSP violations, ${failed.length} failed requests`, [...errors, ...csp, ...failed].slice(0, 3).join(" | "));
      // In-page anchors ("#main") are not links to check.
      for (const href of await p.$$eval("a[href]:not([href^='#'])", (as) => as.map((a) => a.href))) {
        if (href.startsWith(base)) links.set(href.replace(base, "").split("#")[0] || "/", label);
      }
      if (width === 1280 || page === "/") {
        const res = await new AxeBuilder({ page: p }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
        for (const v of res.violations.filter((v) => v.impact === "serious" || v.impact === "critical")) {
          a11y.push(`${label}: ${v.id} (${v.impact}, ${v.nodes.length}x) ${v.nodes[0]?.target?.join(" ") || ""}`);
        }
      }
      if (page === "/newsroom" && width === 1280) {
        const badge = await p.evaluate((u) => ({ text: document.getElementById("livePill").textContent, want: "Updated " + RR.ago(u) }), news.updated);
        check("Freshness badge shows news.json time", badge.text === badge.want, badge.text, `expected "${badge.want}"`);
      }
      if (page === "/" && width === 1280) {
        const shown = await p.evaluate(() => {
          const tile = [...document.querySelectorAll(".stat")].find((s) => /Projects announced this month/.test(s.textContent));
          return tile ? Number(tile.querySelector(".stat-value").dataset.v) : null;
        });
        let expected = null;
        try { expected = Number(JSON.parse(fs.readFileSync(path.join(ROOT, "data/health.json"), "utf8")).checks.find((c) => /excludes Cancelled/.test(c.name)).value); } catch (e) { /* not run yet */ }
        check("Overview 'announced' matches recomputed value", expected !== null && shown === expected, shown, `Python recomputed ${expected} (Cancelled / Blocked excluded)`);
      }
      if (page === "/atlas" && width === 1280) await atlas(p, base);
      await ctx.close();
    }
  }

  // Rendered links: every same-origin link resolves, is clean and is a sitemap page.
  const sm = sitemap();
  const bad = [];
  for (const [href, from] of links) {
    const r = await fetch(base + href);
    if (r.status !== 200) bad.push(`${href} -> ${r.status} (on ${from})`);
    if (href.includes(".html")) bad.push(`${href} uses .html`);
    if (!href.startsWith("/assets/") && !sm.includes(href)) bad.push(`${href} not in sitemap`);
  }
  check("Rendered internal links resolve, clean, in sitemap", !bad.length, `${links.size} links`, bad.slice(0, 5).join("; "));
  const smBad = [];
  for (const u of sm) { const r = await fetch(base + u); if (r.status !== 200) smBad.push(`${u} -> ${r.status}`); }
  check("Sitemap entries return 200", !smBad.length, `${sm.length} entries`, smBad.join("; "));
  check("No serious or critical accessibility issues (axe)", !a11y.length, `${a11y.length} issues`, a11y.slice(0, 6).join(" | "));

  await browser.close();
  server.close();
  return report();
}

async function atlas(p, base) {
  const pins = await p.$$eval(".leaflet-marker-icon", (e) => e.length);
  const atCountry = await p.$$eval(".cluster .apx, .bubble", (e) => e.length);
  await p.click(".leaflet-control-zoom-in"); await p.waitForTimeout(500);
  await p.click(".leaflet-control-zoom-in"); await p.waitForTimeout(900);
  const bubbles = await p.$$eval(".bubble", (e) => e.length);
  check("Atlas renders pins and state bubbles", pins > 0 && bubbles > 0, `${pins} markers, ${bubbles} bubbles (zoom 5+), ${atCountry} approx counts at country zoom`);
  // Click into clusters until a single pin is visible, then click it.
  let opened = false;
  for (let i = 0; i < 6 && !opened; i++) {
    const pin = await p.$(".leaflet-marker-icon .pin-rack, .leaflet-marker-icon .pin-auto");
    if (pin) { await pin.click({ force: true }); await p.waitForTimeout(1200); opened = await p.$eval("#detail", (d) => d.classList.contains("open")); break; }
    const cl = await p.$(".leaflet-marker-icon .cluster");
    if (!cl) break;
    await cl.click({ force: true }); await p.waitForTimeout(900);
  }
  check("Atlas pin click opens the panel", opened, opened ? await p.$eval("#detailTitle", (e) => e.textContent) : "no panel");
  const before = await p.textContent("#listCount");
  const st = await p.$$eval("#state option", (o) => (o[1] ? o[1].value : ""));
  await p.selectOption("#state", st); await p.waitForTimeout(600);
  const after = await p.textContent("#listCount");
  check("Atlas filters change the list", before !== after, `${before} -> ${after} (state ${st})`);
  const proj = JSON.parse(fs.readFileSync(path.join(ROOT, "data/projects.json"), "utf8")).projects[0];
  await p.goto(base + "/atlas#project=" + encodeURIComponent(proj.id)); await p.waitForTimeout(2200);
  const title = await p.$eval("#detailTitle", (e) => e.textContent).catch(() => "");
  check("Atlas deep link opens the project", title === proj.name, `#project=${proj.id} -> ${title || "no panel"}`);
}

function report() {
  const file = path.join(ROOT, "data/health.json");
  let doc = { checks: [] };
  try { doc = JSON.parse(fs.readFileSync(file, "utf8")); } catch (e) { /* first run */ }
  doc.checks = doc.checks.filter((c) => !c.name.startsWith("Browser: ")).concat(checks);
  doc.browser_checked_at = new Date().toISOString().replace(/\.\d+Z$/, "+00:00");
  doc.checked_at = doc.checked_at || doc.browser_checked_at;
  doc.overall = doc.checks.some((c) => c.status === "fail") ? "fail" : "pass";
  fs.writeFileSync(file, JSON.stringify(doc, null, 1) + "\n");
  const w = Math.max(...checks.map((c) => c.name.length));
  for (const c of checks) console.log(c.name.padEnd(w) + "  " + c.status.toUpperCase().padEnd(6) + "  " + c.value + (c.status === "fail" && c.detail ? "  (" + c.detail + ")" : ""));
  const failing = checks.filter((c) => c.status === "fail").length;
  console.log(`\nBrowser checks: ${failing ? "FAIL" : "PASS"} (${failing} failing)`);
  return failing ? 1 : 0;
}

main().then((code) => process.exit(code), (e) => { console.error(e); process.exit(1); });
