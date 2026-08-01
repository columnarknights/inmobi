const METRIC_LABELS = {
  revenue: "Revenue", fill_rate: "Fill rate", ecpm: "eCPM",
  requests: "Requests", ctr: "CTR", render_rate: "Render rate",
};
const REVENUE_FACTORS = ["requests", "fill_rate", "render_rate", "ecpm"];

function fmtNumber(v) {
  if (v === null || v === undefined) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (abs >= 1e3) return (v / 1e3).toFixed(2) + "K";
  if (abs < 1 && abs > 0) return v.toFixed(4);
  return v.toFixed(2);
}
function fmtPct(v) { return v === null || v === undefined ? "—" : (v * 100).toFixed(1) + "%"; }
function fmtSignedPct(v) { return v === null || v === undefined ? "—" : `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`; }

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function showToast(message, type) {
  const container = document.getElementById("toast-container");
  const t = document.createElement("div");
  t.className = "toast" + (type ? ` ${type}` : "");
  t.textContent = message;
  container.appendChild(t);
  setTimeout(() => {
    t.classList.add("fade-out");
    setTimeout(() => t.remove(), 200);
  }, 4000);
}

// metric_rel_delta/segment_chain/severity/confidence all come straight from
// the API now (web.py: _derive_fields) -- computed once, server-side, so this
// page and the dashboard list can't drift out of sync with each other.
function confidenceRing(pct, size) {
  size = size || 30;
  const r = size / 2 - 3, c = 2 * Math.PI * r;
  if (pct === null) {
    return `<svg class="ring" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">` +
      `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="var(--gridline)" stroke-width="3"/></svg>`;
  }
  const off = c * (1 - pct / 100);
  return `<svg class="ring" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">` +
    `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="3"/>` +
    `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="url(#chartAreaGradient)" stroke-width="3" ` +
    `stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${off}" transform="rotate(-90 ${size / 2} ${size / 2})"/>` +
    `</svg>`;
}

async function setupFollowupButtons(id, metricLabel, data) {
  const buttons = [document.getElementById("followup-btn-top"), document.getElementById("followup-btn-bottom")];
  try {
    const meta = await (await fetch("/api/meta")).json();
    if (!meta.librechat_followup_agent_id) return; // not configured; leave hidden
    const prompt =
      `Let's discuss incident ${id} (${metricLabel}, ${data.current_window[0]} to ${data.current_window[1]}). ` +
      `Call get_investigation('${id}') first, then help me understand it further.`;
    buttons.forEach((btn) => {
      btn.style.display = "";
      btn.addEventListener("click", () => {
        const url = new URL("/c/new", meta.librechat_base_url);
        url.searchParams.set("agent_id", meta.librechat_followup_agent_id);
        url.searchParams.set("prompt", prompt);
        url.searchParams.set("submit", "true");
        window.open(url.toString(), "_blank", "noopener");
      });
    });
  } catch (e) {
    console.error("Follow-up button setup failed:", e);
    showToast("Couldn't set up follow-up chat: " + e.message, "error");
  }
}

function setupLangfuseButton(data) {
  const btn = document.getElementById("langfuse-btn");
  if (!data.langfuse_trace_url) return;
  btn.style.display = "";
  btn.addEventListener("click", () => window.open(data.langfuse_trace_url, "_blank", "noopener"));
}

function setupDownloadButton(data) {
  document.getElementById("download-btn").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.id}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showToast("Downloaded " + a.download, "success");
  });
}

function setupExportButton() {
  document.getElementById("export-btn").addEventListener("click", () => window.print());
}

