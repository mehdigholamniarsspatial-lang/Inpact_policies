(function () {
  const { G } = App;
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const F = ["sector", "mechanism", "layer", "source", "match", "status"];
  let DATA = [], sortKey = "sector", sortDir = 1;

  const opts = {
    sector: () => G.sectorOrder.map((k) => [k, k]),
    mechanism: () => G.mechanismOrder.map((k) => [k, App.mechLabel(k)]),
    layer: () => G.layerOrder.map((k) => [k, App.layerLabel(k)]),
    source: () => Object.entries(G.sources).map(([k, v]) => [k, v.label]),
    match: () => Object.entries(G.match).map(([k, v]) => [k, v.label]),
  };
  Object.entries(opts).forEach(([f, fn]) => {
    $("f-" + f).insertAdjacentHTML("beforeend", fn().map(([v, l]) => `<option value="${App.esc(v)}">${App.esc(l)}</option>`).join(""));
  });
  F.forEach((f) => { if (params.get(f)) $("f-" + f).value = params.get(f); $("f-" + f).addEventListener("change", render); });
  $("q").value = params.get("q") || "";
  $("q").addEventListener("input", render);
  $("reset").addEventListener("click", () => { F.forEach((f) => ($("f-" + f).value = "")); $("q").value = ""; render(); });
  document.querySelectorAll("th.sortable").forEach((th) => th.addEventListener("click", () => {
    const k = th.dataset.k; sortDir = sortKey === k ? -sortDir : (["i2023", "effectKt"].includes(k) ? -1 : 1); sortKey = k; render();
  }));

  App.getJSON(window.URLS.series).then((d) => { DATA = d.series; render(); });

  const orderIdx = { sector: G.sectorOrder, mechanism: G.mechanismOrder, layer: G.layerOrder, match: ["exact", "close", "partial", "none"] };
  function cmp(a, b) {
    let x = a[sortKey], y = b[sortKey];
    if (orderIdx[sortKey]) { x = orderIdx[sortKey].indexOf(x); y = orderIdx[sortKey].indexOf(y); }
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    const r = typeof x === "string" ? x.localeCompare(y) : x - y;
    return r * sortDir || a.start - b.start;
  }

  function render() {
    if (!DATA.length) return;
    const q = $("q").value.trim().toLowerCase();
    const v = Object.fromEntries(F.map((f) => [f, $("f-" + f).value]));
    const rows = DATA.filter((s) =>
      (!v.sector || s.sector === v.sector) && (!v.mechanism || s.mechanism === v.mechanism) && (!v.layer || s.layer === v.layer) &&
      (!v.source || s.source === v.source) && (!v.match || s.match === v.match) && (!v.status || s.years.status[23] === v.status) &&
      (!q || `${s.name} ${s.id} ${s.capmfCode} ${s.bundle}`.toLowerCase().includes(q))).sort(cmp);

    document.querySelectorAll("th.sortable").forEach((th) => th.setAttribute("aria-sort", th.dataset.k === sortKey ? (sortDir > 0 ? "ascending" : "descending") : "none"));
    const ids = new Set(rows.map((s) => s.id));
    $("count").textContent = `${rows.length} series from ${ids.size} policies shown, out of ${DATA.length}.`;
    $("tbl").tBodies[0].innerHTML = rows.length ? rows.map((s) => `<tr>
        <td><a class="pname" href="${App.policyUrl(s.slug)}">${App.esc(s.name)}</a><div class="small muted">${App.esc(s.id)}</div></td>
        <td><span class="tag"><span class="dot" style="background:${App.sectorColor(s.sector)}"></span>${App.esc(s.sector)}</span></td>
        <td><span class="tag" data-term="mechanisms.${s.mechanism}"><span class="dot" style="background:${App.mechColor(s.mechanism)}"></span>${App.esc(App.mechLabel(s.mechanism))}</span></td>
        <td><span class="tag layer" data-term="layers.${s.layer}">${App.esc(App.layerLabel(s.layer))}</span></td>
        <td style="white-space:nowrap">${s.start}${s.end ? "–" + s.end : "–"}</td>
        <td><span class="term" data-term="match.${s.match}">${App.esc((G.match[s.match] || {}).label || s.match)}</span></td>
        <td>${App.spark(s.years.intensity, App.mechColor(s.mechanism), 130, 26, 0.5)}</td>
        <td class="num">${App.fmt(s.i2023)}</td>
        <td class="num">${s.effectKt === null ? '<span class="muted">–</span>' : App.fmtInt(s.effectKt)}</td></tr>`).join("")
      : '<tr><td colspan="9" class="empty">No policies match. Clear a filter or change the search.</td></tr>';

    const p = new URLSearchParams();
    F.forEach((f) => v[f] && p.set(f, v[f])); if (q) p.set("q", q);
    history.replaceState(null, "", "?" + p.toString());
    const e = new URLSearchParams();
    const all = rows.length === DATA.length;
    if (!all) [...ids].forEach((id) => e.append("policy_id", id));
    if (!all && v.sector) e.set("sector", v.sector);
    $("export").href = window.URLS.exportCsv + (e.toString() ? "?" + e : "");
  }
})();
