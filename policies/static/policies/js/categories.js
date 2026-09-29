(function () {
  const { G } = App;
  const $ = (id) => document.getElementById(id);
  let DATA = [], hier = "sector", chartType = "sunburst";

  App.seg($("hier"), (v) => { hier = v; drawSun(); });
  App.seg($("chart-type"), (v) => { chartType = v; drawSun(); });
  App.seg($("guide-toggle"), (v) => { $("guide-mech").hidden = v !== "mech"; $("guide-sector").hidden = v !== "sector"; });

  const fontSize = App.textSizer($("font-size"), { key: "categories", sizes: [10, 12, 14, 16, 18, 20], start: 12 },
    () => { if (DATA.length) drawSun(); });

  const DIM = {
    sector: { key: (s) => s.sector, label: (k) => k, color: App.sectorColor, term: (k) => `sectors.${k}`, order: G.sectorOrder },
    mechanism: { key: (s) => s.mechanism, label: App.mechLabel, color: App.mechColor, term: (k) => `mechanisms.${k}`, order: G.mechanismOrder },
    layer: { key: (s) => s.layer, label: App.layerLabel, color: () => "#0B5563", term: (k) => `layers.${k}`, order: G.layerOrder },
    source: { key: (s) => s.source, label: (k) => (G.sources[k] || {}).label || k, color: (k) => ({ "EEA": "#2F68A8", "CAPMF": "#0E7C74", "EEA+CAPMF": "#46507A" }[k]), term: (k) => `sources.${k}`, order: ["EEA+CAPMF", "EEA", "CAPMF"] },
    match: { key: (s) => s.match, label: (k) => (G.match[k] || {}).label || k, color: (k) => ({ exact: "#0B5563", close: "#3D8C99", partial: "#9CC3C8", none: "#C9D2D1" }[k]), term: (k) => `match.${k}`, order: ["exact", "close", "partial", "none"] },
  };
  const PAIRS = { sector: ["sector", "mechanism"], mechanism: ["mechanism", "sector"], layer: ["layer", "mechanism"], source: ["source", "match"] };

  App.getJSON(window.URLS.series).then((d) => {
    DATA = d.series;
    drawSun();
    drawScatter();
    setupFormula();
  });

  /* ---------------------------------------------------------- sunburst */
  function drawSun() {
    const [a, b] = PAIRS[hier].map((k) => DIM[k]);
    const ids = [], labels = [], parents = [], values = [], colors = [], custom = [];
    const lvl1 = d3.group(DATA, a.key);
    [...lvl1.keys()].sort((x, y) => a.order.indexOf(x) - a.order.indexOf(y)).forEach((k1) => {
      const rows1 = lvl1.get(k1);
      ids.push(k1); labels.push(a.label(k1)); parents.push(""); values.push(rows1.length); colors.push(a.color(k1)); custom.push(a.term(k1));
      const lvl2 = d3.group(rows1, b.key);
      [...lvl2.keys()].sort((x, y) => b.order.indexOf(x) - b.order.indexOf(y)).forEach((k2) => {
        const rows2 = lvl2.get(k2), id2 = `${k1}/${k2}`;
        ids.push(id2); labels.push(b.label(k2)); parents.push(k1); values.push(rows2.length);
        colors.push(App.tint(b.color(k2), 0.82)); custom.push(b.term(k2));
        rows2.forEach((s) => {
          ids.push(`${id2}/${s.slug}`); labels.push(s.name.length > 34 ? s.name.slice(0, 32) + "…" : s.name);
          parents.push(id2); values.push(1); colors.push(App.tint(b.color(k2), 0.45)); custom.push("leaf:" + s.slug);
        });
      });
    });
    const trace = {
      type: chartType, ids, labels, parents, values, branchvalues: "total", customdata: custom,
      marker: { colors, line: { color: "#fff", width: 1.2 } },
      hovertemplate: "<b>%{label}</b><br>%{value} series<extra></extra>",
      insidetextorientation: "radial", maxdepth: chartType === "sunburst" ? 3 : 3, textinfo: "label",
      tiling: { pad: 2 }, pathbar: { visible: true, textfont: { size: fontSize() } },
      textfont: { size: fontSize() },
    };
    const layout = App.plotLayout({ margin: { l: 4, r: 4, t: 4, b: 4 } });
    layout.font = Object.assign({}, layout.font, { size: fontSize() });
    layout.hoverlabel = Object.assign({}, layout.hoverlabel, { font: Object.assign({}, layout.hoverlabel.font, { size: fontSize() }) });
    Plotly.react("sunburst", [trace], layout, App.plotConfig);
    const el = $("sunburst");
    if (!el._bound) {
      el.on("plotly_sunburstclick", onNode); el.on("plotly_treemapclick", onNode);
      el._bound = true;
    }
  }

  function onNode(ev) {
    const p = ev.points && ev.points[0];
    if (!p) return;
    const cd = p.customdata;
    if (cd && cd.startsWith("leaf:")) { showLeaf(DATA.find((s) => s.slug === cd.slice(5))); return false; }
    const parts = p.id.split("/");
    const [a, b] = PAIRS[hier].map((k) => DIM[k]);
    const rows = DATA.filter((s) => a.key(s) === parts[0] && (parts.length < 2 || b.key(s) === parts[1]));
    const [grp, code] = cd.split(".");
    const info = (G[grp] || {})[code] || {};
    const title = parts.length < 2 ? a.label(parts[0]) : `${a.label(parts[0])}: ${b.label(parts[1])}`;
    const years = rows.map((s) => s.start);
    $("node-panel").innerHTML = `<h3>${App.esc(title)}</h3>
      <p class="small">${App.esc(info.desc || "")}</p>
      <p class="small muted">${rows.length} series, ${new Set(rows.map((s) => s.id)).size} distinct policies. Earliest start ${Math.min(...years)}, latest ${Math.max(...years)}.</p>
      <ul>${rows.sort((x, y) => x.start - y.start).map((s) => `<li><span class="tag" style="margin-right:6px"><span class="dot" style="background:${App.mechColor(s.mechanism)}"></span>${s.start}</span><a href="${App.policyUrl(s.slug)}">${App.esc(s.name)}</a> <span class="muted small">${App.esc(s.sector)}</span></li>`).join("")}</ul>
      <p style="margin-top:12px"><a class="btn ghost" href="${window.URLS.timeline}?${rows.map((s) => "sector=" + encodeURIComponent(s.sector)).filter((v, i, arr) => arr.indexOf(v) === i).join("&")}&group=${hier === "source" ? "source" : hier === "layer" ? "layer" : "mechanism"}">See these sectors on the timeline</a></p>`;
  }

  function showLeaf(s) {
    if (!s) return;
    $("node-panel").innerHTML = `<p class="small muted" style="margin:0">${App.esc(s.id)}</p><h3>${App.esc(s.name)}</h3>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin:8px 0">
        <span class="tag"><span class="dot" style="background:${App.sectorColor(s.sector)}"></span>${App.esc(s.sector)}</span>
        <span class="tag" data-term="mechanisms.${s.mechanism}"><span class="dot" style="background:${App.mechColor(s.mechanism)}"></span>${App.esc(App.mechLabel(s.mechanism))}</span>
        <span class="tag layer" data-term="layers.${s.layer}">${App.esc(App.layerLabel(s.layer))}</span></div>
      <p class="small">${App.esc(s.summary)}${s.summary.length >= 260 ? "…" : ""}</p>
      ${App.spark(s.years.intensity, App.mechColor(s.mechanism), 280, 50, 0.5)}
      <p class="note">Policy intensity 2000–2023</p>
      <p><a class="btn" href="${App.policyUrl(s.slug)}">Open the policy profile</a></p>`;
  }

  /* ---------------------------------------------------------- scatter */
  function drawScatter() {
    const seen = {};
    const jit = (s) => { const k = `${s.coverage}|${s.bindingness}`; const n = (seen[k] = (seen[k] || 0) + 1) - 1; const ang = n * 2.4, r = 0.018 * Math.sqrt(n); return [r * Math.cos(ang), r * Math.sin(ang)]; };
    const byMech = d3.group(DATA, (s) => s.mechanism);
    const traces = [...byMech.keys()].sort((a, b) => G.mechanismOrder.indexOf(a) - G.mechanismOrder.indexOf(b)).map((m) => {
      const rows = byMech.get(m), off = rows.map(jit);
      return {
        type: "scatter", mode: "markers", name: App.mechLabel(m),
        x: rows.map((s, i) => s.coverage + off[i][0]), y: rows.map((s, i) => s.bindingness + off[i][1]),
        customdata: rows.map((s) => s.slug),
        text: rows.map((s) => `<b>${s.name}</b><br>${s.sector}<br>Coverage ${App.fmt(s.coverage)}, bindingness ${App.fmt(s.bindingness)}<br>Peak intensity ${App.fmt(s.peak)}`),
        hovertemplate: "%{text}<extra></extra>",
        marker: { color: App.mechColor(m), size: rows.map((s) => 8 + 26 * Math.sqrt(s.peak || 0)), opacity: 0.85, line: { color: "#fff", width: 1 }, symbol: rows.map((s) => (s.layer === "residual" ? "diamond" : "circle")) },
      };
    });
    Plotly.newPlot("scatter", traces, App.plotLayout({
      margin: { l: 56, r: 12, t: 10, b: 50 },
      xaxis: { title: { text: "Coverage score (scope)" }, range: [0, 1.12], tickvals: [0.1, 0.25, 0.5, 1], gridcolor: "#E4EAE9" },
      yaxis: { title: { text: "Bindingness" }, range: [0.1, 1.12], tickvals: [0.25, 0.5, 0.75, 1], gridcolor: "#E4EAE9" },
      legend: { orientation: "h", y: -0.18, font: { size: 11 } },
    }), App.plotConfig);
    $("scatter").on("plotly_click", (ev) => { const p = ev.points[0]; if (p && p.customdata) location.href = App.policyUrl(p.customdata); });
  }

  /* ---------------------------------------------------------- formula */
  function setupFormula() {
    const sel = $("f-policy");
    const sorted = [...DATA].filter((s) => s.layer !== "residual").sort((a, b) => a.name.localeCompare(b.name));
    sel.innerHTML = sorted.map((s) => `<option value="${s.slug}">${App.esc(s.name)} (${App.esc(s.sector)})</option>`).join("");
    const carbon = sorted.find((s) => s.id === "IRL_P0005");
    if (carbon) sel.value = carbon.slug;
    const update = () => {
      const s = DATA.find((x) => x.slug === sel.value), year = +$("f-year").value, i = year - 2000, y = s.years;
      $("f-year-out").textContent = year;
      const bar = (v) => `<div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, (v || 0) * 100)}%"></div></div>`;
      const src = y.status[i] === "pre_implementation" ? "The policy has not started yet, so implementation is zero." :
        y.src[i] === "capmf_derived" ? `The matched OECD score this year is ${App.fmt(y.capmf[i])} out of 10, so implementation is ${App.fmt(y.impl[i])}.` :
          y.status[i] === "post_expiry_residual" ? "The policy has expired; implementation decays from its last level using an assumed half-life." :
            "No usable OECD score, so implementation follows an assumed ramp-up from the start year.";
      $("f-body").innerHTML = `
        <p class="small" style="margin-top:8px"><b>${App.esc(App.statusLabel(y.status[i]))}</b> in ${year}. ${src}</p>
        <div class="formula">
          <div class="term-box"><b>${App.fmt(y.impl[i])}</b><span>implementation</span>${bar(y.impl[i])}</div><span class="op">×</span>
          <div class="term-box"><b>${App.fmt(s.coverage)}</b><span>coverage</span>${bar(s.coverage)}</div><span class="op">×</span>
          <div class="term-box"><b>${App.fmt(s.bindingness)}</b><span>bindingness</span>${bar(s.bindingness)}</div>
        </div>
        <div class="formula"><span class="op">=</span><div class="term-box result" style="flex:1"><b>${App.fmt(y.intensity[i], 3)}</b><span>policy intensity in ${year}</span></div></div>
        <p class="note">Equal-weight alternative (simple average, zero before start): ${App.fmt(y.gated[i], 3)}</p>
        <p><a href="${App.policyUrl(s.slug)}">Open ${App.esc(s.name)}</a></p>`;
    };
    sel.addEventListener("change", update);
    $("f-year").addEventListener("input", update);
    update();
  }
})();