async function main() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");
  if (!id) { document.getElementById("title").textContent = "No incident id given"; return; }

  const res = await fetch(`/api/incidents/${encodeURIComponent(id)}`);
  if (!res.ok) { document.getElementById("title").textContent = "Not found"; return; }
  const data = await res.json();

  const metricLabel = METRIC_LABELS[data.metric] || data.metric;
  const relDelta = data.metric_rel_delta;
  const sev = data.severity;
  const chain = data.segment_chain || [];
  const conf = data.confidence;

  document.title = `${metricLabel} ${data.current_window[0]}..${data.current_window[1]} — Incident`;
  document.getElementById("title").textContent = `${metricLabel} ${relDelta >= 0 ? "Spike" : "Drop"}`;

  const sevBadge = document.getElementById("sevBadge");
  sevBadge.style.display = "";
  sevBadge.className = "sev-badge " + sev;
  sevBadge.textContent = (sev === "high" ? "🔴 " : sev === "medium" ? "🟡 " : "🟢 ") + sev.toUpperCase();

  document.getElementById("dateLabel").textContent =
    data.current_window[0] === data.current_window[1] ? data.current_window[0] : `${data.current_window[0]} .. ${data.current_window[1]}`;
  const confWrap = document.getElementById("confWrap");
  confWrap.innerHTML = conf === null
    ? `${confidenceRing(null, 22)}<span style="color:var(--text-muted);">Broad-based — no single localized cause</span>`
    : `${confidenceRing(conf, 22)}Confidence <b>${conf}%</b>`;

  document.getElementById("impactLabel").textContent = `${metricLabel} Impact`.toUpperCase();
  const impactValue = document.getElementById("impactValue");
  impactValue.textContent = fmtSignedPct(relDelta);
  impactValue.className = "impact-value " + (relDelta >= 0 ? "up" : "down");

  const narrativeEl = document.getElementById("narrative");
  narrativeEl.textContent = data.narrative;
  const links = el("div", "trace-links");
  if (data.langfuse_trace_url) {
    const a = el("a", null, "View Langfuse trace ->");
    a.href = data.langfuse_trace_url; a.target = "_blank"; a.rel = "noopener";
    links.appendChild(a);
  }
  if (data.local_trace_path) {
    links.appendChild(el("span", null, `Local trace: ${data.local_trace_path}`));
  }
  narrativeEl.appendChild(links);

  setupFollowupButtons(data.id, metricLabel, data);
  setupLangfuseButton(data);
  setupDownloadButton(data);
  setupExportButton();

  renderPath(data, metricLabel, chain);
  renderFactors(data.decomposition);
  renderEvidence(data, metricLabel, chain);
  renderDrillTree(document.getElementById("drill-tree"), data.drill_down, 0);
  renderStepper();
}

// ---------------- Investigation Path + Why panel ----------------

function buildPathNodes(data, metricLabel, chain) {
  const nodes = [{ kind: "metric", label: metricLabel }];
  if (data.drill_factor && data.drill_factor !== data.metric) {
    nodes.push({ kind: "factor", label: METRIC_LABELS[data.drill_factor] || data.drill_factor, factor: data.drill_factor });
  }
  chain.forEach((seg, i) => {
    nodes.push({ kind: "segment", label: `${seg.dimension} = ${seg.value}`, segment: seg, levelIndex: i });
  });
  return nodes;
}

function renderPath(data, metricLabel, chain) {
  const nodes = buildPathNodes(data, metricLabel, chain);
  const defaultActive = nodes.length - 1; // lead with the deepest finding
  const wrap = document.getElementById("detPath");

  function paint(activeIndex) {
    wrap.innerHTML = "";
    nodes.forEach((node, i) => {
      if (i > 0) wrap.appendChild(el("div", "path-connector"));
      const n = el("div", "path-node" + (i === activeIndex ? " active" : ""), node.label);
      n.tabIndex = 0;
      n.addEventListener("click", () => { paint(i); renderWhy(data, metricLabel, chain, nodes, i); });
      wrap.appendChild(n);
    });
  }
  paint(defaultActive);
  renderWhy(data, metricLabel, chain, nodes, defaultActive);
}

