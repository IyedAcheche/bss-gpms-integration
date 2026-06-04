/* --- HUMS & critical (cached poll) --- */

const FDM_COMPACT_COLUMNS = [
  "row_index",
  "timestamp",
  "latitude",
  "longitude",
  "altitude",
  "heading",
  "ground_speed",
  "pitch",
  "roll",
  "indicated_airspeed",
];

const FDM_FULL_COLUMNS = [
  "row_index",
  "timestamp",
  "latitude",
  "longitude",
  "altitude",
  "heading",
  "ground_speed",
  "gps_latitude",
  "gps_longitude",
  "gps_altitude",
  "gps_ground_speed",
  "pitch",
  "roll",
  "pitch_rate",
  "roll_rate",
  "yaw_rate",
  "acceleration_x",
  "acceleration_y",
  "acceleration_z",
  "normalized_acceleration",
  "wander",
  "ng",
  "np",
  "nr",
  "torque",
  "mgt",
  "xot",
  "mr_speed_roc",
  "oat",
  "barometric_pressure",
  "pressure_altitude",
  "radar_altitude",
  "indicated_airspeed",
  "altitude_rate",
  "cpi",
  "wind_speed",
  "wind_direction",
];

let fdmState = {
  assetId: null,
  operationId: null,
  lastReport: null,
  rawCsv: null,
};

function statusClass(status) {
  const s = status || "normal";
  if (s === "pending") return "status-dot status-pending";
  return `status-dot status-${s}`;
}

function fmt(dt) {
  if (!dt) return "—";
  return (
    new Date(dt).toLocaleString("en-US", {
      timeZone: "UTC",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }) + " UTC"
  );
}

function fmtNum(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(4) : String(value);
}

function fmtCell(key, value) {
  if (value == null || value === "") return "—";
  if (key === "timestamp") return fmt(value);
  if (typeof value === "number") return fmtNum(value);
  return String(value);
}

function statusCell(status, metricValue) {
  const label = status || "normal";
  const metric =
    metricValue != null && metricValue !== ""
      ? ` · ${fmtNum(metricValue)}`
      : "";
  return `<span class="status-cell">
    <span class="${statusClass(status)}" title="${label}"></span>
    <span class="status-text">${label}${metric}</span>
  </span>`;
}

function columnLabel(key) {
  return key.replace(/_/g, " ");
}

async function loadCriticalEvents() {
  const res = await fetch("/api/events/critical");
  const events = await res.json();
  const section = document.getElementById("events-section");
  const list = document.getElementById("events-list");
  list.innerHTML = "";
  if (!events.length) {
    section.classList.add("hidden");
    return;
  }
  section.classList.remove("hidden");
  for (const e of events) {
    const li = document.createElement("li");
    li.textContent = `${e.tail_number || e.asset_name || e.gpms_asset_id}: ${e.metric} ${e.status}`;
    list.appendChild(li);
  }
}

async function apiErrorMessage(res) {
  const text = await res.text();
  try {
    const body = JSON.parse(text);
    const d = body.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
    return JSON.stringify(body);
  } catch {
    return text || res.statusText;
  }
}

function showApiError(message) {
  alert(message);
}

function updateFdmSelectedLabel(assetId, assetName) {
  const el = document.getElementById("fdm-selected-label");
  if (!el) return;
  if (assetId == null) {
    el.textContent = "";
    return;
  }
  const name = assetName ? ` — ${assetName}` : "";
  el.textContent = `(asset ${assetId}${name})`;
}

function syncAssetSelection(assetId) {
  setSelectedRow("hums-table", assetId, "data-gpms-asset-id");
  setSelectedRow("fdm-assets-table", assetId, "data-asset-id");
}

async function openFdmForAsset(assetId, assetName) {
  syncAssetSelection(assetId);
  updateFdmSelectedLabel(assetId, assetName);
  document.getElementById("fdm-section").scrollIntoView({
    behavior: "smooth",
    block: "block",
  });
  await selectFdmAsset(assetId);
}

