(function () {
  const { G } = App;
  const matrix = JSON.parse(document.getElementById("matrix-data").textContent);

  /* Sector × mechanism matrix ------------------------------------------------ */
  const sectors = G.sectorOrder.filter((s) => matrix[s]);
  const mechs = G.mechanismOrder.filter((m) => sectors.some((s) => matrix[s][m]));
  const maxN = Math.max(...sectors.flatMap((s) => mechs.map((m) => (matrix[s][m] || []).length)));
  const tbl = document.getElementById("matrix");
  let html = "<thead><tr><th></th>" + mechs.map((m) => `<th><span class="term" tabindex="0" data-term="mechanisms.${m}">${App.esc(App.mechLabel(m))}</span></th>`).join("") + "</tr></thead><tbody>";
  sectors.forEach((s) => {
    html += `<tr><th class="rowh" scope="row"><span class="term" tabindex="0" data-term="sectors.${s}">${App.esc(s)}</span></th>`;
    mechs.forEach((m) => {
      const list = matrix[s][m] || [];
      if (!list.length) { html += "<td></td>"; return; }
      const bg = App.tint(App.mechColor(m), 0.45 + 0.55 * (list.length / maxN));
      html += `<td class="has" tabindex="0" style="background:${bg}" data-s="${App.esc(s)}" data-m="${m}">${list.length}</td>`;
    });
    html += "</tr>";
  });
  tbl.innerHTML = html + "</tbody>";
  tbl.addEventListener("mouseover", (e) => {
    const td = e.target.closest("td.has"); if (!td) return;
    const list = matrix[td.dataset.s][td.dataset.m];
    App.showTip(`<strong>${App.esc(td.dataset.s)}: ${App.esc(App.mechLabel(td.dataset.m))}</strong>` + list.map((p) => "\u2022 " + App.esc(p.name)).join("<br>") + "<hr>Click to open in the policy list", e);
  });
  tbl.addEventListener("mousemove", App.moveTip);
  tbl.addEventListener("mouseout", App.hideTip);
  const go = (td) => { location.href = `${window.URLS.policyBase}?sector=${encodeURIComponent(td.dataset.s)}&mechanism=${td.dataset.m}`; };
  tbl.addEventListener("click", (e) => { const td = e.target.closest("td.has"); if (td) go(td); });
  tbl.addEventListener("keydown", (e) => { const td = e.target.closest("td.has"); if (td && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); go(td); } });

  App.getJSON(window.URLS.series).then(({ series, years }) => {
    /* Layer counts */
    const layerCounts = {};
    series.forEach((s) => { layerCounts[s.layer] = layerCounts[s.layer] || new Set(); layerCounts[s.layer].add(s.id); });
    document.querySelectorAll("[data-layer-count]").forEach((el) => {
      const n = (layerCounts[el.dataset.layerCount] || new Set()).size;
      el.textContent = `(${n} ${el.dataset.layerCount === "residual" ? "bundles" : n === 1 ? "policy" : "policies"})`;
    });

    drawRiver(series, years);
    drawEmissions();
    drawActive(series, years);
    drawSource(series, years);
  });

  /* Emissions context ------------------------------------------------------------ */
  function drawEmissions() {
    const E = JSON.parse(document.getElementById("emissions-data").textContent).filter((d) => d.sector !== "LULUCF").sort((a, b) => a.mt - b.mt);
    Plotly.newPlot("emis-chart", [
      { type: "bar", orientation: "h", name: "Emissions 2023 (Mt CO₂e)", y: E.map((d) => d.sector), x: E.map((d) => d.mt),
        marker: { color: E.map((d) => d.color) }, text: E.map((d) => `${d.mt.toFixed(1)} Mt (${(d.share * 100).toFixed(1)}%)`), textposition: "outside", cliponaxis: false,
        customdata: E.map((d) => d.note), hovertemplate: "<b>%{y}</b><br>%{x:.2f} Mt CO₂e<br>%{customdata}<extra></extra>", xaxis: "x" },
      { type: "scatter", mode: "markers+text", name: "Policy series", y: E.map((d) => d.sector), x: E.map((d) => d.series), xaxis: "x2",
        marker: { symbol: "diamond", size: 11, color: "#15252D" }, text: E.map((d) => d.series), textposition: "middle right", textfont: { size: 11 },
        hovertemplate: "%{y}: %{x} policy series<extra></extra>" },
    ], App.plotLayout({
      margin: { l: 86, r: 20, t: 16, b: 44 }, barmode: "overlay", showlegend: false,
      xaxis: { domain: [0, 0.68], title: { text: "Mt CO₂e, 2023" }, gridcolor: "#E4EAE9", range: [0, 27] },
      xaxis2: { domain: [0.76, 1], title: { text: "Policy series" }, gridcolor: "#E4EAE9", range: [0, 16] },
      yaxis: { gridcolor: "rgba(0,0,0,0)" },
    }), App.plotConfig);
  }

  /* Hero "river": one thin strip per series ---------------------------------- */
  function drawRiver(series, years) {
    const el = document.getElementById("river");
    const ordered = [...series].sort((a, b) => (G.sectorOrder.indexOf(a.sector) - G.sectorOrder.indexOf(b.sector)) || (a.start - b.start));
    const W = el.clientWidth || 640, rowH = 6, gap = 2, left = 0, top = 4, bottom = 22;
    const H = top + ordered.length * (rowH + gap) + bottom;
    const x = d3.scaleBand().domain(years).range([left, W]).paddingInner(0.08);
    const svg = d3.select(el).append("svg").attr("width", W).attr("height", H).attr("viewBox", `0 0 ${W} ${H}`);
    const rows = svg.selectAll("g.r").data(ordered).join("g").attr("class", "r")
      .attr("transform", (d, i) => `translate(0,${top + i * (rowH + gap)})`).style("cursor", "pointer")
      .on("click", (e, d) => { location.href = App.policyUrl(d.slug); })
      .on("mouseenter", function (e, d) {
        d3.select(this).selectAll("rect").attr("stroke", "#15252D").attr("stroke-width", 0.6);
        App.showTip(`<strong>${App.esc(d.name)}</strong>${App.esc(d.sector)}, ${App.esc(App.mechLabel(d.mechanism))}<br>Starts ${d.start}${d.end ? `, ends ${d.end}` : ""}<br>Intensity 2023: ${App.fmt(d.i2023)}`, e);
      })
      .on("mousemove", App.moveTip)
      .on("mouseleave", function () { d3.select(this).selectAll("rect").attr("stroke", null); App.hideTip(); });
    rows.selectAll("rect").data((d) => years.map((y, i) => ({ y, v: d.years.intensity[i], st: d.years.status[i], m: d.mechanism })))
      .join("rect").attr("x", (d) => x(d.y)).attr("width", x.bandwidth()).attr("height", rowH).attr("rx", 1)
      .attr("fill", (d) => d.st === "pre_implementation" ? "#EEF2F1" : App.tint(App.mechColor(d.m), 0.12 + 0.88 * Math.sqrt(Math.min(1, (d.v || 0) / 0.5))));
    const axis = svg.append("g").attr("transform", `translate(0,${H - bottom + 4})`).attr("class", "tl-axis");
    [2000, 2005, 2010, 2015, 2020, 2023].forEach((y) => {
      axis.append("text").attr("x", x(y) + x.bandwidth() / 2).attr("y", 12).attr("text-anchor", "middle").text(y);
    });
    const leg = document.getElementById("river-legend");
    leg.innerHTML = [...new Set(series.map((s) => s.mechanism))].sort((a, b) => G.mechanismOrder.indexOf(a) - G.mechanismOrder.indexOf(b))
      .map((m) => `<span class="tag" data-term="mechanisms.${m}"><span class="dot" style="background:${App.mechColor(m)}"></span>${App.esc(App.mechLabel(m))}</span>`).join(" ");
  }

  /* Active series by sector (stacked area) ------------------------------------ */
  function drawActive(series, years) {
    const traces = G.sectorOrder.map((sec) => {
      const ss = series.filter((s) => s.sector === sec);
      if (!ss.length) return null;
      return {
        type: "scatter", mode: "lines", stackgroup: "a", name: sec, x: years,
        y: years.map((_, i) => ss.filter((s) => s.years.status[i] === "active").length),
        line: { width: 0.8, color: App.sectorColor(sec) }, fillcolor: App.tint(App.sectorColor(sec), 0.75),
        hovertemplate: `${sec}: %{y}<extra></extra>`,
      };
    }).filter(Boolean);
    Plotly.newPlot("active-chart", traces, App.plotLayout({ hovermode: "x unified", yaxis: { title: { text: "Active series" }, gridcolor: "#E4EAE9" }, legend: { orientation: "v", x: 1.02, y: 1, font: { size: 11 } }, margin: { l: 52, r: 120, t: 12, b: 36 } }), App.plotConfig);
  }

  /* Implementation source among active series ---------------------------------- */
  function drawSource(series, years) {
    const count = (fn) => years.map((_, i) => series.filter((s) => s.layer !== "residual" && s.years.status[i] !== "pre_implementation" && fn(s, i)).length);
    const oecd = count((s, i) => s.years.src[i] === "capmf_derived");
    const assumed = count((s, i) => s.years.src[i] === "assumed");
    const traces = [
      { type: "bar", name: "OECD CAPMF score", x: years, y: oecd, marker: { color: "#0B5563" }, hovertemplate: "OECD-derived: %{y}<extra></extra>" },
      { type: "bar", name: "Assumed ramp-up or decay", x: years, y: assumed, marker: { color: "#C4841D" }, hovertemplate: "Assumed: %{y}<extra></extra>" },
    ];
    Plotly.newPlot("source-chart", traces, App.plotLayout({ barmode: "stack", hovermode: "x unified", bargap: 0.18, yaxis: { title: { text: "Active core series" }, gridcolor: "#E4EAE9" } }), App.plotConfig);
  }
})();