function renderWhy(data, metricLabel, chain, nodes, index) {
  const node = nodes[index];
  const decomp = data.decomposition;
  document.getElementById("whyTitle").textContent = `📌 Why ${node.label}?`;
  const statsEl = document.getElementById("whyStats");
  const reasonsEl = document.getElementById("whyReasons");
  let stats = [], reasons = [];

  if (node.kind === "metric") {
    const b = decomp.baseline_factors[data.metric], c = decomp.current_factors[data.metric];
    const rel = data.metric_rel_delta;
    stats = [
      [`Baseline ${metricLabel}`, fmtNumber(b)],
      [`Current ${metricLabel}`, fmtNumber(c)],
      ["Deviation", fmtSignedPct(rel)],
    ];
    reasons = [
      "Fell outside the like-for-like baseline for this window, which is what triggers an automatic investigation.",
      data.drill_factor !== data.metric
        ? "Decomposed via LMDI into requests, fill rate, render rate, and eCPM to find which factor drove it."
        : "Investigated directly, since it isn't one of the revenue identity's four factors.",
    ];
  } else if (node.kind === "factor") {
    const contributions = decomp.factor_contributions_to_revenue_delta || {};
    const relDeltas = decomp.factor_rel_deltas || {};
    const revenueDelta = decomp.revenue_delta || 1;
    // Divide by |revenueDelta|, not revenueDelta -- otherwise a negative total
    // delta flips every factor's sign, showing a factor that pushed revenue
    // *up* as a negative percentage (and vice versa).
    const pctOfTotal = (contributions[node.factor] || 0) / Math.abs(revenueDelta);
    stats = [
      ["LMDI Contribution", fmtSignedPct(pctOfTotal)],
      ["Revenue Change", fmtSignedPct(decomp.revenue_rel_delta)],
      [`${node.label} Change`, fmtSignedPct(relDeltas[node.factor])],
    ];
    const sortedByAbsContrib = REVENUE_FACTORS.slice().sort((a, b) => Math.abs(contributions[b] || 0) - Math.abs(contributions[a] || 0));
    reasons.push(sortedByAbsContrib[0] === node.factor
      ? "Largest contributor to the revenue movement, by LMDI decomposition."
      : "One of the factors LMDI attributed part of the revenue movement to.");
    const others = REVENUE_FACTORS.filter((f) => f !== node.factor);
    const smallMovers = others.filter((f) => Math.abs(relDeltas[f] || 0) < 0.01).map((f) => METRIC_LABELS[f] || f);
    if (smallMovers.length) reasons.push(`${smallMovers.join(" and ")} moved less than 1% and weren't significant drivers.`);
    const revRel = decomp.revenue_rel_delta, facRel = relDeltas[node.factor];
    if (revRel !== undefined && facRel !== undefined) {
      const close = Math.abs(Math.abs(facRel) - Math.abs(revRel)) < 0.03;
      reasons.push(`${node.label} moved ${fmtSignedPct(facRel)}, ${close ? "closely tracking" : "diverging from"} revenue's overall ${fmtSignedPct(revRel)} move.`);
    }
  } else {
    const seg = node.segment;
    stats = [
      ["Explanatory Power", seg.explanatory_power],
      ["Lift", `${seg.lift.toFixed(2)}×`],
      ["Rate (baseline → current)", `${fmtNumber(seg.rate_baseline)} → ${fmtNumber(seg.rate_current)}`],
    ];
    const level = levelAtDepth(data.drill_down, node.levelIndex);
    const dims = (level && level.dimensions_checked) || {};
    const totalChecked = Object.values(dims).reduce((n, d) => n + (d.top_segments || []).length, 0);
    // Every segment in a segment_chain already cleared the pipeline's lift
    // bar server-side to be named `primary_segment` (attribution.py's
    // lift_thresh) -- so this is always "far more than", never the other
    // branch. Phrased as a plain statement rather than re-testing a threshold
    // that's already been applied.
    reasons = [
      `${seg.value} explains ${fmtPct(seg.explanatory_power)} of the movement at this level.`,
      `Lift of ${seg.lift.toFixed(1)}× — far more than its size would predict.`,
      `${totalChecked} segment(s) across ${Object.keys(dims).length} dimension(s) were checked at this level.`,
    ];
  }

  statsEl.innerHTML = stats.map(([label, value]) =>
    `<div class="why-stat"><div class="label">${label}</div><div class="value">${value}</div></div>`
  ).join("");
  reasonsEl.innerHTML = reasons.map((r) => `<li>${r}</li>`).join("");
}

function levelAtDepth(drillDown, depth) {
  let level = drillDown;
  for (let i = 0; i < depth; i++) { if (!level) return null; level = level.deeper; }
  return level;
}

// ---------------- Contribution breakdown ----------------

function renderFactors(decomp) {
  const grid = document.getElementById("factor-grid");
  grid.innerHTML = "";
  const contributions = decomp.factor_contributions_to_revenue_delta || {};
  const revenueDelta = decomp.revenue_delta || 1;
  const maxAbs = Math.max(...REVENUE_FACTORS.map((f) => Math.abs(contributions[f] || 0)), 1e-9);

  REVENUE_FACTORS.forEach((f) => {
    const contrib = contributions[f] || 0;
    // |revenueDelta|, not revenueDelta: see the comment in renderWhy() -- same flip.
    const pctOfTotal = contrib / Math.abs(revenueDelta);
    const cls = contrib >= 0 ? "up" : "down";
    const row = el("div", "contrib-row");
    row.appendChild(el("div", "contrib-label", (METRIC_LABELS[f] || f).toLowerCase()));
    const track = el("div", "contrib-track");
    const fill = el("div", `contrib-fill ${cls}`);
    fill.style.width = `${(Math.abs(contrib) / maxAbs) * 100}%`;
    track.appendChild(fill);
    row.appendChild(track);
    row.appendChild(el("div", `contrib-value ${cls}`, fmtSignedPct(pctOfTotal)));
    grid.appendChild(row);
  });
}

// ---------------- Supporting evidence ----------------

