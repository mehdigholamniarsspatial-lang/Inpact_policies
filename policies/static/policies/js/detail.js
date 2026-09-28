(function () {
  const C = JSON.parse(document.getElementById("chart-data").textContent);
  const P = window.POLICY;
  const $ = (id) => document.getElementById(id);
  let mode = "index", year = 2023;
  const STATUS_FILL = { pre_implementation: "rgba(0,0,0,0)", active: "rgba(11,85,99,.05)", post_expiry_residual: "rgba(196,132,29,.10)", post_expiry_no_effect: "rgba(0,0,0,.05)" };

  function bands() {
    const out = [];
    let start = 0;
    for (let i = 1; i <= C.years.length; i++) {
      if (i === C.years.length || C.status[i] !== C.status[start]) {
        out.push({ type: "rect", xref: "x", yref: "paper", x0: C.years[start] - 0.5, x1: C.years[i - 1] + 0.5, y0: 0, y1: 1, fillcolor: STATUS_FILL[C.status[start]], line: { width: 0 }, layer: "below" });
        start = i;
      }
    }
    return out;
  }
  const markerFor = (color) => ({ size: 7, color: C.src.map((s) => (s === "capmf_derived" ? color : "#fff")), line: { color, width: 1.6 } });

  function draw() {
    let traces;
    if (mode === "index") {
      traces = [
        { name: "Policy intensity", y: C.intensity, line: { color: "#0B5563", width: 3 }, marker: markerFor("#0B5563") },
        { name: "Implementation level", y: C.impl, line: { color: P.color, width: 1.8, dash: "dot" }, marker: markerFor(P.color) },
        { name: "Equal-weight (gated)", y: C.gated, line: { color: "#8C969C", width: 1.4, dash: "dash" }, mode: "lines" },
      ];
    } else {
      traces = [{ name: "OECD stringency", y: C.capmf, line: { color: "#0E7C74", width: 2.5 }, marker: { size: 7, color: "#0E7C74" }, connectgaps: false }];
    }
    traces = traces.map((t) => Object.assign({ type: "scatter", mode: "lines+markers", x: C.years, hovertemplate: `${t.name}: %{y:.3f}<extra></extra>` }, t));
    const shapes = bands().concat([{ type: "line", x0: year, x1: year, yref: "paper", y0: 0, y1: 1, line: { color: "#C4841D", width: 1.5, dash: "dot" } }]);
    const annotations = [];
    const statusStarts = C.status.map((s, i) => (i === 0 || s !== C.status[i - 1] ? i : -1)).filter((i) => i >= 0);
    statusStarts.forEach((i) => annotations.push({ x: C.years[i] - 0.4, y: 1, yref: "paper", xanchor: "left", yanchor: "top", showarrow: false, text: App.statusLabel(C.status[i]), font: { size: 10, color: "#4B5C65" } }));
    Plotly.react("chart", traces, App.plotLayout({
      hovermode: "x unified", shapes, annotations, margin: { l: 44, r: 12, t: 10, b: 60 },
      yaxis: { range: mode === "index" ? [0, 1.08] : [0, 10.5], gridcolor: "#E4EAE9", title: { text: mode === "index" ? "0–1 index" : "0–10 scale" } },
      xaxis: { dtick: 2, gridcolor: "#E4EAE9" },
      legend: { orientation: "h", y: -0.16, font: { size: 11 } },
    }), App.plotConfig);
  }

  function breakdown() {
    const i = year - 2000;
    $("yr-out").textContent = year;
    const src = C.status[i] === "pre_implementation" ? "Not started, so implementation is zero." :
      C.src[i] === "capmf_derived" ? `Matched OECD stringency ${App.fmt(C.capmf[i])} / 10.` :
        C.detail[i] === "endpoint_assumed_times_assumed_half_life" ? "Expired: last level decays with an assumed half-life." :
          P.residual ? "Average of the bundle members." : "No OECD score: assumed ramp-up from the start year.";
    $("breakdown").innerHTML = `<p class="small" style="margin:10px 0 0"><b>${year}: ${App.esc(App.statusLabel(C.status[i]))}.</b> ${src}</p>
      <div class="formula">
        <div class="term-box"><b>${App.fmt(C.impl[i])}</b><span>implementation</span></div><span class="op">×</span>
        <div class="term-box"><b>${App.fmt(P.coverage)}</b><span>coverage${P.residual ? " (mean)" : ""}</span></div><span class="op">×</span>
        <div class="term-box"><b>${App.fmt(P.bindingness)}</b><span>bindingness${P.residual ? " (mean)" : ""}</span></div><span class="op">${P.residual ? "≈" : "="}</span>
        <div class="term-box result"><b>${App.fmt(C.intensity[i], 3)}</b><span>policy intensity</span></div>
      </div>${P.residual ? '<p class="note">For residual bundles, intensity is the mean of member intensities, so multiplying the displayed means does not reproduce it exactly.</p>' : ""}`;
  }

  App.seg($("chart-mode"), (v) => { mode = v; draw(); });
  $("yr").addEventListener("input", (e) => { year = +e.target.value; draw(); breakdown(); });
  draw(); breakdown();
  $("chart").on("plotly_click", (ev) => { if (ev.points[0]) { year = +ev.points[0].x; $("yr").value = year; draw(); breakdown(); } });
})();
