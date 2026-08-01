const METRIC_LABELS = {
  revenue: "Revenue", fill_rate: "Fill rate", ecpm: "eCPM",
  requests: "Requests", ctr: "CTR", render_rate: "Render rate",
};

function fmtNumber(v) {
  if (v === null || v === undefined) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (abs >= 1e3) return (v / 1e3).toFixed(2) + "K";
  if (abs < 1 && abs > 0) return v.toFixed(4);
  return v.toFixed(2);
}
function fmtPct(v) { return v === null || v === undefined ? "—" : (v * 100).toFixed(1) + "%"; }

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

async function setupFollowupButton(id, metricLabel, data) {
  const btn = document.getElementById("followup-btn");
  try {
    const meta = await (await fetch("/api/meta")).json();
    if (!meta.librechat_followup_agent_id) return; // not configured; leave hidden
    btn.style.display = "";
    btn.addEventListener("click", () => {
      const prompt =
        `Let's discuss incident ${id} (${metricLabel}, ${data.current_window[0]} to ${data.current_window[1]}). ` +
        `Call get_investigation('${id}') first, then help me understand it further.`;
      const url = new URL("/c/new", meta.librechat_base_url);
      url.searchParams.set("agent_id", meta.librechat_followup_agent_id);
      url.searchParams.set("prompt", prompt);
      url.searchParams.set("submit", "true");
      window.open(url.toString(), "_blank", "noopener");
    });
  } catch (e) {
    console.error("Follow-up button setup failed:", e);
  }
}

async function main() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");
  if (!id) { document.getElementById("title").textContent = "No incident id given"; return; }

  const res = await fetch(`/api/incidents/${encodeURIComponent(id)}`);
  if (!res.ok) { document.getElementById("title").textContent = "Not found"; return; }
  const data = await res.json();

  const metricLabel = METRIC_LABELS[data.metric] || data.metric;
  document.title = `${metricLabel} ${data.current_window[0]}..${data.current_window[1]} — Incident`;
  document.getElementById("title").textContent = `${metricLabel}: ${data.current_window[0]} .. ${data.current_window[1]}`;
  document.getElementById("sub").textContent =
    `Baseline window: ${data.baseline_window[0]} .. ${data.baseline_window[1]} · drill factor: ${data.drill_factor}`;

  const narrativeEl = document.getElementById("narrative");
  narrativeEl.textContent = data.narrative;
  const links = el("div", "trace-links");
  if (data.langfuse_trace_url) {
    const a = el("a", null, "View Langfuse trace ->");
    a.href = data.langfuse_trace_url; a.target = "_blank"; a.rel = "noopener";
    links.appendChild(a);
  }

  // data.id is the clean investigation id (no .json suffix) matching the
  // ClickHouse `investigations` table's primary key — the URL's own `id`
  // param is the out/*.json filename, which get_investigation() won't match.
  setupFollowupButton(data.id, metricLabel, data);
  if (data.local_trace_path) {
    links.appendChild(el("span", null, `Local trace: ${data.local_trace_path}`));
  }
  narrativeEl.appendChild(links);

  renderFactors(data.decomposition);
  renderDrillTree(document.getElementById("drill-tree"), data.drill_down, 0);
}

function renderFactors(decomp) {
  const grid = document.getElementById("factor-grid");
  grid.innerHTML = "";
  const factors = ["requests", "fill_rate", "render_rate", "ecpm"];
  const contributions = decomp.factor_contributions_to_revenue_delta || {};
  const maxAbs = Math.max(...factors.map((f) => Math.abs(contributions[f] || 0)), 1e-9);

  factors.forEach((f) => {
    const bf = decomp.baseline_factors?.[f];
    const cf = decomp.current_factors?.[f];
    const contrib = contributions[f] || 0;
    const tile = el("div", "factor-tile");
    tile.appendChild(el("div", "label", f.replace("_", " ")));
    tile.appendChild(el("div", "value", `${fmtNumber(bf)} → ${fmtNumber(cf)}`));
    const sub = el("div", "delta " + (contrib >= 0 ? "up" : "down"),
      `${contrib >= 0 ? "+" : ""}${fmtNumber(contrib)} to revenue delta`);
    tile.appendChild(sub);
    const track = el("div", "bar-track");
    const fill = el("div", "bar-fill");
    fill.style.width = `${(Math.abs(contrib) / maxAbs) * 100}%`;
    fill.style.background = contrib >= 0 ? "var(--good)" : "var(--critical)";
    track.appendChild(fill);
    tile.appendChild(track);
    grid.appendChild(tile);
  });

  const summary = el("div", "factor-tile");
  summary.appendChild(el("div", "label", "revenue delta"));
  summary.appendChild(el("div", "value", `${fmtNumber(decomp.revenue_delta)} (${fmtPct(decomp.revenue_rel_delta)})`));
  grid.appendChild(summary);
}

function renderDrillTree(container, level, depth) {
  if (!level) return;
  const wrap = el("div", "drill-level" + (depth > 0 ? " nested" : ""));

  if (level.filters && level.filters.length) {
    const f = el("div", "dim-name", "Within: " + level.filters.map((x) => `${x.dimension}=${x.value}`).join(", "));
    wrap.appendChild(f);
  }

  if (level.primary_segment) {
    const p = level.primary_segment;
    const banner = el("div", "narrative-snippet",
      `Localized cause at this level: ${p.dimension}=${p.value} (explanatory power ${p.explanatory_power}, lift ${p.lift}×)`);
    banner.style.fontWeight = "600";
    banner.style.color = "var(--critical)";
    banner.style.marginBottom = "10px";
    wrap.appendChild(banner);
  } else {
    const banner = el("div", "narrative-snippet", "No single segment disproportionately explains this level — movement looks broad-based/proportional.");
    banner.style.marginBottom = "10px";
    wrap.appendChild(banner);
  }

  const dims = level.dimensions_checked || {};
  Object.keys(dims).forEach((dimName) => {
    const info = dims[dimName];
    const block = el("div", "dim-block");
    block.appendChild(el("div", "dim-name",
      `${dimName} (${info.n_segments_checked} segments checked, ${info.n_excluded_low_volume} excluded as low-volume)`));
    const table = document.createElement("table");
    table.className = "seg-table";
    const thead = document.createElement("thead");
    thead.innerHTML = "<tr><th>Value</th><th>Explanatory power</th><th>Lift</th><th>Volume share</th><th>Rate (base → current)</th><th>Status</th></tr>";
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    (info.top_segments || []).forEach((s) => {
      const tr = document.createElement("tr");
      tr.className = (level.primary_segment && s.value === level.primary_segment.value && dimName === level.primary_segment.dimension)
        ? "primary-row" : (s.ruled_out ? "ruled-out" : "");
      const cells = [
        s.value,
        s.explanatory_power,
        s.lift,
        fmtPct(s.volume_share_current),
        `${fmtNumber(s.rate_baseline)} → ${fmtNumber(s.rate_current)}`,
        s.ruled_out ? "ruled out" : "significant",
      ];
      cells.forEach((c, i) => {
        const td = document.createElement("td");
        td.textContent = c;
        if (i === 2 && Math.abs(s.lift) >= 1.8) td.className = "lift-cell hot";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    block.appendChild(table);
    wrap.appendChild(block);
  });

  container.appendChild(wrap);

  if (level.deeper) {
    renderDrillTree(container, level.deeper, depth + 1);
  }
}

main().catch((e) => {
  document.getElementById("title").textContent = "Failed to load";
  document.getElementById("sub").textContent = e.message;
});