function renderEvidence(data, metricLabel, chain) {
  const decomp = data.decomposition;
  const rows = [];
  rows.push([metricLabel, decomp.baseline_factors[data.metric], decomp.current_factors[data.metric], data.metric_rel_delta]);

  if (data.drill_factor && data.drill_factor !== data.metric) {
    const fLabel = METRIC_LABELS[data.drill_factor] || data.drill_factor;
    rows.push([fLabel, decomp.baseline_factors[data.drill_factor], decomp.current_factors[data.drill_factor], (decomp.factor_rel_deltas || {})[data.drill_factor]]);
  }
  if (chain.length) {
    const seg = chain[chain.length - 1];
    const segRel = seg.rate_baseline ? (seg.rate_current - seg.rate_baseline) / seg.rate_baseline : null;
    rows.push([`${seg.dimension} = ${seg.value}`, seg.rate_baseline, seg.rate_current, segRel]);
  }

  const grid = document.getElementById("detEvidence");
  grid.innerHTML = rows.map(([label, baseline, current, rel]) => {
    const neg = rel !== null && rel !== undefined && rel < 0;
    return `<div class="evidence-card">` +
      `<div class="evidence-metric">${label}</div>` +
      `<div class="evidence-row"><span>Baseline</span><span>${fmtNumber(baseline)}</span></div>` +
      `<div class="evidence-row"><span>Current</span><span>${fmtNumber(current)}</span></div>` +
      `<div class="evidence-row diff"><span>Difference</span><span class="${neg ? "neg" : "pos"}">${fmtSignedPct(rel)}</span></div>` +
      `</div>`;
  }).join("");
}

// ---------------- Full evidence (collapsed per-dimension tables) ----------------

function renderDrillTree(container, level, depth) {
  if (!level) return;
  const wrap = el("div", "drill-level" + (depth > 0 ? " nested" : ""));

  if (level.filters && level.filters.length) {
    const f = el("div", "dim-name", "Within: " + level.filters.map((x) => `${x.dimension}=${x.value}`).join(", "));
    wrap.appendChild(f);
  }

  const dims = level.dimensions_checked || {};
  const dimNames = Object.keys(dims);
  const totalSegments = dimNames.reduce((n, d) => n + (dims[d].top_segments || []).length, 0);

  const details = document.createElement("details");
  details.className = "evidence-details";
  const summary = document.createElement("summary");
  summary.textContent = level.primary_segment
    ? `Show full evidence at this level (${dimNames.length} dimensions, ${totalSegments} segments checked)`
    : `Show what was checked (${dimNames.length} dimensions, ${totalSegments} segments — none stood out)`;
  details.appendChild(summary);

  dimNames.forEach((dimName) => {
    const info = dims[dimName];
    const block = el("div", "dim-block");
    block.appendChild(el("div", "dim-name",
      `${dimName} (${info.n_segments_checked} segments checked, ${info.n_excluded_low_volume} excluded as low-volume)`));
    const table = document.createElement("table");
    table.className = "seg-table";
    const thead = document.createElement("thead");
    thead.innerHTML = "<tr><th>Status</th><th>Value</th><th>Rate (base → current)</th><th>Volume share</th><th>Explanatory power</th><th>Lift</th></tr>";
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    (info.top_segments || []).forEach((s) => {
      const isPrimary = level.primary_segment && s.value === level.primary_segment.value && dimName === level.primary_segment.dimension;
      const tr = document.createElement("tr");
      tr.className = isPrimary ? "primary-row" : (s.ruled_out ? "ruled-out" : "");

      const statusTd = document.createElement("td");
      statusTd.textContent = isPrimary ? "🔴 Localized cause" : (s.ruled_out ? "Ruled out" : "Notable, not primary");
      tr.appendChild(statusTd);

      const cells = [
        s.value,
        `${fmtNumber(s.rate_baseline)} → ${fmtNumber(s.rate_current)}`,
        fmtPct(s.volume_share_current),
        s.explanatory_power,
        s.lift,
      ];
      cells.forEach((c, i) => {
        const td = document.createElement("td");
        td.textContent = c;
        if (i === 4 && Math.abs(s.lift) >= 1.8) td.className = "lift-cell hot";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    block.appendChild(table);
    details.appendChild(block);
  });

  wrap.appendChild(details);
  container.appendChild(wrap);

  if (level.deeper) {
    renderDrillTree(container, level.deeper, depth + 1);
  }
}

// ---------------- Pipeline stepper ----------------

function renderStepper() {
  const steps = ["Baseline Comparison", "LMDI Decomposition", "Root Cause Localization", "AI Report Generation"];
  const checkIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';
  const wrap = document.getElementById("detStepper");
  wrap.innerHTML = "";
  steps.forEach((label, i) => {
    if (i > 0) wrap.appendChild(el("div", "step-line"));
    const step = el("div", "step");
    step.innerHTML = `<div class="step-dot">${checkIcon}</div><div class="step-label">${label}</div>`;
    wrap.appendChild(step);
  });
}

main().catch((e) => {
  document.getElementById("title").textContent = "Failed to load";
  console.error(e);
  showToast("Failed to load investigation: " + e.message, "error");
});
