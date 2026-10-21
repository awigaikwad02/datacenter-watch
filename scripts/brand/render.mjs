// Renders the PNG brand assets from the SVG sources.
// Dev-only helper, not used by the site. Needs Node and Playwright:
//   npm i -g playwright && npx playwright install chromium
//   node scripts/brand/render.mjs            (writes assets/*.png)
//   node scripts/brand/render.mjs --preview DIR  (also writes logo previews)
import { chromium } from "playwright";
import { readFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const read = (p) => readFileSync(join(root, p), "utf8");
const mark = read("assets/mark.svg");
const favicon = read("assets/favicon.svg");
const logo = read("assets/logo.svg");
const FONT = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap">';

const page = (body, w, h, bg = "transparent") =>
  `<!doctype html><html><head>${FONT}<style>html,body{margin:0;width:${w}px;height:${h}px;background:${bg};overflow:hidden}
  body{display:grid;place-items:center;font-family:Inter,sans-serif;color:#E9EEF7}svg{display:block}</style></head><body>${body}</body></html>`;

const sized = (svg, w, h) => svg.replace(/width="\d+" height="\d+"/, `width="${w}" height="${h}"`);

const og = `<div style="position:relative;width:1200px;height:630px;background:radial-gradient(900px 500px at 85% -10%,rgba(56,189,248,.16),transparent 60%),radial-gradient(700px 420px at 0% 110%,rgba(185,245,66,.10),transparent 60%),#070B14;overflow:hidden">
  <div style="position:absolute;inset:0;background-image:linear-gradient(rgba(148,163,184,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,.07) 1px,transparent 1px);background-size:48px 48px"></div>
  <div style="position:absolute;left:96px;top:150px;color:#E9EEF7">${sized(mark, 132, 132)}</div>
  <div style="position:absolute;left:96px;top:318px;font-size:84px;letter-spacing:-2.5px;color:#F4F7FB;font-weight:400">The <b style="font-weight:600">Rack</b> Report</div>
  <div style="position:absolute;left:100px;top:432px;font-size:32px;color:#A9B6C9;letter-spacing:-.3px">The U.S. data center buildout, tracked in one place.</div>
  <div style="position:absolute;left:100px;top:520px;display:flex;gap:12px;align-items:center;font-size:22px;color:#B9F542;font-weight:600"><span style="width:12px;height:12px;border-radius:50%;background:#B9F542;box-shadow:0 0 18px #B9F542"></span>News · Project Atlas · Companies · Learn</div>
</div>`;

const jobs = [
  ["assets/favicon-32.png", page(sized(favicon, 32, 32), 32, 32), 32, 32],
  ["assets/apple-touch-icon.png", page(sized(favicon, 180, 180).replace('rx="11"', 'rx="0"'), 180, 180, "#0A1020"), 180, 180],
  ["assets/og.png", page(og, 1200, 630), 1200, 630],
];
const pi = process.argv.indexOf("--preview");
if (pi > 0) {
  const dir = process.argv[pi + 1];
  mkdirSync(dir, { recursive: true });
  const strip = [24, 64, 240].map((s) => `<div style="padding:12px">${sized(mark, s, s)}</div>`).join("");
  const both = (bg, fg) => `<div style="display:flex;align-items:center;background:${bg};color:${fg};padding:16px">${strip}<div style="padding:12px">${sized(logo, 316, 48)}</div></div>`;
  jobs.push([join(dir, "logo-preview.png"), page(both("#070B14", "#E9EEF7") + both("#ffffff", "#0B1324"), 900, 560, "#333"), 900, 560]);
  jobs.push([join(dir, "favicon-preview.png"), page([16, 24, 32, 64].map((s) => sized(favicon, s, s)).join('<span style="width:16px"></span>'), 220, 80, "#ddd"), 220, 80]);
}

const browser = await chromium.launch();
for (const [out, html, w, h] of jobs) {
  const p = await browser.newPage({ viewport: { width: w, height: h } });
  await p.setContent(html, { waitUntil: "networkidle" });
  await p.screenshot({ path: out.startsWith("/") ? out : join(root, out), omitBackground: out.includes("favicon-32") });
  await p.close();
  console.log("wrote", out);
}
await browser.close();