async function loadMappings() {
  const res = await fetch("/api/mappings");
  if (!res.ok) {
    showApiError(await apiErrorMessage(res));
    return;
  }
  const rows = await res.json();
  const tbody = document.querySelector("#mappings-table tbody");
  tbody.innerHTML = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.gpms_asset_id}</td>
      <td><strong>${row.brazos_tail_number}</strong></td>
      <td>${row.gpms_asset_name || "—"}</td>
      <td>${row.is_active ? "yes" : "no"}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadHums() {
  const [humsRes, aircraftRes] = await Promise.all([
    fetch("/api/hums"),
    fetch("/api/fdm/aircraft"),
  ]);
  if (!humsRes.ok) {
    showApiError(await apiErrorMessage(humsRes));
    return;
  }
  const rows = await humsRes.json();
  const aircraftById = {};
  if (aircraftRes.ok) {
    for (const a of await aircraftRes.json()) {
      aircraftById[a.asset_id] = a;
    }
  }
  const tbody = document.querySelector("#hums-table tbody");
  tbody.innerHTML = "";
  for (const row of rows) {
    const extra = aircraftById[row.gpms_asset_id];
    const tr = document.createElement("tr");
    tr.setAttribute("data-gpms-asset-id", row.gpms_asset_id);
    if (String(fdmState.assetId) === String(row.gpms_asset_id)) {
      tr.classList.add("selected");
    }
    tr.innerHTML = `
      <td><strong>${row.tail_number || "—"}</strong></td>
      <td>${row.gpms_asset_id}</td>
      <td>${row.asset_name || "—"}</td>
      <td class="hums-health-col">${statusCell(row.mdstatus, row.mdmax)}</td>
      <td class="hums-health-col">${statusCell(row.rtbstatus, row.rtbhealth)}</td>
      <td>${extra ? extra.operation_count : "—"}</td>
      <td>${fmt(row.last_operation_date)}</td>
      <td>${fmt(row.polled_at)}</td>
    `;
    tr.onclick = () =>
      openFdmForAsset(
        row.gpms_asset_id,
        row.tail_number || row.asset_name || null
      );
    tbody.appendChild(tr);
  }
}

/* --- FDM explorer (DB cache) --- */

function setFdmStepVisible(step) {
  for (let n = 2; n <= 4; n += 1) {
    const el = document.getElementById(`fdm-step-${n}`);
    if (el) el.classList.toggle("hidden", n > step);
  }
}

function resetFdmFlow() {
  fdmState.assetId = null;
  fdmState.operationId = null;
  fdmState.lastReport = null;
  fdmState.rawCsv = null;
  setSelectedRow("hums-table", -1, "data-gpms-asset-id");
  setSelectedRow("fdm-assets-table", -1, "data-asset-id");
  setSelectedRow("fdm-ops-table", -1, "data-operation-id");
  updateFdmSelectedLabel(null);
  setFdmStepVisible(1);
}

function setSelectedRow(tableId, assetOrOpId, attr) {
  document.querySelectorAll(`#${tableId} tbody tr`).forEach((tr) => {
    tr.classList.toggle("selected", tr.getAttribute(attr) === String(assetOrOpId));
  });
}

async function loadFdmAssets() {
  resetFdmFlow();
  const res = await fetch("/api/fdm/aircraft");
  if (!res.ok) {
    showApiError(await apiErrorMessage(res));
    return;
  }
  const assets = await res.json();
  const tbody = document.querySelector("#fdm-assets-table tbody");
  tbody.innerHTML = "";
  if (!assets.length) {
    tbody.innerHTML =
      '<tr><td colspan="6" class="muted">No mappings — run seed or add via /api/admin/mappings</td></tr>';
    return;
  }
  for (const a of assets) {
    const tr = document.createElement("tr");
    tr.setAttribute("data-asset-id", a.asset_id);
    const md = a.hums_cached ? a.mdstatus : "pending";
    const rtb = a.hums_cached ? a.rtbstatus : "pending";
    tr.innerHTML = `
      <td><strong>${a.brazos_tail_number}</strong></td>
      <td>${a.asset_id}</td>
      <td>${a.asset_name || "—"}</td>
      <td>${statusCell(md, a.mdmax)}</td>
      <td>${statusCell(rtb, a.rtbhealth)}</td>
      <td>${a.operation_count}</td>
    `;
    tr.onclick = () =>
      openFdmForAsset(a.asset_id, a.brazos_tail_number || a.asset_name || null);
    tbody.appendChild(tr);
  }
  if (fdmState.assetId != null) {
    syncAssetSelection(fdmState.assetId);
  }
}

async function selectFdmAsset(assetId) {
  fdmState.assetId = assetId;
  fdmState.operationId = null;
  fdmState.lastReport = null;
  fdmState.rawCsv = null;
  syncAssetSelection(assetId);
  clearFdmExport();
  document.getElementById("fdm-asset-detail").textContent = "Loading asset…";
  setFdmStepVisible(2);

  const assetRes = await fetch(`/api/fdm/aircraft/${assetId}`);
  if (!assetRes.ok) {
    showApiError(await apiErrorMessage(assetRes));
    return;
  }
  const asset = await assetRes.json();
  updateFdmSelectedLabel(assetId, asset.asset_name || null);
  document.getElementById("fdm-asset-detail").textContent = JSON.stringify(
    asset,
    null,
    2
  );
  setFdmStepVisible(2);
  document.getElementById("fdm-step-2").scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });

  const opsRes = await fetch(
    `/api/fdm/aircraft/${assetId}/operations?limit=100`
  );
  const tbody = document.querySelector("#fdm-ops-table tbody");
  tbody.innerHTML = "";
  if (!opsRes.ok) {
    tbody.innerHTML = `<tr><td colspan="5">${await opsRes.text()}</td></tr>`;
    setFdmStepVisible(2);
    return;
  }
  const ops = await opsRes.json();
  if (!ops.length) {
    tbody.innerHTML =
      '<tr><td colspan="5" class="muted">No flights ingested yet — FDM poll runs on startup and every 10 minutes.</td></tr>';
    setFdmStepVisible(3);
    return;
  }
  for (const op of ops) {
    const tr = document.createElement("tr");
    tr.setAttribute("data-operation-id", op.operation_id);
    tr.innerHTML = `
      <td>${op.operation_id}</td>
      <td>${fmt(op.start_time)}</td>
      <td>${fmt(op.end_time)}</td>
      <td>${op.flight_time ?? "—"}</td>
      <td>${fmt(op.ingested_at)}</td>
    `;
    tr.onclick = () => selectFdmOperation(op.operation_id);
    tbody.appendChild(tr);
  }
  setFdmStepVisible(3);
  document.getElementById("fdm-step-3").scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });
}

