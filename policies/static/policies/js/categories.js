(function () {
  const { G } = App;
  const $ = (id) => document.getElementById(id);
  let DATA = [], hier = "sector", chartType = "sunburst";

  App.seg($("hier"), (v) => { hier = v; ROOT = null; drawSun(); });
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
    if (document.fonts) document.fonts.ready.then(drawSun); // re-measure labels once the web font is in
    drawScatter();
    setupFormula();
  });

  /* ---------------------------------------------------------- sunburst / treemap (D3)
     Every piece of chart text is sized in em from one variable, --chart-fs, set on #sb-wrap
     by the A−/A+ buttons. Labels keep that size: if one does not fit its segment it is
     rotated, shortened or (for small categories) moved outside the ring with a leader line. */
  const TAU = 2 * Math.PI;
  const chartEl = $("sunburst");
  let ROOT = null, NODE = new Map(), focusId = "", HL = null;

  const measure = document.createElement("canvas").getContext("2d");
  const textW = (t, px, weight = 600) => {
    measure.font = `${weight} ${px}px "Public Sans", system-ui, sans-serif`;
    return measure.measureText(t).width;
  };
  const fit = (t, px, maxW, weight) => {
    if (textW(t, px, weight) <= maxW) return t;
    let n = t.length;
    while (n > 3 && textW(t.slice(0, n) + "…", px, weight) > maxW) n--;
    return n > 3 ? t.slice(0, n).trimEnd() + "…" : "";
  };
  const wrap = (t, px, maxW, maxLines) => {
    const words = t.split(/\s+/), lines = [];
    let cur = "";
    words.forEach((w) => {
      const next = cur ? cur + " " + w : w;
      if (textW(next, px) <= maxW || !cur) cur = next; else { lines.push(cur); cur = w; }
    });
    if (cur) lines.push(cur);
    if (lines.length > maxLines) { lines.length = maxLines; lines[maxLines - 1] += "…"; }
    return lines.map((l) => fit(l, px, maxW)).filter(Boolean);
  };
  /* Black or white text, whichever has the higher WCAG contrast ratio against the fill */
  const rgb = (c) => {
    if (c[0] === "#") { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
    return (c.match(/\d+/g) || [0, 0, 0]).slice(0, 3).map(Number);
  };
  const lum = (c) => {
    const [r, g, b] = rgb(c).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const inkOn = (fill) => { const L = lum(fill); return (L + 0.05) / 0.05 >= 1.05 / (L + 0.05) ? "#111" : "#fff"; };
  const haloFor = (ink) => (ink === "#fff" ? "rgba(0,0,0,.5)" : "rgba(255,255,255,.85)");

  function buildTree() {
    const [a, b] = PAIRS[hier].map((k) => DIM[k]);
    const lvl1 = d3.group(DATA, a.key);
    const kids1 = [...lvl1.keys()].sort((x, y) => a.order.indexOf(x) - a.order.indexOf(y)).map((k1) => {
      const lvl2 = d3.group(lvl1.get(k1), b.key);
      const kids2 = [...lvl2.keys()].sort((x, y) => b.order.indexOf(x) - b.order.indexOf(y)).map((k2) => {
        const id2 = `${k1}/${k2}`;
        return {
          id: id2, label: b.label(k2), color: App.tint(b.color(k2), 0.82), term: b.term(k2),
          children: lvl2.get(k2).map((s) => ({ id: `${id2}/${s.slug}`, label: s.name, color: App.tint(b.color(k2), 0.45), term: "leaf:" + s.slug, s, value: 1 })),
        };
      });
      return { id: k1, label: a.label(k1), color: a.color(k1), term: a.term(k1), children: kids2 };
    });
    ROOT = d3.hierarchy({ id: "", label: "All policy series", children: kids1 }).sum((d) => d.value || 0);
    d3.partition()(ROOT);
    NODE = new Map(ROOT.descendants().map((d) => [d.data.id, d]));
  }

  function drawSun() {
    if (!DATA.length) return;
    if (!ROOT) { buildTree(); focusId = ""; }
    const fs = fontSize();
    $("sb-wrap").style.setProperty("--chart-fs", fs + "px");
    const focus = NODE.get(focusId) || ROOT;
    chartEl.innerHTML = "";
    if (chartType === "sunburst") drawRadial(focus, fs); else drawTreemap(focus, fs);
    drawCrumbs(focus);
    $("sb-legend").innerHTML = ROOT.children.map((d) => `<button type="button" class="sb-key" data-id="${App.esc(d.data.id)}"><i style="background:${d.data.color}"></i>${App.esc(d.data.label)} <b>${d.value}</b></button>`).join("");
  }

  function drawCrumbs(focus) {
    const path = focus.ancestors().reverse();
    $("sb-crumbs").innerHTML = path.map((d, i) => (i === path.length - 1
      ? `<span aria-current="true">${App.esc(d.data.label)} (${d.value})</span>`
      : `<button type="button" data-id="${App.esc(d.data.id)}">${App.esc(d.data.label)}</button><span aria-hidden="true">›</span>`)).join("");
  }

  function select(d) {
    if (!d.height) { showLeaf(d.data.s); return; }
    zoomTo(d.data.id);
  }
  function zoomTo(id) {
    focusId = id;
    drawSun();
    const n = NODE.get(id);
    if (n && n.depth) onNode(id, n.data.term);
  }

  /* High-contrast magnified label shown on hover or keyboard focus */
  function magnifier(svg, vb) {
    const g = svg.append("g").attr("class", "sb-mag").attr("pointer-events", "none").style("display", "none");
    const rect = g.append("rect").attr("rx", 6);
    const t1 = g.append("text").attr("class", "sb-mag-title"), t2 = g.append("text").attr("class", "sb-mag-sub");
    return {
      show(d, [px, py]) {
        const fs = fontSize(), big = fs * 1.35, small = fs * 1.05, pad = fs * 0.7;
        const title = fit(d.data.label, big, vb.w - 2 * pad - 8, 700);
        const sub = d.height ? `${d.value} series` : `${d.data.s.sector}, starts ${d.data.s.start}`;
        const w = Math.max(textW(title, big, 700), textW(sub, small, 500)) + 2 * pad;
        const h = pad * 2 + big * 1.2 + small * 1.3;
        let x = px + fs, y = py - h - fs * 0.6;
        if (y < vb.y + 4) y = py + fs * 1.4;
        x = Math.max(vb.x + 4, Math.min(vb.x + vb.w - w - 4, x));
        y = Math.max(vb.y + 4, Math.min(vb.y + vb.h - h - 4, y));
        rect.attr("width", w).attr("height", h);
        t1.attr("x", pad).attr("y", pad + big * 0.95).text(title);
        t2.attr("x", pad).attr("y", pad + big * 1.2 + small * 1.05).text(sub);
        g.attr("transform", `translate(${x},${y})`).style("display", null).raise();
      },
      hide() { g.style("display", "none"); },
    };
  }

  function bindSegments(sel, on, off) {
    sel.attr("tabindex", 0).attr("role", "button")
      .attr("aria-label", (d) => `${d.data.label}: ${d.value} series. ${d.height ? "Select to zoom in" : "Select for details"}`)
      .on("mouseenter", (e, d) => on(d, e)).on("mousemove", (e, d) => on(d, e)).on("mouseleave", (e, d) => off(d))
      .on("focus", (e, d) => on(d)).on("blur", (e, d) => off(d))
      .on("click", (e, d) => select(d))
      .on("keydown", (e, d) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(d); } });
  }

  function drawRadial(focus, fs) {
    const W = Math.max(300, chartEl.clientWidth);
    const H0 = Math.round(Math.max(400, Math.min(600, W * 0.85)));
    // Outside labels sit left and right of the ring when the longest one fits there in full;
    // otherwise (narrow screens, large text) they stack in rows above and below the ring.
    const longest = d3.max(focus.children, (d) => textW(`${d.data.label} (${d.value})`, fs * 0.95)) + fs * 2.2;
    const stacked = W < 560 || longest > W * 0.28;
    const side = stacked ? fs : longest;
    const R = Math.max(90, Math.min(H0 / 2 - fs * 1.5, W / 2 - side));
    const levels = ROOT.height - focus.depth;
    // The outermost ring holds the long policy names, so it gets 1.8× the thickness of the inner rings
    const OUTER = levels > 1 ? 1.8 : 1;
    const hole = R * 0.24, ring = (R - hole) / (levels - 1 + OUTER), span = focus.x1 - focus.x0;
    const rIn = (k) => hole + Math.min(k - 1, levels - 1) * ring;
    const rOut = (k) => (k === levels ? R : hole + k * ring);
    const nodes = focus.descendants().slice(1);
    nodes.forEach((d) => {
      const k = d.depth - focus.depth;
      d.g = { a0: (d.x0 - focus.x0) / span * TAU, a1: (d.x1 - focus.x0) / span * TAU, r0: rIn(k), r1: rOut(k) };
    });
    const arc = (g, grow = 0) => d3.arc()({ startAngle: g.a0, endAngle: g.a1, innerRadius: Math.max(hole, g.r0 - grow / 2), outerRadius: g.r1 + grow });
    const mid = (d) => (d.g.a0 + d.g.a1) / 2, rmid = (d) => (d.g.r0 + d.g.r1) / 2;
    const at = (a, r) => [Math.sin(a) * r, -Math.cos(a) * r];

    // Decide each label: tangential or radial inside the segment (whichever reads closer to
    // horizontal and fits at full size), otherwise outside with a leader line for categories.
    const inside = [], outside = [];
    nodes.forEach((d) => {
      const a = mid(d), rm = rmid(d), da = d.g.a1 - d.g.a0, thick = d.g.r1 - d.g.r0;
      const text = d.data.label, full = textW(text, fs);
      const along = da >= Math.PI ? 1.6 * rm : 2 * rm * Math.sin(da / 2);
      const bow = Math.hypot(rm, full / 2) - rm; // how far the ends of straight text drift outwards
      const tanOK = along >= full + fs && bow + fs * 0.6 <= thick / 2;
      let radText = thick >= fs * 2.5 && along >= fs * 1.25 ? fit(text, fs, thick - fs * 0.8) : "";
      // A stub such as "Cros…" does not help; keep a shortened label only if most of it survives
      if (radText !== text && radText.length - 1 < 10) radText = "";
      const preferTan = Math.abs(Math.sin(a)) < 0.7;
      if (tanOK && (preferTan || radText !== text)) inside.push({ d, text, mode: "tan" });
      else if (radText) inside.push({ d, text: radText, mode: "rad" });
      else if (d.depth === focus.depth + 1) outside.push(d); // small sector in the inner ring: label outside
      // outer-ring segments that are too small keep no label; hovering shows it magnified
    });

    const edge = R + fs * 0.4, gap = fs * 1.4;
    const lab = outside.map((d) => {
      const a = mid(d);
      return { d, right: a < Math.PI, p0: at(a, rmid(d)), p1: at(a, edge), y: at(a, edge)[1] };
    });
    if (stacked) {
      // One row per label above (or below) the ring; labels nearest the centre line get the nearest rows,
      // so each vertical leader line only passes rows whose text runs away from it.
      [-1, 1].forEach((dir) => {
        lab.filter((l) => Math.sign(l.p1[1] || 1) === dir).sort((p, q) => Math.abs(p.p1[0]) - Math.abs(q.p1[0]))
          .forEach((l, i) => { l.y = dir * (R + fs * 1.6 + i * gap); });
      });
    } else [true, false].forEach((right) => {
      const s = lab.filter((l) => l.right === right).sort((p, q) => p.y - q.y);
      for (let i = 1; i < s.length; i++) s[i].y = Math.max(s[i].y, s[i - 1].y + gap);
      const over = s.length ? s[s.length - 1].y - (H0 / 2 - fs) : 0;
      if (over > 0) {
        s.forEach((l) => { l.y -= over; });
        for (let i = s.length - 2; i >= 0; i--) s[i].y = Math.min(s[i].y, s[i + 1].y - gap);
      }
    });
    const half = stacked ? R + fs : H0 / 2;
    const top = Math.min(-half, (d3.min(lab, (l) => l.y) ?? 0) - fs);
    const H = Math.max(half, (d3.max(lab, (l) => l.y) ?? 0) + fs) - top;
    const vb = { x: -W / 2, y: top, w: W, h: H };

    const svg = d3.select(chartEl).append("svg").attr("viewBox", [vb.x, vb.y, W, H]).attr("width", W).attr("height", H)
      .attr("role", "group").attr("aria-label", `Sunburst of ${focus.data.label}: ${focus.value} policy series`);
    const segs = svg.append("g").selectAll("path").data(nodes).join("path").attr("class", "sb-seg")
      .attr("d", (d) => arc(d.g)).attr("fill", (d) => d.data.color).attr("stroke", "#fff").attr("stroke-width", 1);

    const labs = svg.append("g").attr("class", "sb-labs");
    inside.forEach(({ d, text, mode }) => {
      const deg = mid(d) * 180 / Math.PI;
      const turn = mode === "tan" ? (deg < 90 || deg > 270 ? 90 : -90) : (deg < 180 ? 0 : 180);
      const ink = inkOn(d.data.color);
      labs.append("text").attr("class", "sb-lab").attr("transform", `rotate(${deg - 90}) translate(${rmid(d)},0) rotate(${turn})`)
        .attr("text-anchor", "middle").attr("dominant-baseline", "central")
        .attr("fill", ink).attr("stroke", haloFor(ink)).text(text);
    });

    const outG = svg.append("g").attr("class", "sb-out");
    lab.forEach((l) => {
      const sx = l.right ? 1 : -1, x0 = sx * (R + fs * 0.9), x1 = sx * (R + fs * 1.4);
      const px = l.p1[0], room = stacked ? Math.min(W - 8, W / 2 + Math.abs(px)) - fs : W / 2 - R - fs * 2;
      const t = fit(`${l.d.data.label} (${l.d.value})`, fs * 0.95, room) || fit(l.d.data.label, fs * 0.95, room);
      if (!t) return; // never draw a leader line without a label
      const g = outG.append("g").attr("class", "sb-out-item").datum(l.d);
      g.append("path").attr("d", stacked ? `M${l.p0}L${l.p1}L${px},${l.y}` : `M${l.p0}L${l.p1}L${x0},${l.y}L${x1},${l.y}`);
      g.append("circle").attr("cx", l.p0[0]).attr("cy", l.p0[1]).attr("r", 2.5);
      // Stacked labels run towards the centre from the top of their leader line; side labels run outwards
      g.append("text").attr("x", stacked ? px - sx * 4 : x1 + sx * 4).attr("y", l.y)
        .attr("text-anchor", stacked ? (l.right ? "end" : "start") : (l.right ? "start" : "end")).attr("dominant-baseline", "central")
        .text(t);
    });

    // Centre: current level; click to zoom out
    const c = svg.append("g").attr("class", "sb-centre" + (focus.depth ? " can-zoom" : ""));
    c.append("circle").attr("r", hole - 2);
    const cl = focus.depth ? [[fit(focus.data.label, fs, hole * 1.8), "sb-c1"], [`${focus.value} series`, "sb-c2"]]
      : [[String(focus.value), "sb-c1 sb-big"], ["series", "sb-c2"]];
    if (focus.depth) cl.push([fit("↑ Zoom out", fs * 0.85, hole * 1.8), "sb-c3"]);
    cl.forEach(([t, cls], i) => c.append("text").attr("class", cls).attr("text-anchor", "middle").attr("dominant-baseline", "central")
      .attr("y", (i - (cl.length - 1) / 2) * fs * 1.25).text(t));
    if (focus.depth) {
      const up = () => zoomTo(focus.parent.data.id);
      c.attr("tabindex", 0).attr("role", "button").attr("aria-label", `Zoom out to ${focus.parent.data.label}`)
        .on("click", up).on("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); up(); } });
    }

    const mag = magnifier(svg, vb);
    const byId = new Map();
    segs.each(function (d) { byId.set(d.data.id, this); });
    let cur = null;
    const on = (d, e) => {
      if (cur && cur !== d) off(cur);
      cur = d;
      d3.select(byId.get(d.data.id)).attr("d", arc(d.g, fs * 0.6)).attr("stroke", "#15252D").attr("stroke-width", 2).raise();
      mag.show(d, e && e.type && e.type.startsWith("mouse") ? d3.pointer(e, svg.node()) : at(mid(d), rmid(d)));
    };
    const off = (d) => {
      d3.select(byId.get(d.data.id)).attr("d", arc(d.g)).attr("stroke", "#fff").attr("stroke-width", 1);
      mag.hide(); cur = null;
    };
    bindSegments(segs, on, off);
    bindSegments(outG.selectAll(".sb-out-item"), on, off);
    HL = { on: (id) => { const d = nodes.find((n) => n.data.id === id); if (d) on(d); }, off: () => { if (cur) off(cur); } };
  }

  function drawTreemap(focus, fs) {
    const W = Math.max(300, chartEl.clientWidth), H = Math.round(Math.max(400, Math.min(600, W * 0.85)));
    const head = Math.round(fs * 1.7), pad = fs * 0.45;
    const sub = focus.copy().sum((d) => d.value || 0).sort((p, q) => q.value - p.value);
    d3.treemap().size([W, H]).round(true).paddingInner(2).paddingOuter(3).paddingTop((d) => (d === sub ? 3 : head))(sub);
    const nodes = sub.descendants().slice(1);
    const svg = d3.select(chartEl).append("svg").attr("viewBox", [0, 0, W, H]).attr("width", W).attr("height", H)
      .attr("role", "group").attr("aria-label", `Treemap of ${focus.data.label}: ${focus.value} policy series`);
    const cells = svg.append("g").selectAll("rect").data(nodes).join("rect").attr("class", "sb-seg")
      .attr("x", (d) => d.x0).attr("y", (d) => d.y0).attr("width", (d) => Math.max(0, d.x1 - d.x0)).attr("height", (d) => Math.max(0, d.y1 - d.y0))
      .attr("rx", 2).attr("fill", (d) => d.data.color).attr("stroke", "#fff").attr("stroke-width", 1);
    const labs = svg.append("g").attr("class", "sb-labs");
    nodes.forEach((d) => {
      const w = d.x1 - d.x0 - 2 * pad, h = d.y1 - d.y0, ink = inkOn(d.data.color);
      const text = (x, y, t) => labs.append("text").attr("class", "sb-lab").attr("x", x).attr("y", y).attr("dominant-baseline", "central")
        .attr("fill", ink).attr("stroke", haloFor(ink)).text(t);
      if (d.height) {
        const t = fit(`${d.data.label} (${d.value})`, fs, w);
        if (t && h >= head) text(d.x0 + pad, d.y0 + head / 2 + 1, t);
      } else if (w >= fs * 2.5 && h >= fs * 1.6) {
        wrap(d.data.label, fs, w, Math.max(1, Math.floor((h - pad) / (fs * 1.2))))
          .forEach((t, i) => text(d.x0 + pad, d.y0 + pad + fs * 0.6 + i * fs * 1.2, t));
      }
    });
    const mag = magnifier(svg, { x: 0, y: 0, w: W, h: H });
    let cur = null;
    const on = (d, e) => {
      if (cur && cur !== d) off(cur);
      cur = d;
      const el = cells.filter((n) => n === d).attr("stroke", "#15252D").attr("stroke-width", 2.5);
      if (!d.height) el.attr("x", d.x0 - 2).attr("y", d.y0 - 2).attr("width", d.x1 - d.x0 + 4).attr("height", d.y1 - d.y0 + 4).raise();
      mag.show(d, e && e.type && e.type.startsWith("mouse") ? d3.pointer(e, svg.node()) : [(d.x0 + d.x1) / 2, (d.y0 + d.y1) / 2]);
    };
    const off = (d) => {
      cells.filter((n) => n === d).attr("stroke", "#fff").attr("stroke-width", 1)
        .attr("x", d.x0).attr("y", d.y0).attr("width", Math.max(0, d.x1 - d.x0)).attr("height", Math.max(0, d.y1 - d.y0));
      mag.hide(); cur = null;
    };
    bindSegments(cells, on, off);
    HL = { on: (id) => { const d = nodes.find((n) => n.data.id === id); if (d) on(d); }, off: () => { if (cur) off(cur); } };
  }

  $("sb-crumbs").addEventListener("click", (e) => { const b = e.target.closest("button[data-id]"); if (b) zoomTo(b.dataset.id); });
  $("sb-legend").addEventListener("click", (e) => { const b = e.target.closest(".sb-key"); if (b) zoomTo(b.dataset.id); });
  ["mouseover", "focusin"].forEach((t) => $("sb-legend").addEventListener(t, (e) => { const b = e.target.closest(".sb-key"); if (b && HL) HL.on(b.dataset.id); }));
  ["mouseout", "focusout"].forEach((t) => $("sb-legend").addEventListener(t, () => { if (HL) HL.off(); }));
  let lastW = 0;
  new ResizeObserver(() => {
    const w = chartEl.clientWidth;
    if (w && Math.abs(w - lastW) > 4) { lastW = w; drawSun(); }
  }).observe(chartEl);

  function onNode(id, cd) {
    if (cd && cd.startsWith("leaf:")) { showLeaf(DATA.find((s) => s.slug === cd.slice(5))); return; }
    const parts = id.split("/");
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
