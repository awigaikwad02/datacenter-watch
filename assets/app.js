// Shared helpers for Data Center Watch
window.DCW = (function () {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmtDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return "";
    return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" });
  }
  function fmtDateTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return "";
    return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  }
  function dayKey(iso) {
    const d = new Date(iso);
    return isNaN(d) ? "" : d.toISOString().slice(0, 10);
  }
  function ago(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const h = Math.round((Date.now() - d.getTime()) / 36e5);
    if (h < 1) return "just now";
    if (h < 24) return h + "h ago";
    const days = Math.round(h / 24);
    return days === 1 ? "yesterday" : days + " days ago";
  }
  function fmtMW(mw) {
    if (mw == null) return "";
    return mw >= 1000 ? (mw / 1000).toFixed(mw % 1000 === 0 ? 0 : 1) + " GW" : mw + " MW";
  }
  function fmtMoney(b) {
    if (b == null) return "";
    return b >= 1 ? "$" + (Math.round(b * 10) / 10) + "B" : "$" + Math.round(b * 1000) + "M";
  }
  async function loadJSON(path) {
    const r = await fetch(path + "?v=" + Math.floor(Date.now() / 60000));
    if (!r.ok) throw new Error(path + " " + r.status);
    return r.json();
  }
  return { esc, fmtDate, fmtDateTime, dayKey, ago, fmtMW, fmtMoney, loadJSON };
})();