async function selectFdmOperation(operationId) {
  fdmState.operationId = operationId;
  setSelectedRow("fdm-ops-table", operationId, "data-operation-id");
  setFdmStepVisible(3);
  await loadFdmExportstates();
}

function clearFdmExport() {
  document.getElementById("fdm-export-meta").textContent = "";
  document.querySelector("#fdm-export-table thead").innerHTML = "";
  document.querySelector("#fdm-export-table tbody").innerHTML = "";
  document.getElementById("fdm-export-table-wrap").classList.remove("hidden");
  document.getElementById("fdm-download-csv").classList.add("hidden");
}

async function loadFdmExportstates() {
  const { assetId, operationId } = fdmState;
  if (assetId == null || operationId == null) return;

  const limit = document.getElementById("fdm-row-limit").value;
  document.getElementById("fdm-export-meta").textContent = "Loading exportstates…";

  const [reportRes, rawRes] = await Promise.all([
    fetch(
      `/api/fdm/aircraft/${assetId}/operations/${operationId}/exportstates?row_limit=${limit}`
    ),
    fetch(
      `/api/fdm/aircraft/${assetId}/operations/${operationId}/exportstates/raw`
    ),
  ]);

  if (!reportRes.ok) {
    document.getElementById("fdm-export-meta").textContent = await reportRes.text();
    setFdmStepVisible(3);
    return;
  }
  fdmState.lastReport = await reportRes.json();
  fdmState.rawCsv = rawRes.ok ? await rawRes.text() : null;

  const dl = document.getElementById("fdm-download-csv");
  if (fdmState.rawCsv) {
    const blob = new Blob([fdmState.rawCsv], { type: "text/csv" });
    dl.href = URL.createObjectURL(blob);
    dl.download = `asset${assetId}_op${operationId}_STATES.csv`;
    dl.classList.remove("hidden");
  } else if (fdmState.lastReport?.rows?.length) {
    const cols = Object.keys(fdmState.lastReport.rows[0]);
    const csv = [cols.join(","), ...fdmState.lastReport.rows.map((r) => cols.map((c) => r[c] ?? "").join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    dl.href = URL.createObjectURL(blob);
    dl.download = `asset${assetId}_op${operationId}_STATES.csv`;
    dl.classList.remove("hidden");
  }

  document.getElementById("fdm-export-meta").textContent =
    `${fdmState.lastReport.csv_line_count} CSV lines · ${fdmState.lastReport.csv_byte_count} bytes · showing ${fdmState.lastReport.rows.length} parsed rows`;

  setFdmStepVisible(4);
  renderFdmExportView();
  document.getElementById("fdm-step-4").scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });
}

function renderFdmExportView() {
  const tableWrap = document.getElementById("fdm-export-table-wrap");
  tableWrap.classList.remove("hidden");
  if (!fdmState.lastReport?.rows?.length) {
    document.querySelector("#fdm-export-table tbody").innerHTML =
      '<tr><td colspan="99" class="muted">No rows.</td></tr>';
    return;
  }

  const full = document.getElementById("fdm-full-columns").checked;
  const columns = full
    ? FDM_FULL_COLUMNS
    : FDM_COMPACT_COLUMNS.filter((c) =>
        Object.prototype.hasOwnProperty.call(fdmState.lastReport.rows[0], c)
      );

  const thead = document.querySelector("#fdm-export-table thead");
  const tbody = document.querySelector("#fdm-export-table tbody");
  thead.innerHTML = `<tr>${columns.map((c) => `<th>${columnLabel(c)}</th>`).join("")}</tr>`;
  tbody.innerHTML = "";
  for (const row of fdmState.lastReport.rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = columns.map((c) => `<td>${fmtCell(c, row[c])}</td>`).join("");
    tbody.appendChild(tr);
  }
}

document.getElementById("load-mappings").onclick = loadMappings;
document.getElementById("load-hums").onclick = loadHums;
document.getElementById("fdm-refresh-fleets").onclick = loadFdmAssets;
document.getElementById("fdm-full-columns").onchange = renderFdmExportView;
document.getElementById("fdm-row-limit").onchange = () => {
  if (fdmState.operationId != null) loadFdmExportstates();
};
loadCriticalEvents();
loadMappings();
loadHums();
resetFdmFlow();
loadFdmAssets();
