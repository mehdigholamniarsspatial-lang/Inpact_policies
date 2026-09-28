(function () {
  const $ = (id) => document.getElementById(id);
  const F = JSON.parse($("flow-data").textContent);
  const M = JSON.parse($("materiality-data").textContent);
  const T = JSON.parse($("timing-data").textContent);

  /* ---------------------------------------------------- Sankey */
  const nodes = [
    [`EEA registry: ${F.eea_records} records`, "#2F68A8"],
    [`Group rows, not policies: ${F.eea_records - F.eea_single}`, "#B8C2C1"],
    [`Single measures: ${F.eea_single}`, "#2F68A8"],
    [`Distinct EEA policies: ${F.eea_units}`, "#2F68A8"],
    [`OECD level-3 categories: ${F.capmf_l3}`, "#0E7C74"],
    [`No positive score: ${F.capmf_l3 - F.capmf_pos}`, "#B8C2C1"],
    [`Positive categories: ${F.capmf_pos}`, "#0E7C74"],
    [`Excluded: ${F.eea_excluded + F.capmf_excluded}`, "#B8C2C1"],
    [`Core set: ${F.core_families} policy families`, "#0B5563"],
    [`Residual bundles: ${F.residual_bundles} (from ${F.eea_residual} measures)`, "#8C969C"],
  ];
  const links = [
    [0, 1, F.eea_records - F.eea_single, "EEA group rows are summaries of other records"],
    [0, 2, F.eea_single, "Individual policies and measures"],
    [2, 3, F.eea_units, "Scenario variants (existing / additional measures) merged into one identity"],
    [3, 8, F.eea_core, "Top-impact (90% rule) or OECD-anchored EEA policies"],
    [3, 9, F.eea_residual, "Eligible but smaller measures"],
    [3, 7, F.eea_excluded, "Failed an eligibility test"],
    [4, 5, F.capmf_l3 - F.capmf_pos, "Never scored above zero for Ireland"],
    [4, 6, F.capmf_pos, "Scored above zero at least once"],
    [6, 8, F.capmf_core, "Anchors a named national or EU instrument"],
    [6, 7, F.capmf_excluded, "No domestic instrument or start identifiable"],
  ];
  Plotly.newPlot("sankey", [{
    type: "sankey", arrangement: "snap",
    node: { label: nodes.map((n) => n[0]), color: nodes.map((n) => n[1]), pad: 18, thickness: 16, line: { color: "#fff", width: 0.5 }, hovertemplate: "%{label}<extra></extra>" },
    link: { source: links.map((l) => l[0]), target: links.map((l) => l[1]), value: links.map((l) => l[2]), customdata: links.map((l) => l[3]),
      color: links.map((l) => (l[1] === 7 || l[1] === 1 || l[1] === 5 ? "rgba(140,150,156,.25)" : l[1] === 9 ? "rgba(140,150,156,.45)" : "rgba(11,85,99,.22)")),
      hovertemplate: "%{value}: %{customdata}<extra></extra>" },
  }], App.plotLayout({ margin: { l: 8, r: 8, t: 8, b: 8 }, font: { size: 12, family: "Public Sans, sans-serif" } }), App.plotConfig);

  /* ---------------------------------------------------- Candidates */
  let C = [], origin = "", outcome = "";
  App.seg($("c-origin"), (v) => { origin = v; renderC(); });
  App.seg($("c-outcome"), (v) => { outcome = v; renderC(); });
  $("c-q").addEventListener("input", renderC);
  App.getJSON(window.URLS.selection).then((d) => { C = d.candidates; renderC(); });
  const tick = (b) => (b ? '<span class="pass">✓</span>' : '<span class="fail">✕</span>');
  const OUT = { core: '<span class="tag layer">Core</span>', residual: '<span class="tag">Residual</span>', excluded: '<span class="tag" style="border-style:dashed">Excluded</span>' };
  function renderC() {
    const q = $("c-q").value.trim().toLowerCase();
    const rows = C.filter((c) => (!origin || c.candidate_origin === origin) && (!outcome || c.outcome === outcome) && (!q || (c.candidate_name + " " + c.candidate_id).toLowerCase().includes(q)));
    $("c-count").textContent = `${rows.length} of ${C.length} candidates`;
    $("cands").tBodies[0].innerHTML = rows.map((c) => `<tr>
      <td><b>${App.esc(c.candidate_name)}</b><div class="small muted">${App.esc(c.candidate_id)}, ${c.candidate_origin.startsWith("EEA") ? "EEA" : "OECD"}</div></td>
      <td>${App.esc(c.primary_sector || "–")}</td>
      <td style="white-space:nowrap;letter-spacing:3px">${[c.criteria_a_mitigation, c.criteria_b_ireland, c.criteria_c_instrument, c.criteria_d_start, c.criteria_e_active].map(tick).join("")}</td>
      <td class="num">${c.reported_effect_kt === null ? "–" : App.fmtInt(c.reported_effect_kt)}</td>
      <td class="num">${c.cumulative_effect_share === null ? "–" : (c.cumulative_effect_share * 100).toFixed(1) + "%"}</td>
      <td>${OUT[c.outcome]}</td>
      <td class="small">${App.esc(c.exclusion_reason || ((App.G.selection[c.selection_rule] || {}).desc) || App.humanise(c.selection_rule))}</td></tr>`).join("") || '<tr><td colspan="7" class="empty">No candidates match.</td></tr>';
  }

  /* ---------------------------------------------------- Materiality */
  const mm = M.slice().reverse();
  Plotly.newPlot("materiality", [{
    type: "bar", orientation: "h", y: mm.map((d) => d.sector), x: mm.map((d) => (d.share === null ? 0 : d.share * 100)),
    marker: { color: mm.map((d) => (d.share === null ? "#D3DCDB" : "#0B5563")) },
    text: mm.map((d) => (d.share === null ? "not assessable (zero total)" : `${(d.share * 100).toFixed(1)}%, ${d.units} of ${d.eligible} measures`)),
    textposition: "outside", cliponaxis: false,
    hovertemplate: "%{y}: %{text}<extra></extra>",
  }], App.plotLayout({
    margin: { l: 90, r: 30, t: 26, b: 40 }, xaxis: { range: [0, 135], title: { text: "Share of reported sector total selected (%)" }, gridcolor: "#E4EAE9", tickvals: [0, 25, 50, 75, 90, 100] },
    shapes: [{ type: "line", x0: 90, x1: 90, yref: "paper", y0: 0, y1: 1, line: { color: "#C4841D", width: 2, dash: "dot" } }],
    annotations: [{ x: 90, y: 1.0, yref: "paper", yanchor: "bottom", text: "90% target", showarrow: false, font: { color: "#C4841D", size: 11 } }],
  }), App.plotConfig);

  /* ---------------------------------------------------- Ramp explorer */
  const sel = $("t-class");
  sel.innerHTML = T.map((t) => `<option value="${t.mechanism_class}">${App.esc(App.humanise(t.mechanism_class))}</option>`).join("");
  sel.value = "asset_subsidy";
  const drawRamp = () => {
    const t = T.find((x) => x.mechanism_class === sel.value), endAfter = +$("t-end").value;
    $("t-end-out").textContent = endAfter;
    const xs = Array.from({ length: 31 }, (_, i) => i - 2);
    let last = 0;
    const ys = xs.map((k) => {
      if (endAfter && k > endAfter) return t.half_life_years ? last * Math.pow(2, -(k - endAfter) / t.half_life_years) : 0;
      const v = Math.max(0, Math.min(1, (k - t.lag_years + 0.5) / t.ramp_years));
      last = v; return v;
    });
    Plotly.react("ramp", [{ type: "scatter", mode: "lines+markers", x: xs, y: ys, line: { color: "#C4841D", width: 2.5 }, marker: { size: 5 }, hovertemplate: "Year %{x} after start: %{y:.2f}<extra></extra>" }],
      App.plotLayout({ margin: { l: 40, r: 10, t: 10, b: 40 }, xaxis: { title: { text: "Years since start" }, gridcolor: "#E4EAE9" }, yaxis: { range: [0, 1.05], title: { text: "Implementation" }, gridcolor: "#E4EAE9" },
        annotations: [{ xref: "paper", yref: "paper", x: 1, y: 0.05, xanchor: "right", showarrow: false, text: `lag ${t.lag_years} yr, ramp ${t.ramp_years} yr, half-life ${t.half_life_years} yr`, font: { size: 11, color: "#4B5C65" } }],
        shapes: endAfter ? [{ type: "line", x0: endAfter + 0.5, x1: endAfter + 0.5, yref: "paper", y0: 0, y1: 1, line: { color: "#15252D", width: 1, dash: "dot" } }] : [] }), App.plotConfig);
  };
  sel.addEventListener("change", drawRamp); $("t-end").addEventListener("input", drawRamp); drawRamp();

  /* ---------------------------------------------------- Dictionary filter */
  $("dict-q").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    $("dict").tBodies[0].querySelectorAll("tr").forEach((tr) => { tr.hidden = q && !tr.textContent.toLowerCase().includes(q); });
  });
})();
