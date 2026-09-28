(function () {
  const $ = (id) => document.getElementById(id);
  const DOMAINS = ["Cross-sector or international", "Electricity", "Buildings", "Industry", "Transport", "Other"];
  const YEARS = Array.from({ length: 34 }, (_, i) => 1990 + i);
  const PALETTE = ["#0B5563", "#C4841D", "#7B4F96", "#3D944B", "#B0503A", "#2F68A8", "#8B5A38", "#C0567A"];
  let L3 = [], L4 = [], ALL = {}, SLUG = {}, show = "all", picked = [];

  Promise.all([App.getJSON(window.URLS.capmf + "?level=3"), App.getJSON(window.URLS.capmf + "?level=4"), App.getJSON(window.URLS.series)]).then(([a, b, s]) => {
    L3 = a.categories; L4 = b.categories;
    [...L3, ...L4].forEach((c) => (ALL[c.code] = c));
    s.series.forEach((x) => { if (!SLUG[x.id]) SLUG[x.id] = { slug: x.slug, name: x.name }; });
    const q = new URLSearchParams(location.search).getAll("code").filter((c) => ALL[c]);
    picked = q.length ? q : ["LEV3_ETS_E", "LEV3_CARBONTAX_B", "LEV3_BC", "LEV3_NZ"];
    drawHeat(); drawLines(); drawElig(); info(ALL[picked[0]]);
  });
  App.seg($("show"), (v) => { show = v; drawHeat(); });

  const valAt = (c, y) => { const i = c.years.indexOf(y); return i < 0 ? null : c.values[i]; };
  const used = (c) => c.linked.length > 0 || (c.representedBy && c.eligible);

  /* ---------------------------------------------------------- heatmap */
  function drawHeat() {
    let rows = L3.filter((c) => show === "all" || (show === "used" ? used(c) : c.firstPositive));
    rows.sort((a, b) => DOMAINS.indexOf(a.domain) - DOMAINS.indexOf(b.domain) || a.label.localeCompare(b.label));
    rows = rows.reverse(); // Plotly draws the first row at the bottom
    const y = rows.map((c) => (used(c) ? "● " : "") + (c.label.length > 48 ? c.label.slice(0, 46) + "…" : c.label) + "  ");
    const z = rows.map((c) => YEARS.map((yr) => valAt(c, yr)));
    const text = rows.map((c) => YEARS.map((yr) => {
      const i = c.years.indexOf(yr), st = i < 0 ? "" : c.status[i];
      return `<b>${c.label}</b><br>${c.domain}<br>${yr}: ${valAt(c, yr) === null ? "missing (" + st + ")" : valAt(c, yr).toFixed(2) + " / 10"}${st === "E" ? " (estimated)" : ""}`;
    }));
    const H = Math.max(260, rows.length * 19 + 70);
    $("heat").style.height = H + "px";
    // domain separators
    const shapes = [{ type: "rect", xref: "x", yref: "paper", x0: 1999.5, x1: 2023.5, y0: 0, y1: 1, line: { color: "#C4841D", width: 1.2 }, fillcolor: "rgba(0,0,0,0)" }];
    const annotations = [];
    let prev = null;
    rows.forEach((c, i) => {
      if (c.domain !== prev) {
        if (prev !== null) shapes.push({ type: "line", xref: "paper", x0: -0.5, x1: 1, y0: i - 0.5, y1: i - 0.5, line: { color: "#15252D", width: 1 } });
        prev = c.domain;
      }
    });
    DOMAINS.forEach((d) => {
      const idx = rows.map((c, i) => (c.domain === d ? i : -1)).filter((i) => i >= 0);
      if (idx.length) annotations.push({ xref: "paper", x: 1.005, y: (idx[0] + idx[idx.length - 1]) / 2, xanchor: "left", showarrow: false, text: d.replace("Cross-sector or international", "Cross-sector /<br>international"), font: { size: 11, color: "#4B5C65" }, align: "left" });
    });
    Plotly.react("heat", [{
      type: "heatmap", x: YEARS, y: y.map((l, i) => l + "\u200b".repeat(i)), z, text, hovertemplate: "%{text}<extra></extra>", zmin: 0, zmax: 10, xgap: 1, ygap: 1,
      colorscale: [[0, "#F2F5F4"], [0.001, "#E3EEEE"], [0.3, "#9CC3C8"], [0.65, "#2F7F8C"], [1, "#0B3F4A"]],
      colorbar: { title: { text: "0–10", side: "top" }, thickness: 10, len: 0.5, x: 1.13, y: 1, yanchor: "top" },
      customdata: rows.map((c) => YEARS.map(() => c.code)),
    }], App.plotLayout({
      margin: { l: 300, r: 150, t: 10, b: 30 }, shapes, annotations,
      xaxis: { dtick: 5, side: "bottom", gridcolor: "rgba(0,0,0,0)" }, yaxis: { automargin: false, tickfont: { size: 11 }, gridcolor: "rgba(0,0,0,0)" },
    }), App.plotConfig);
    const el = $("heat");
    if (!el._bound) {
      el.on("plotly_click", (ev) => { const code = ev.points[0].customdata; if (!picked.includes(code)) picked.push(code); drawLines(); info(ALL[code]); });
      el._bound = true;
    }
  }

  /* ---------------------------------------------------------- lines + picker */
  function drawLines() {
    $("picked").innerHTML = picked.map((c, i) => `<button class="chip" type="button" data-code="${c}" aria-label="Remove ${App.esc(ALL[c].label)}"><span class="dot" style="background:${PALETTE[i % PALETTE.length]}"></span>${App.esc(ALL[c].label)} <span class="x">×</span></button>`).join("");
    const traces = picked.map((code, i) => {
      const c = ALL[code];
      return { type: "scatter", mode: "lines", name: c.label, x: c.years, y: c.values, customdata: c.years.map(() => code), connectgaps: false,
        line: { color: PALETTE[i % PALETTE.length], width: 2.2, shape: "hv", dash: code.startsWith("LEV4") ? "dot" : "solid" }, hovertemplate: `${c.label}: %{y:.2f}<extra></extra>` };
    });
    Plotly.react("lines", traces, App.plotLayout({
      hovermode: "x unified", margin: { l: 40, r: 10, t: 10, b: 30 }, showlegend: false,
      yaxis: { range: [0, 10.4], title: { text: "Stringency 0–10" }, gridcolor: "#E4EAE9" }, xaxis: { gridcolor: "#E4EAE9" },
      shapes: [{ type: "rect", xref: "x", yref: "paper", x0: 1990, x1: 2000, y0: 0, y1: 1, fillcolor: "rgba(0,0,0,.035)", line: { width: 0 } }],
      annotations: [{ x: 1995, y: 1, yref: "paper", text: "before dataset window", showarrow: false, font: { size: 10, color: "#7A8990" }, yanchor: "top" }],
    }), App.plotConfig);
    const el = $("lines");
    if (!el._bound) { el.on("plotly_click", (ev) => info(ALL[ev.points[0].customdata])); el._bound = true; }
  }
  $("picked").addEventListener("click", (e) => {
    const b = e.target.closest(".chip"); if (!b) return;
    picked = picked.filter((c) => c !== b.dataset.code); drawLines();
  });

  const input = $("pick"), list = $("pick-list");
  let hits = [], sel = 0;
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { list.hidden = true; input.setAttribute("aria-expanded", "false"); return; }
    hits = Object.values(ALL).filter((c) => (c.label + " " + c.code).toLowerCase().includes(q)).slice(0, 14);
    sel = 0; renderHits();
  });
  function renderHits() {
    list.innerHTML = hits.length ? hits.map((c, i) => `<li role="option" data-code="${c.code}" aria-selected="${i === sel}">${App.esc(c.label)}<small>${c.code.startsWith("LEV4") ? "indicator" : "category"}</small></li>`).join("") : '<li class="muted">No matching category</li>';
    list.hidden = false; input.setAttribute("aria-expanded", "true");
  }
  function choose(code) { if (code && !picked.includes(code)) picked.push(code); input.value = ""; list.hidden = true; drawLines(); info(ALL[code]); }
  list.addEventListener("mousedown", (e) => { const li = e.target.closest("li[data-code]"); if (li) { e.preventDefault(); choose(li.dataset.code); } });
  input.addEventListener("keydown", (e) => {
    if (list.hidden) return;
    if (e.key === "ArrowDown") { sel = Math.min(hits.length - 1, sel + 1); renderHits(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); renderHits(); e.preventDefault(); }
    else if (e.key === "Enter") { if (hits[sel]) choose(hits[sel].code); e.preventDefault(); }
    else if (e.key === "Escape") list.hidden = true;
  });
  input.addEventListener("blur", () => setTimeout(() => (list.hidden = true), 150));

  /* ---------------------------------------------------------- details */
  function repLinks(c) {
    const ids = (c.representedBy || "").split(";").filter(Boolean);
    return ids.map((id) => (SLUG[id] ? `<a href="${App.policyUrl(SLUG[id].slug)}">${App.esc(SLUG[id].name)}</a>` : App.esc(App.humanise(id)))).join(", ");
  }
  function info(c) {
    if (!c) return;
    const vals = c.values.filter((v) => v !== null);
    const v2023 = valAt(c, 2023);
    const linked = c.linked.map((l) => `<li><a href="${App.policyUrl(l.slug)}">${App.esc(l.name)}</a> <span class="muted">${App.esc(l.sector)}</span></li>`).join("");
    const decision = c.eligible === null ? "" : c.eligible ? `<p class="small"><b>Eligible.</b> Represented by ${repLinks(c) || "EEA finance programmes"}.</p>` : `<p class="small"><b>Not used.</b> ${App.esc(c.exclusion)}</p>`;
    $("cat-info").innerHTML = `<p class="small muted" style="margin:0"><code>${c.code}</code></p><h3>${App.esc(c.label)}</h3>
      <p class="small muted">${App.esc(c.domain)}${c.cls ? ", " + App.esc(c.cls) : ""}</p>
      ${App.spark(c.values, "#0B5563", 300, 60, 10)}
      <dl class="kv"><dt>Score in 2023</dt><dd>${v2023 === null ? "missing" : v2023.toFixed(2) + " / 10"}</dd>
        <dt>Range</dt><dd>${vals.length ? Math.min(...vals).toFixed(2) + " to " + Math.max(...vals).toFixed(2) : "no values"}</dd>
        ${c.firstPositive ? `<dt>First positive</dt><dd>${c.firstPositive}</dd>` : ""}</dl>
      ${decision}
      ${linked ? `<h4 style="margin:10px 0 4px;font-size:13px">Directly matched policies</h4><ul class="small" style="padding-left:18px">${linked}</ul>` : ""}`;
  }

  function drawElig() {
    const rows = L3.filter((c) => c.eligible !== null).sort((a, b) => (b.eligible - a.eligible) || DOMAINS.indexOf(a.domain) - DOMAINS.indexOf(b.domain));
    $("elig").tBodies[0].innerHTML = rows.map((c) => `<tr><td><a href="#" data-code="${c.code}">${App.esc(c.label)}</a><div class="small muted">${c.code}</div></td><td>${App.esc(c.domain)}</td><td>${c.firstPositive || "–"}</td>
      <td>${c.eligible ? '<span class="pass">Eligible</span>' : '<span class="muted">Excluded</span>'}</td><td class="small">${c.eligible ? repLinks(c) || "EEA finance programmes" : App.esc(c.exclusion)}</td></tr>`).join("");
    $("elig").addEventListener("click", (e) => {
      const a = e.target.closest("a[data-code]"); if (!a) return; e.preventDefault();
      if (!picked.includes(a.dataset.code)) picked.push(a.dataset.code);
      drawLines(); info(ALL[a.dataset.code]); $("lines").scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }
})();
