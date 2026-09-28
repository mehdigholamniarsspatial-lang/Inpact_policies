/* Shared helpers: glossary, colours, tooltips, formatting, Plotly defaults. */
(function () {
  const G = JSON.parse(document.getElementById("glossary-data").textContent);
  const App = (window.App = { G });

  App.YEARS = Array.from({ length: 24 }, (_, i) => 2000 + i);
  App.sectorColor = (s) => (G.sectors[s] || {}).color || "#8C969C";
  App.mechColor = (m) => (G.mechanisms[m] || {}).color || "#8C969C";
  App.mechLabel = (m) => (G.mechanisms[m] || {}).label || App.humanise(m);
  App.layerLabel = (l) => (G.layers[l] || {}).label || App.humanise(l);
  App.statusLabel = (s) => (G.status[s] || {}).label || App.humanise(s);
  App.humanise = (c) => { if (!c) return ""; const t = String(c).replace(/_/g, " ").trim(); return t.charAt(0).toUpperCase() + t.slice(1); };
  App.fmt = (v, d = 2) => (v === null || v === undefined || Number.isNaN(v) ? "\u2013" : Number(v).toFixed(d));
  App.fmtInt = (v) => (v === null || v === undefined ? "\u2013" : Math.round(v).toLocaleString("en-IE"));
  App.esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  App.policyUrl = (slug) => window.URLS.policyBase + slug + "/";

  /* Mix a hex colour towards white; t=0 white, t=1 full colour. */
  App.tint = (hex, t) => {
    const n = parseInt(hex.slice(1), 16);
    const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    const k = Math.max(0, Math.min(1, t));
    const mix = (c) => Math.round(255 + (c - 255) * k);
    return `rgb(${mix(r)},${mix(g)},${mix(b)})`;
  };

  /* Cached JSON fetch */
  const cache = {};
  App.getJSON = (url) => (cache[url] = cache[url] || fetch(url).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }));

  /* Tooltip */
  const tip = document.getElementById("tip");
  App.showTip = (html, evt) => {
    tip.innerHTML = html; tip.hidden = false;
    App.moveTip(evt);
  };
  App.moveTip = (evt) => {
    if (!evt || tip.hidden) return;
    const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + w > window.innerWidth - 8) x = evt.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = evt.clientY - h - pad;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  };
  App.hideTip = () => { tip.hidden = true; };

  /* Glossary terms: <span class="term" data-term="mechanisms.pricing">...</span> */
  App.termHtml = (key) => {
    const [group, code] = key.split(".");
    const entry = (G[group] || {})[code];
    if (!entry) return null;
    return `<strong>${App.esc(entry.label || App.humanise(code))}</strong>${App.esc(entry.desc)}`;
  };
  document.addEventListener("mouseover", (e) => {
    const t = e.target.closest("[data-term],[data-tip]");
    if (!t) return;
    const html = t.dataset.term ? App.termHtml(t.dataset.term) : App.esc(t.dataset.tip);
    if (html) App.showTip(html, e);
  });
  document.addEventListener("mousemove", (e) => { if (e.target.closest("[data-term],[data-tip]")) App.moveTip(e); });
  document.addEventListener("mouseout", (e) => { if (e.target.closest("[data-term],[data-tip]")) App.hideTip(); });
  document.addEventListener("focusin", (e) => {
    const t = e.target.closest("[data-term]");
    if (t) { const r = t.getBoundingClientRect(); App.showTip(App.termHtml(t.dataset.term), { clientX: r.left, clientY: r.bottom }); }
  });
  document.addEventListener("focusout", App.hideTip);

  /* Segmented control helper */
  App.seg = (el, onChange) => {
    el.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-value]");
      if (!b) return;
      el.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
      onChange(b.dataset.value);
    });
    const cur = el.querySelector('button[aria-pressed="true"]');
    return cur ? cur.dataset.value : null;
  };

  /* Chip toggle group; returns a getter for the active set */
  App.chipGroup = (el, items, onChange) => {
    el.innerHTML = items.map((it) => `<button type="button" class="chip" aria-pressed="true" data-value="${App.esc(it.value)}"${it.term ? ` data-term="${it.term}"` : ""}><span class="dot" style="background:${it.color}"></span>${App.esc(it.label)}</button>`).join("");
    const active = new Set(items.map((i) => i.value));
    el.addEventListener("click", (e) => {
      const b = e.target.closest(".chip");
      if (!b) return;
      const v = b.dataset.value;
      if (e.altKey || e.metaKey) { // solo mode
        active.clear(); active.add(v);
      } else if (active.has(v)) active.delete(v); else active.add(v);
      el.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", active.has(c.dataset.value) ? "true" : "false"));
      onChange(active);
    });
    return {
      active,
      set(values) {
        active.clear(); values.forEach((v) => active.add(v));
        el.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", active.has(c.dataset.value) ? "true" : "false"));
      },
    };
  };

  /* Tiny inline sparkline (SVG string) */
  App.spark = (values, color, w = 120, h = 26, max = 1) => {
    const n = values.length, step = w / (n - 1);
    let d = "", area = "";
    values.forEach((v, i) => {
      const x = i * step, y = v === null ? null : h - 2 - (Math.min(v, max) / max) * (h - 4);
      if (y === null) return;
      d += (d ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1);
    });
    if (d) area = d + `L${w},${h}L0,${h}Z`;
    return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><path d="${area}" fill="${color}" opacity=".14"/><path d="${d}" fill="none" stroke="${color}" stroke-width="1.6"/></svg>`;
  };

  /* Plotly defaults */
  App.plotLayout = (extra = {}) => Object.assign({
    font: { family: "Public Sans, system-ui, sans-serif", size: 12, color: "#15252D" },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 52, r: 16, t: 16, b: 40 },
    hoverlabel: { bgcolor: "#15252D", bordercolor: "#15252D", font: { color: "#fff", family: "Public Sans, sans-serif", size: 12 } },
    xaxis: { gridcolor: "#E4EAE9", linecolor: "#D3DCDB", zeroline: false },
    yaxis: { gridcolor: "#E4EAE9", linecolor: "#D3DCDB", zeroline: false },
    legend: { orientation: "h", y: -0.14, yanchor: "top", font: { size: 12 } },
  }, extra);
  App.plotConfig = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"] };
})();
