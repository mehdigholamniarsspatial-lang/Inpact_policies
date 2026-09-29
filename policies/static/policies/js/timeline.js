(function () {
  const { G } = App;
  const params = new URLSearchParams(location.search);
  const state = {
    view: params.get("view") || "grid",
    metric: params.get("metric") || "intensity",
    group: params.get("group") || "sector",
    sort: params.get("sort") || "start",
    q: params.get("q") || "",
    year: +(params.get("year") || 2015),
    sectors: null,
    layers: null,
  };
  const METRIC = {
    intensity: { label: "Policy intensity", max: 0.5, digits: 2 },
    impl: { label: "Implementation level", max: 1, digits: 2 },
    capmf: { label: "OECD stringency", max: 10, digits: 2 },
    gated: { label: "Equal-weight intensity", max: 1, digits: 2 },
  };
  let DATA = [], YEARS = [];

  /* ------------------------------------------------------------------ controls */
  const $ = (id) => document.getElementById(id);
  const setPressed = (el, v) => el.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.value === v ? "true" : "false"));
  setPressed($("view"), state.view); setPressed($("group"), state.group);
  $("metric").value = state.metric; $("sort").value = state.sort; $("q").value = state.q;
  $("year").value = state.year; $("year-out").textContent = state.year;
  App.seg($("view"), (v) => { state.view = v; render(); });
  App.seg($("group"), (v) => { state.group = v; render(); });
  $("metric").addEventListener("change", (e) => { state.metric = e.target.value; render(); });
  $("sort").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
  $("q").addEventListener("input", (e) => { state.q = e.target.value.trim().toLowerCase(); render(); });
  $("year").addEventListener("input", (e) => setYear(+e.target.value));
  const tlFont = App.textSizer($("tl-font"), { key: "timeline", sizes: [11, 12.5, 14, 16, 18, 20], start: 12.5 }, () => render());

  let timer = null;
  $("play").addEventListener("click", () => {
    if (timer) return stop();
    if (state.year >= 2023) setYear(2000);
    $("play").textContent = "❚❚ Pause";
    timer = setInterval(() => { if (state.year >= 2023) return stop(); setYear(state.year + 1); }, 750);
  });
  function stop() { clearInterval(timer); timer = null; $("play").textContent = "▶ Play"; }

  $("drawer-close").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

  /* ------------------------------------------------------------------ data */
  App.getJSON(window.URLS.series).then((d) => {
    DATA = d.series; YEARS = d.years;
    const sectors = G.sectorOrder.filter((s) => DATA.some((x) => x.sector === s));
    const layers = G.layerOrder.filter((l) => DATA.some((x) => x.layer === l));
    const sectorChips = App.chipGroup($("sector-chips"), sectors.map((s) => ({ value: s, label: s, color: App.sectorColor(s), term: `sectors.${s}` })), (a) => { state.sectors = a; render(); });
    const layerChips = App.chipGroup($("layer-chips"), layers.map((l) => ({ value: l, label: App.layerLabel(l), color: "#0B5563", term: `layers.${l}` })), (a) => { state.layers = a; render(); });
    state.sectors = sectorChips.active; state.layers = layerChips.active;
    if (params.get("sector")) sectorChips.set(params.getAll("sector"));
    if (params.get("layer")) layerChips.set(params.getAll("layer"));
    render();
    window.addEventListener("resize", debounce(render, 150));
  }).catch(() => { $("canvas").innerHTML = '<div class="empty">The timeline data could not be loaded. Reload the page to try again.</div>'; });

  function debounce(fn, ms) { let t; return () => { clearTimeout(t); t = setTimeout(fn, ms); }; }

  /* ------------------------------------------------------------------ helpers */
  const groupKey = (s) => ({ sector: s.sector, mechanism: s.mechanism, layer: s.layer, source: s.source }[state.group]);
  const groupOrder = () => ({ sector: G.sectorOrder, mechanism: G.mechanismOrder, layer: G.layerOrder, source: ["EEA+CAPMF", "EEA", "CAPMF"] }[state.group]);
  const groupLabel = (k) => ({ sector: k, mechanism: App.mechLabel(k), layer: App.layerLabel(k), source: (G.sources[k] || {}).label || k }[state.group]);
  const groupTerm = (k) => ({ sector: `sectors.${k}`, mechanism: `mechanisms.${k}`, layer: `layers.${k}`, source: `sources.${k}` }[state.group]);
  const groupColor = (k) => ({ sector: App.sectorColor(k), mechanism: App.mechColor(k), layer: "#0B5563", source: "#0B5563" }[state.group]);
  const val = (s, i) => s.years[state.metric][i];
  const yi = (y) => y - 2000;

  function filtered() {
    return DATA.filter((s) => state.sectors.has(s.sector) && state.layers.has(s.layer) &&
      (!state.q || (s.name + " " + s.id + " " + s.capmfCode + " " + s.bundle).toLowerCase().includes(state.q)));
  }
  function grouped(list) {
    const order = groupOrder();
    const cmp = {
      start: (a, b) => a.start - b.start || a.name.localeCompare(b.name),
      i2023: (a, b) => (b.i2023 ?? -1) - (a.i2023 ?? -1),
      peak: (a, b) => (b.peak ?? -1) - (a.peak ?? -1),
      name: (a, b) => a.name.localeCompare(b.name),
    }[state.sort];
    const map = d3.group(list, groupKey);
    return [...map.entries()].sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0])).map(([k, rows]) => ({ key: k, rows: rows.sort(cmp) }));
  }

  function syncUrl() {
    const p = new URLSearchParams();
    ["view", "metric", "group", "sort", "year"].forEach((k) => p.set(k, state[k]));
    if (state.q) p.set("q", state.q);
    history.replaceState(null, "", "?" + p.toString());
    const e = new URLSearchParams();
    const allS = G.sectorOrder.filter((s) => DATA.some((x) => x.sector === s));
    if (state.sectors.size < allS.length) state.sectors.forEach((s) => e.append("sector", s));
    const allL = G.layerOrder;
    if (state.layers.size < allL.length) state.layers.forEach((l) => e.append("layer", l));
    if (state.q) filtered().forEach((s) => e.append("policy_id", s.id));
    $("export").href = window.URLS.exportCsv + (e.toString() ? "?" + e.toString() : "");
  }

  /* ------------------------------------------------------------------ render */
  function render() {
    if (!DATA.length) return;
    $("metric-control").style.opacity = state.view === "grid" ? 1 : 0.45;
    $("metric").disabled = state.view !== "grid";
    const groups = grouped(filtered());
    drawLegend();
    if (state.view === "grid") drawGrid(groups); else drawLife(groups);
    drawSnapshot();
    drawCharts(groups);
    syncUrl();
  }

  function drawLegend() {
    const el = $("legend");
    if (state.view === "grid") {
      const m = METRIC[state.metric];
      const steps = [0.02, 0.1, 0.25, 0.5].map((t) => `<span class="sw" style="background:${App.tint("#0B5563", 0.1 + 0.9 * Math.sqrt(t / 0.5))}" title="${(t / 0.5 * m.max).toFixed(2)}"></span>`).join("");
      el.innerHTML = `<span><b>${m.label}</b>: 0 ${steps} ${m.max}+ (in each policy's mechanism colour)</span>
        <span><span class="sw" style="background:linear-gradient(#fff 0 4px,#DDE4E3 4px 6px,#fff 6px)"></span>Not yet started</span>
        <span><span class="sw" style="background:repeating-linear-gradient(135deg,#0B5563 0 3px,#8FB6BC 3px 5px)"></span>Implementation assumed (no OECD score)</span>
        <span><span class="sw" style="background:#fff;border:1.5px dotted #4B5C65"></span>Expired, lingering effect</span>
        ${state.metric === "capmf" ? '<span><span class="sw" style="background:repeating-linear-gradient(45deg,#fff 0 3px,#DCE3E2 3px 4px)"></span>No OECD match</span>' : ""}
        <span>▸ start, ▮ end</span>`;
    } else {
      el.innerHTML = [...new Set(DATA.map((s) => s.mechanism))].sort((a, b) => G.mechanismOrder.indexOf(a) - G.mechanismOrder.indexOf(b))
        .map((m) => `<span data-term="mechanisms.${m}"><span class="sw" style="background:${App.mechColor(m)}"></span>${App.esc(App.mechLabel(m))}</span>`).join("") +
        `<span><span class="sw" style="background:linear-gradient(90deg,#8C969C,#fff)"></span>Lingering effect after expiry</span>`;
    }
  }

  function frame(groups, years) {
    const el = $("canvas");
    el.innerHTML = "";
    if (!groups.length) { el.innerHTML = '<div class="empty">No policies match these filters. Turn a sector or layer back on, or clear the search box.</div>'; return null; }
    const k = tlFont() / 12.5;
    el.style.setProperty("--tl-k", k);
    const W = Math.max(el.clientWidth, 760);
    const labelW = Math.min(380, Math.max(240, W * 0.33)) * Math.min(k, 1.25);
    const right = 14, top = 34, rowH = Math.round(22 * k), headH = Math.round(34 * k);
    const colW = (W - labelW - right) / years.length;
    let y = top;
    const layout = [];
    groups.forEach((g) => {
      layout.push({ type: "head", g, y }); y += headH;
      g.rows.forEach((s) => { layout.push({ type: "row", s, y }); y += rowH; });
      y += 6;
    });
    const H = y + 8;
    const svg = d3.select(el).append("svg").attr("width", W).attr("height", H).attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img")
      .attr("aria-label", `${state.view === "grid" ? "Intensity grid" : "Lifespan chart"} of ${groups.reduce((n, g) => n + g.rows.length, 0)} policy series`);
    const defs = svg.append("defs");
    const hatch = defs.append("pattern").attr("id", "hatch").attr("patternUnits", "userSpaceOnUse").attr("width", 5).attr("height", 5).attr("patternTransform", "rotate(45)");
    hatch.append("rect").attr("width", 1.6).attr("height", 5).attr("fill", "rgba(255,255,255,.55)");
    const nodata = defs.append("pattern").attr("id", "nodata").attr("patternUnits", "userSpaceOnUse").attr("width", 4).attr("height", 4).attr("patternTransform", "rotate(-45)");
    nodata.append("rect").attr("width", 4).attr("height", 4).attr("fill", "#fff");
    nodata.append("rect").attr("width", 1).attr("height", 4).attr("fill", "#DCE3E2");
    return { svg, W, H, labelW, colW, rowH, headH, top, layout, k, x: (yr) => labelW + (yr - years[0]) * colW };
  }

  function drawAxis(f, years, step) {
    const ax = f.svg.append("g").attr("class", "tl-axis");
    years.forEach((yr) => {
      const sel = yr === state.year;
      const near = state.year >= years[0] && Math.abs(yr - state.year) * f.colW < 34 && !sel;
      if (!sel && (near || ((yr % step !== 0) && yr !== years[years.length - 1]))) return;
      if (!sel && yr === years[years.length - 1] && (yr % step !== 0) && f.colW * (yr % step) < 34) return;
      ax.append("text").attr("x", f.x(yr) + f.colW / 2).attr("y", 20).attr("text-anchor", "middle")
        .style("font-weight", sel ? 700 : 500).style("fill", sel ? "var(--cursor)" : null)
        .style("cursor", yr >= 2000 ? "pointer" : null).text(f.colW < 24 && !sel ? "'" + String(yr).slice(2) : yr)
        .on("click", () => { if (yr >= 2000) setYear(yr); });
    });
    // clickable header strip for any year
    ax.selectAll("rect.hit").data(years.filter((y) => y >= 2000)).join("rect").attr("class", "hit")
      .attr("x", (d) => f.x(d)).attr("y", 4).attr("width", f.colW).attr("height", 22).attr("fill", "transparent").style("cursor", "pointer")
      .on("click", (e, d) => setYear(d)).append("title").text((d) => `Show ${d}`);
  }

  function drawLabels(f) {
    const heads = f.svg.append("g");
    f.layout.filter((l) => l.type === "head").forEach((l) => {
      const g = heads.append("g").attr("transform", `translate(0,${l.y})`);
      g.append("rect").attr("x", 0).attr("y", 6).attr("width", f.W).attr("height", f.headH - 8).attr("fill", "#F4F7F6");
      g.append("rect").attr("x", 0).attr("y", 6).attr("width", 4).attr("height", f.headH - 8).attr("fill", groupColor(l.g.key));
      const t = g.append("text").attr("x", 14).attr("y", f.headH / 2 + 1 + 5 * f.k).attr("class", "tl-group-label").attr("data-term", groupTerm(l.g.key)).text(groupLabel(l.g.key));
      const bb = t.node().getComputedTextLength();
      g.append("text").attr("x", 14 + bb + 8).attr("y", f.headH / 2 + 1 + 5 * f.k).attr("class", "tl-group-sub").text(`${l.g.rows.length} series`);
    });
    const rows = f.svg.append("g");
    f.layout.filter((l) => l.type === "row").forEach((l) => {
      const s = l.s;
      const g = rows.append("g").attr("transform", `translate(0,${l.y})`).attr("class", "tl-row").datum(s);
      g.append("rect").attr("class", "row-bg").attr("x", 0).attr("y", 1).attr("width", f.W).attr("height", f.rowH - 2).attr("fill", "transparent");
      g.append("circle").attr("cx", 12).attr("cy", f.rowH / 2).attr("r", 4).attr("fill", App.mechColor(s.mechanism));
      const extra = state.group === "sector" ? "" : s.sector;
      const since = s.start < 2000 ? `since ${s.start}` : "";
      const side = [since, extra].filter(Boolean).join(", ");
      const txt = g.append("text").attr("class", "tl-row-label").attr("x", 22).attr("y", f.rowH / 2 + 4 * f.k).attr("tabindex", 0).text(s.name)
        .on("click", () => openDrawer(s)).on("keydown", (e) => { if (e.key === "Enter") openDrawer(s); });
      let sideW = 0;
      if (side) sideW = g.append("text").attr("x", f.labelW - 8).attr("y", f.rowH / 2 + 4 * f.k).attr("text-anchor", "end").attr("class", "tl-group-sub").style("font-size", `${11 * f.k}px`).text(side).node().getComputedTextLength() + 8;
      const avail = f.labelW - 30 - sideW - 8;
      const node = txt.node();
      if (node.getComputedTextLength() > avail) {
        let n = s.name.length;
        while (n > 4 && node.getComputedTextLength() > avail) { n -= 2; node.textContent = s.name.slice(0, n) + "…"; }
      }
      txt.append("title").text(`${s.name} (${s.sector})`);
    });
    return rows;
  }

  function hoverRow(f, rowsSel) {
    const hl = (s, on) => rowsSel.selectAll("g.tl-row").filter((d) => d === s).select("rect.row-bg").attr("fill", on ? "#EEF4F4" : "transparent");
    return hl;
  }

  function cursor(f, years) {
    if (state.year < years[0]) return;
    f.svg.append("rect").attr("x", f.x(state.year)).attr("y", f.top - 4).attr("width", f.colW).attr("height", f.H - f.top)
      .attr("fill", "rgba(196,132,29,.08)").attr("stroke", "var(--cursor)").attr("stroke-width", 1.2).attr("pointer-events", "none");
  }

  /* --------------------------------------------------------------- grid view */
  function drawGrid(groups) {
    const years = YEARS;
    const f = frame(groups, years);
    if (!f) return;
    drawAxis(f, years, f.colW < 26 ? 5 : 2);
    const rowsSel = drawLabels(f);
    const hl = hoverRow(f, rowsSel);
    const m = METRIC[state.metric];
    const cells = f.svg.append("g");
    const pad = f.colW > 18 ? 1.5 : 0.8;
    f.layout.filter((l) => l.type === "row").forEach((l) => {
      const s = l.s, color = App.mechColor(s.mechanism);
      const g = cells.append("g").attr("transform", `translate(0,${l.y})`);
      years.forEach((yr, i) => {
        const st = s.years.status[i], v = val(s, i);
        const x = f.x(yr) + pad, w = f.colW - pad * 2, h = f.rowH - 6;
        if (st === "pre_implementation") {
          g.append("rect").attr("x", x).attr("y", f.rowH / 2 - 1).attr("width", w).attr("height", 2).attr("fill", "#DDE4E3");
        } else {
        let fill;
        if (v === null) fill = state.metric === "capmf" ? "url(#nodata)" : "#E7ECEB";
        else fill = App.tint(color, 0.1 + 0.9 * shade(v, m));
        const r = g.append("rect").attr("x", x).attr("y", 3).attr("width", w).attr("height", h).attr("rx", 2).attr("fill", fill);
        if (st === "post_expiry_residual") r.attr("stroke", "#4B5C65").attr("stroke-dasharray", "1.5,1.5").attr("stroke-width", 1.1);
        if (st !== "pre_implementation" && s.years.src[i] === "assumed" && s.layer !== "residual" && v !== null && state.metric !== "capmf")
          g.append("rect").attr("x", x).attr("y", 3).attr("width", w).attr("height", h).attr("rx", 2).attr("fill", "url(#hatch)").attr("pointer-events", "none");
        }
        g.append("rect").attr("x", f.x(yr)).attr("y", 0).attr("width", f.colW).attr("height", f.rowH).attr("fill", "transparent").style("cursor", "pointer")
          .on("mouseenter", (e) => { hl(s, true); App.showTip(cellTip(s, i), e); })
          .on("mousemove", App.moveTip)
          .on("mouseleave", () => { hl(s, false); App.hideTip(); })
          .on("click", () => { setYear(yr, false); openDrawer(s); });
      });
      if (s.start >= 2000) g.append("path").attr("d", `M${f.x(s.start) + 0.5},3 l4,${(f.rowH - 6) / 2} l-4,${(f.rowH - 6) / 2}Z`).attr("fill", "#15252D").attr("pointer-events", "none");
      if (s.end && s.end <= 2023) g.append("rect").attr("x", f.x(s.end) + f.colW - 3).attr("y", 2).attr("width", 2.5).attr("height", f.rowH - 4).attr("fill", "#15252D").attr("pointer-events", "none");
    });
    cursor(f, years);
  }

  function shade(v, m) { return Math.sqrt(Math.max(0, Math.min(1, v / m.max))); }

  function cellTip(s, i) {
    const yr = YEARS[i], y = s.years;
    const src = y.src[i] === "capmf_derived" ? "OECD CAPMF score" : (y.status[i] === "pre_implementation" ? "Not started (structural zero)" : "Assumed timing");
    return `<strong>${App.esc(s.name)}</strong>${App.esc(s.sector)}, ${yr}: ${App.esc(App.statusLabel(y.status[i]))}<hr>
      <div class="row"><span>Policy intensity</span><b>${App.fmt(y.intensity[i])}</b></div>
      <div class="row"><span>Implementation</span><b>${App.fmt(y.impl[i])}</b></div>
      <div class="row"><span>OECD stringency</span><b>${y.capmf[i] === null ? "no match" : App.fmt(y.capmf[i]) + " / 10"}</b></div>
      <div class="row"><span>Coverage × bindingness</span><b>${App.fmt(s.coverage)} × ${App.fmt(s.bindingness)}</b></div>
      <div class="row"><span>Implementation from</span><b>${src}</b></div><hr>Click for details`;
  }

  /* --------------------------------------------------------------- lifespan view */
  function drawLife(groups) {
    const years = d3.range(1990, 2024);
    const f = frame(groups, years);
    if (!f) return;
    // shade the pre-window
    f.svg.append("rect").attr("x", f.x(1990)).attr("y", f.top - 4).attr("width", f.x(2000) - f.x(1990)).attr("height", f.H - f.top).attr("fill", "#F4F6F6");
    f.svg.append("text").attr("x", (f.x(1990) + f.x(2000)) / 2).attr("y", f.H - 6).attr("text-anchor", "middle").attr("class", "tl-group-sub").style("font-size", `${11 * f.k}px`).text("Before the dataset window");
    drawAxis(f, years, 5);
    const rowsSel = drawLabels(f);
    const hl = hoverRow(f, rowsSel);
    const bars = f.svg.append("g");
    f.layout.filter((l) => l.type === "row").forEach((l) => {
      const s = l.s, color = App.mechColor(s.mechanism);
      const g = bars.append("g").attr("transform", `translate(0,${l.y})`).style("cursor", "pointer")
        .on("mouseenter", (e) => { hl(s, true); App.showTip(lifeTip(s), e); })
        .on("mousemove", App.moveTip).on("mouseleave", () => { hl(s, false); App.hideTip(); })
        .on("click", () => openDrawer(s));
      const x0 = f.x(Math.max(1990, s.start)), endY = s.end ?? 2023, x1 = f.x(endY) + f.colW;
      g.append("rect").attr("x", x0).attr("y", 4).attr("width", Math.max(3, x1 - x0)).attr("height", f.rowH - 8).attr("rx", 3).attr("fill", color);
      if (s.end && s.end < 2023) {
        const lingering = s.years.status.some((st) => st === "post_expiry_residual");
        if (lingering) {
          const gid = "fade-" + s.slug;
          const lg = f.svg.select("defs").append("linearGradient").attr("id", gid);
          lg.append("stop").attr("offset", 0).attr("stop-color", color).attr("stop-opacity", 0.55);
          lg.append("stop").attr("offset", 1).attr("stop-color", color).attr("stop-opacity", 0.05);
          g.append("rect").attr("x", x1).attr("y", 6).attr("width", f.x(2023) + f.colW - x1).attr("height", f.rowH - 12).attr("fill", `url(#${gid})`);
        }
      }
      const label = s.end ? `${s.start}–${s.end}` : `${s.start}–`;
      const inside = x1 - x0 > 60 * f.k;
      const roomRight = f.W - x1 > 48 * f.k;
      g.append("text").attr("x", inside ? x0 + 6 : roomRight ? x1 + 5 : x0 - 5).attr("text-anchor", inside || roomRight ? "start" : "end")
        .attr("y", f.rowH / 2 + 4 * f.k).style("font", `600 ${11 * f.k}px var(--sans)`)
        .attr("fill", inside ? "#fff" : "#4B5C65").text(label).attr("pointer-events", "none");
    });
    cursor(f, years);
  }

  function lifeTip(s) {
    return `<strong>${App.esc(s.name)}</strong>${App.esc(s.sector)}, ${App.esc(App.mechLabel(s.mechanism))}<hr>
      <div class="row"><span>Start</span><b>${s.start}</b></div><div class="row"><span>End</span><b>${s.end || "open / continuing"}</b></div>
      <div class="row"><span>Layer</span><b>${App.esc(App.layerLabel(s.layer))}</b></div><div class="row"><span>Source</span><b>${App.esc((G.sources[s.source] || {}).label || s.source)}</b></div><hr>Click for details`;
  }

  /* --------------------------------------------------------------- snapshot */
  function setYear(y, rerender = true) {
    state.year = Math.max(2000, Math.min(2023, y));
    $("year").value = state.year; $("year-out").textContent = state.year;
    if (rerender) render(); else { drawSnapshot(); syncUrl(); }
  }

  function drawSnapshot() {
    const i = yi(state.year), list = filtered();
    const active = list.filter((s) => s.years.status[i] === "active");
    const started = list.filter((s) => s.start === state.year);
    const ended = list.filter((s) => s.end === state.year - 1);
    const core = active.filter((s) => s.layer !== "residual" && s.layer !== "L1_framework");
    const mean = core.length ? d3.mean(core, (s) => s.years.intensity[i]) : null;
    const oecd = active.filter((s) => s.years.src[i] === "capmf_derived").length;
    const bySector = d3.rollups(active, (v) => v.length, (s) => s.sector).sort((a, b) => G.sectorOrder.indexOf(a[0]) - G.sectorOrder.indexOf(b[0]));
    const maxN = Math.max(1, ...bySector.map((d) => d[1]));
    const li = (s) => `<li><span class="dot" style="background:${App.mechColor(s.mechanism)}"></span><a href="${App.policyUrl(s.slug)}">${App.esc(s.name)}</a><span class="muted small">${App.esc(s.sector)}</span></li>`;
    $("snap-body").innerHTML = `
      <div class="year-big" style="margin-top:14px">${state.year}</div>
      <div class="snap-stats">
        <div><b>${active.length}</b><span>series active</span></div>
        <div><b>${App.fmt(mean)}</b><span>mean intensity of active L2/L3 series</span></div>
        <div><b>${oecd}</b><span>with an OECD-derived value</span></div>
        <div><b>${active.length - oecd}</b><span>assumed or residual</span></div>
      </div>
      <h4>Active by sector</h4>
      <div>${bySector.map(([k, n]) => `<div style="display:grid;grid-template-columns:96px 1fr 22px;gap:8px;align-items:center;font-size:12.5px;margin:3px 0"><span>${App.esc(k)}</span><span class="bar-track" style="margin:0"><span class="bar-fill" style="display:block;width:${(n / maxN) * 100}%;background:${App.sectorColor(k)}"></span></span><b style="text-align:right">${n}</b></div>`).join("") || '<p class="muted small">None in the current filter.</p>'}</div>
      <h4>Starting in ${state.year}</h4>
      <ul>${started.map(li).join("") || '<li class="muted">No new series</li>'}</ul>
      <h4>Ended in ${state.year - 1}</h4>
      <ul>${ended.map(li).join("") || '<li class="muted">None</li>'}</ul>`;
  }

  /* --------------------------------------------------------------- summary charts */
  function drawCharts(groups) {
    const traces = [], avg = [];
    $("comp-sub").textContent = `Active series by ${state.group}: see which groups grew as new policies started.`;
    groups.forEach((g) => {
      const c = groupColor(g.key), name = groupLabel(g.key);
      const color = state.group === "layer" || state.group === "source" ? d3.schemeTableau10[groups.indexOf(g) % 10] : c;
      traces.push({ type: "scatter", mode: "lines", stackgroup: "one", name, x: YEARS,
        y: YEARS.map((_, i) => g.rows.filter((s) => s.years.status[i] === "active").length),
        line: { width: 0.8, color }, fillcolor: App.tint(color.startsWith("#") ? color : "#0B5563", 0.7), hovertemplate: `${name}: %{y}<extra></extra>` });
      avg.push({ type: "scatter", mode: "lines+markers", name, x: YEARS, marker: { size: 4 },
        y: YEARS.map((_, i) => { const a = g.rows.filter((s) => s.years.status[i] !== "pre_implementation" && val(s, i) !== null); return a.length ? d3.mean(a, (s) => val(s, i)) : null; }),
        line: { width: 2, color }, hovertemplate: `${name}: %{y:.2f}<extra></extra>`, connectgaps: false });
    });
    const shapes = [{ type: "line", x0: state.year, x1: state.year, yref: "paper", y0: 0, y1: 1, line: { color: "#C4841D", width: 1.5, dash: "dot" } }];
    Plotly.react("comp-chart", traces, App.plotLayout({ hovermode: "x unified", shapes, yaxis: { title: { text: "Active series" }, gridcolor: "#E4EAE9" }, legend: { orientation: "v", x: 1.02, y: 1, font: { size: 11 } }, margin: { l: 52, r: 120, t: 12, b: 36 } }), App.plotConfig);
    Plotly.react("avg-chart", avg, App.plotLayout({ hovermode: "x unified", shapes, yaxis: { title: { text: METRIC[state.metric].label }, gridcolor: "#E4EAE9", rangemode: "tozero" }, legend: { orientation: "v", x: 1.02, y: 1, font: { size: 11 } }, margin: { l: 52, r: 120, t: 12, b: 36 } }), App.plotConfig);
    ["comp-chart", "avg-chart"].forEach((id) => {
      const el = $(id);
      if (!el._bound) { el.on("plotly_click", (ev) => { if (ev.points && ev.points[0]) setYear(+ev.points[0].x); }); el._bound = true; }
    });
  }

  /* --------------------------------------------------------------- drawer */
  function openDrawer(s) {
    const i = yi(state.year), y = s.years;
    const siblings = DATA.filter((x) => x.id === s.id && x.slug !== s.slug);
    $("drawer-body").innerHTML = `
      <p class="small muted" style="margin:0 0 4px">${App.esc(s.id)}</p>
      <h2>${App.esc(s.name)}</h2>
      <div class="tags">
        <span class="tag"><span class="dot" style="background:${App.sectorColor(s.sector)}"></span>${App.esc(s.sector)}</span>
        <span class="tag" data-term="mechanisms.${s.mechanism}"><span class="dot" style="background:${App.mechColor(s.mechanism)}"></span>${App.esc(App.mechLabel(s.mechanism))}</span>
        <span class="tag layer" data-term="layers.${s.layer}">${App.esc(App.layerLabel(s.layer))}</span>
        <span class="tag" data-term="sources.${s.source}">${App.esc((G.sources[s.source] || {}).label || s.source)}</span>
      </div>
      <p class="small">${App.esc(s.summary)}${s.summary.length >= 260 ? "…" : ""}</p>
      <div id="drawer-chart" style="height:200px;margin:6px -6px"></div>
      <h3 style="font-size:17px;margin-top:6px">In ${state.year}: ${App.esc(App.statusLabel(y.status[i]))}</h3>
      <div class="formula">
        <div class="term-box"><b>${App.fmt(y.impl[i])}</b><span>implementation</span></div><span class="op">×</span>
        <div class="term-box"><b>${App.fmt(s.coverage)}</b><span>coverage score</span></div><span class="op">×</span>
        <div class="term-box"><b>${App.fmt(s.bindingness)}</b><span>bindingness</span></div><span class="op">=</span>
        <div class="term-box result"><b>${App.fmt(y.intensity[i])}</b><span>intensity</span></div>
      </div>
      ${s.layer === "residual" ? '<p class="note">For residual bundles the intensity is the mean of member intensities, so the three means shown do not multiply to it exactly.</p>' : ""}
      <dl class="kv">
        <dt>Active</dt><dd>${s.start}${s.end ? "–" + s.end : " onwards"}</dd>
        <dt>OECD match</dt><dd><span class="term" data-term="match.${s.match}">${App.esc((G.match[s.match] || {}).label || s.match)}</span>${s.capmfCode ? ` <code>${App.esc(s.capmfCode)}</code>` : ""}</dd>
        <dt>Why selected</dt><dd><span class="term" data-term="selection.${s.selection}">${App.esc((G.selection[s.selection] || {}).label || s.selection)}</span></dd>
        <dt>Reported saving</dt><dd>${s.effectKt === null ? "Not quantified" : App.fmtInt(s.effectKt) + " kt CO₂e/yr <span class='muted small'>(selection only)</span>"}</dd>
        ${siblings.length ? `<dt>Also in</dt><dd>${siblings.map((x) => `<a href="${App.policyUrl(x.slug)}">${App.esc(x.sector)}</a>`).join(", ")}</dd>` : ""}
      </dl>
      <a class="btn" href="${App.policyUrl(s.slug)}">Open the full policy profile</a>`;
    $("drawer").setAttribute("aria-hidden", "false");
    const lines = [
      { name: "Intensity", y: y.intensity, color: "#0B5563", width: 2.5 },
      { name: "Implementation", y: y.impl, color: App.mechColor(s.mechanism), width: 1.5, dash: "dot" },
    ];
    Plotly.newPlot("drawer-chart", lines.map((l) => ({ type: "scatter", mode: "lines", name: l.name, x: YEARS, y: l.y, line: { color: l.color, width: l.width, dash: l.dash }, hovertemplate: `${l.name}: %{y:.2f}<extra></extra>` })),
      App.plotLayout({ margin: { l: 34, r: 8, t: 8, b: 26 }, hovermode: "x unified", yaxis: { range: [0, 1.02], gridcolor: "#E4EAE9" }, legend: { orientation: "h", y: 1.18, font: { size: 11 } },
        shapes: [{ type: "line", x0: state.year, x1: state.year, yref: "paper", y0: 0, y1: 1, line: { color: "#C4841D", width: 1.5, dash: "dot" } }] }),
      { displayModeBar: false, responsive: true });
    $("drawer-close").focus();
  }
  function closeDrawer() { $("drawer").setAttribute("aria-hidden", "true"); }
})();
