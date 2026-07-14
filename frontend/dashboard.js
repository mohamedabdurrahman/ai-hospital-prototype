let edChart;
let refreshInterval = null;
let simInterval = null;
let state = { kpis: [], ed: [], beds: [], inpatients: [], forecasts: {} };

console.log("dashboard.js loaded");

const API_BASE = localStorage.getItem("API_BASE") || "";

function setApiBase() {
  const url = document.getElementById("apiBaseInput").value.trim();
  const baseUrl = url || localStorage.getItem("API_BASE") || "";
  localStorage.setItem("API_BASE", baseUrl);
  document.getElementById("currentApiBase").innerText = "API Base: " + baseUrl;
  location.reload();
}

function setConnectionStatus(connected) {
  const statusEl = document.getElementById("connectionStatus");
  if (!statusEl) return;
  statusEl.innerText = connected ? "Connected" : "Disconnected";
  statusEl.classList.toggle("disconnected", !connected);
}

function setPanelLoading(elementId, message = "Loading…") {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = `<div class="loading-state">${message}</div>`;
}

function getTrendArrow(trend) {
  if (!trend) return "→";
  const normalized = String(trend).toLowerCase();
  if (normalized.includes("up") || normalized.includes("rise") || normalized.includes("increasing")) return "↑";
  if (normalized.includes("down") || normalized.includes("fall") || normalized.includes("decreasing")) return "↓";
  return "→";
}

function getTrendLabel(trend) {
  if (!trend) return "stable";
  const normalized = String(trend).toLowerCase();
  if (normalized.includes("up") || normalized.includes("rise") || normalized.includes("increasing")) return "rising";
  if (normalized.includes("down") || normalized.includes("fall") || normalized.includes("decreasing")) return "falling";
  return normalized;
}

function getTriageBadge(triage) {
  const normalized = String(triage || "").trim().toLowerCase();
  if (normalized === "green") return '<span class="triage-green">Green</span>';
  if (normalized === "amber") return '<span class="triage-amber">Amber</span>';
  if (normalized === "red") return '<span class="triage-red">Red</span>';
  return `<span class="triage-amber">${triage || "Unknown"}</span>`;
}

function refreshDashboard() {
  renderKPITiles(state.kpis);
  renderEDPanel(state.ed, state.forecasts.ed, state.kpis);
  renderBedMap(state.beds, state.inpatients);
  renderInpatientList(state.inpatients);
  renderDischargeOpportunities(state.inpatients, state.kpis);
  renderForecastPanel(state.forecasts.ed, state.forecasts.beds);
}

function toggleSimulationMode(active) {
  document.body.classList.toggle("sim-active", Boolean(active));
}

function simulateEDQueue() {
  const next = Array.isArray(state.ed) ? [...state.ed] : [];
  const triageOptions = ["Green", "Amber", "Red"];
  if (next.length) {
    const idx = Math.floor(Math.random() * next.length);
    next[idx] = {
      ...next[idx],
      arrival_hour: Math.max(0, Math.min(23, Number(next[idx].arrival_hour || 0) + (Math.random() > 0.5 ? 1 : -1))),
      triage_category: triageOptions[Math.floor(Math.random() * triageOptions.length)]
    };
  }
  if (Math.random() > 0.7) {
    next.unshift({
      patient_id: `SIM-${Math.floor(Math.random() * 900) + 100}`,
      triage_category: triageOptions[Math.floor(Math.random() * triageOptions.length)],
      arrival_hour: Math.floor(Math.random() * 24),
      admitted: Math.random() > 0.5
    });
  }
  if (next.length > 10 && Math.random() > 0.6) next.pop();
  state.ed = next.slice(0, 10);
}

function simulateBedMap() {
  const specialties = ["general_med", "surgery", "geriatrics", "icu"];
  state.beds = Array.isArray(state.beds) && state.beds.length
    ? state.beds.map((bed) => ({
        ...bed,
        occupied: Math.random() > 0.7 ? !bed.occupied : bed.occupied,
        specialty: Math.random() > 0.8 ? specialties[Math.floor(Math.random() * specialties.length)] : bed.specialty
      }))
    : [];
}

function simulateInpatients() {
  const next = Array.isArray(state.inpatients) ? state.inpatients.map((patient) => ({
    ...patient,
    los_days: Math.max(1, Number(patient.los_days || 1) + (Math.random() > 0.5 ? 1 : -1))
  })) : [];

  if (Math.random() > 0.7) {
    next.unshift({
      admission_id: `ADM-SIM-${Math.floor(Math.random() * 900) + 100}`,
      patient_id: `P-SIM-${Math.floor(Math.random() * 900) + 100}`,
      age: Math.floor(Math.random() * 80) + 18,
      frailty_score: Number((Math.random() * 0.8 + 0.1).toFixed(2)),
      primary_diagnosis: ["Chest pain", "COPD exacerbation", "Asthma", "DVT"][Math.floor(Math.random() * 4)],
      los_days: 2
    });
  }
  if (next.length > 12 && Math.random() > 0.6) next.pop();
  state.inpatients = next.slice(0, 12);
}

function simulateKPIs() {
  const currentTrolley = Number(state.kpis.find((item) => item.name === "trolley_count_8am")?.value || 6);
  const currentDtoC = Number(state.kpis.find((item) => item.name === "dtoc_count")?.value || 4);
  const longStayCount = state.inpatients.filter((patient) => Number(patient.los_days || 0) > 14).length;
  const edPressure = state.ed.filter((item) => ["Amber", "Red"].includes(item.triage_category)).length;
  const forecastEd = Math.max(6, Number(state.forecasts.ed?.value || 18) + Math.round(Math.random() * 6) - 3);
  const forecastBeds = Math.max(2, Number(state.forecasts.beds?.value || 10) + Math.round(Math.random() * 4) - 2);

  state.kpis = [
    { name: "trolley_count_8am", value: Math.max(1, currentTrolley + (Math.random() > 0.5 ? 1 : -1)), unit: "patients", trend: "stable" },
    { name: "dtoc_count", value: Math.max(1, currentDtoC + (Math.random() > 0.5 ? 1 : -1)), unit: "patients", trend: "watch" },
    { name: "pet_24hr", value: Math.max(0, edPressure), unit: "patients", trend: "watch" },
    { name: "los_gt_14_days", value: longStayCount, unit: "patients", trend: "watch" }
  ];

  state.forecasts.ed = { ...state.forecasts.ed, value: forecastEd, label: "ed_arrivals_next_6h", unit: "patients" };
  state.forecasts.beds = { ...state.forecasts.beds, value: forecastBeds, label: "available_beds_next_24h", unit: "beds" };
}

function startSimulation() {
  stopSimulation();
  const simToggle = document.getElementById("simToggle");
  if (!simToggle || !simToggle.checked) {
    toggleSimulationMode(false);
    return;
  }

  toggleSimulationMode(true);
  simInterval = setInterval(() => {
    simulateEDQueue();
    simulateBedMap();
    simulateInpatients();
    simulateKPIs();
    refreshDashboard();
  }, 5000);
}

function stopSimulation() {
  if (simInterval) {
    clearInterval(simInterval);
    simInterval = null;
  }
  toggleSimulationMode(false);
}

async function checkConnection() {
  try {
    const res = await fetch(`${API_BASE}/kpis`);
    if (!res.ok) throw new Error("Bad response");
    setConnectionStatus(true);
  } catch (err) {
    setConnectionStatus(false);
    console.error("checkConnection error", err);
  }
}

async function loadKPIs() {
  setPanelLoading("kpi-tiles", "Loading KPI summary…");
  try {
    const kpis = await fetchKPIs();
    state.kpis = Array.isArray(kpis) ? kpis : [];
    refreshDashboard();
    setConnectionStatus(true);
  } catch (error) {
    console.error("loadKPIs error", error);
    setConnectionStatus(false);
  }
}

async function loadED() {
  setPanelLoading("ed-queue", "Loading ED queue…");
  try {
    const [ed, forecastEd] = await Promise.all([fetchED(), fetchForecastED()]);
    state.ed = Array.isArray(ed) ? ed : [];
    state.forecasts.ed = forecastEd || {};
    refreshDashboard();
    setConnectionStatus(true);
  } catch (error) {
    console.error("loadED error", error);
    setConnectionStatus(false);
  }
}

async function loadBeds() {
  setPanelLoading("bed-map", "Loading bed map…");
  try {
    const beds = await fetchBeds();
    state.beds = Array.isArray(beds) ? beds : [];
    refreshDashboard();
    setConnectionStatus(true);
  } catch (error) {
    console.error("loadBeds error", error);
    setConnectionStatus(false);
  }
}

async function loadInpatients() {
  setPanelLoading("inpatient-table-body", "Loading inpatient list…");
  try {
    const inpatients = await fetchInpatients();
    state.inpatients = Array.isArray(inpatients) ? inpatients : [];
    refreshDashboard();
    setConnectionStatus(true);
  } catch (error) {
    console.error("loadInpatients error", error);
    setConnectionStatus(false);
  }
}

async function loadForecasts() {
  try {
    const [forecastEd, forecastBeds] = await Promise.all([fetchForecastED(), fetchForecastBeds()]);
    state.forecasts.ed = forecastEd || {};
    state.forecasts.beds = forecastBeds || {};
    refreshDashboard();
    setConnectionStatus(true);
  } catch (error) {
    console.error("loadForecasts error", error);
    setConnectionStatus(false);
  }
}

function renderKPITiles(kpis) {
  const container = document.getElementById("kpi-tiles");
  if (!container) return;
  container.innerHTML = "";

  const tileConfig = [
    { name: "Trolley count", key: "trolley_count_8am" },
    { name: "DTOC count", key: "dtoc_count" },
    { name: "Patients in ED > 24 hours", key: "pet_24hr" },
    { name: "Long-stay patients (>14 days)", key: "los_gt_14_days" }
  ];

  const safeKpis = Array.isArray(kpis) ? kpis : [];
  tileConfig.forEach((tile) => {
    const metric = safeKpis.find((item) => item.name === tile.key);
    const value = metric ? Math.round(Number(metric.value)) : "—";
    const trend = metric?.trend || "stable";
    const tileElement = document.createElement("div");
    tileElement.className = "kpi-tile";
    tileElement.innerHTML = `<h3>${tile.name}</h3><div class="value">${value}</div><div class="trend-pill">${getTrendArrow(trend)} ${getTrendLabel(trend)}</div>`;
    container.appendChild(tileElement);
  });
}

function renderEDPanel(ed, forecastEd, kpis) {
  const queueEl = document.getElementById("ed-queue");
  const riskBadge = document.getElementById("ed-risk-badge");
  const chartEl = document.getElementById("ed-chart");
  if (!queueEl || !riskBadge || !chartEl) return;

  queueEl.innerHTML = "";
  const safeEd = Array.isArray(ed) ? ed : [];
  const currentQueue = safeEd.slice(0, 8);
  currentQueue.forEach((item) => {
    const row = document.createElement("div");
    row.className = "queue-item";
    row.innerHTML = `<span>${item.patient_id}</span><span>${getTriageBadge(item.triage_category)}</span><span>${item.arrival_hour}h</span>`;
    queueEl.appendChild(row);
  });

  const trolleyMetric = (Array.isArray(kpis) ? kpis : []).find((item) => item.name === "trolley_count_8am");
  const trolleyCount = Number(trolleyMetric?.value || 0);
  const forecastValue = typeof forecastEd?.value === "number" ? forecastEd.value : 0;
  const riskLevel = trolleyCount > 10 || forecastValue > 25 ? "High" : trolleyCount > 5 || forecastValue > 15 ? "Medium" : "Low";
  const riskClass = riskLevel.toLowerCase();
  riskBadge.textContent = riskLevel;
  riskBadge.className = `risk-badge ${riskClass}`;

  const ctx = chartEl.getContext("2d");
  if (edChart) edChart.destroy();

  edChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: ["Now", "+1h", "+2h", "+3h", "+4h", "+5h"],
      datasets: [{
        label: "ED Arrivals",
        data: [forecastValue, forecastValue + 2, forecastValue + 4, forecastValue + 3, forecastValue + 1, forecastValue + 2],
        borderColor: "#ff6b6b",
        backgroundColor: "rgba(255,107,107,0.2)",
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } }
    }
  });
}

function isSpecialtyMismatch(bed) {
  const specialty = String(bed.specialty || "").toLowerCase();
  const ward = String(bed.ward_id || "").toLowerCase();
  if (ward.includes("med") && !["general_med", "general medicine", "medicine"].includes(specialty)) return true;
  if (ward.includes("surg") && !["surgery", "surgical"].includes(specialty)) return true;
  if (ward.includes("ger") && !["geriatrics", "geriatric"].includes(specialty)) return true;
  if (ward.includes("icu") && !["icu", "critical_care", "critical care"].includes(specialty)) return true;
  return false;
}

function renderBedMap(beds, inpatients) {
  const container = document.getElementById("bed-map");
  if (!container) return;
  container.innerHTML = "";

  const safeBeds = Array.isArray(beds) ? beds : [];
  const safeInpatients = Array.isArray(inpatients) ? inpatients : [];
  const bedsByWard = safeBeds.reduce((acc, bed) => {
    acc[bed.ward_id] = acc[bed.ward_id] || [];
    acc[bed.ward_id].push(bed);
    return acc;
  }, {});
  const longStayCount = safeInpatients.filter((patient) => Number(patient.los_days || 0) > 14).length;

  Object.entries(bedsByWard).forEach(([wardId, wardBeds]) => {
    const occupiedCount = wardBeds.filter((bed) => bed.occupied).length;
    const occupancyPct = wardBeds.length ? Math.round((occupiedCount / wardBeds.length) * 100) : 0;
    const mismatchCount = wardBeds.filter(isSpecialtyMismatch).length;
    const pressureScore = Math.round(occupancyPct * 0.5 + longStayCount * 0.3 + mismatchCount * 0.2);
    let pressureClass = "green";
    if (pressureScore > 60) pressureClass = "red";
    else if (pressureScore >= 30) pressureClass = "amber";

    const wardCard = document.createElement("div");
    wardCard.className = "ward-card";

    wardCard.innerHTML = `
      <h3>${wardId}</h3>
      <div class="ward-metrics">
        <span>Occupancy ${occupancyPct}%</span>
        <span>Long-stay ${longStayCount}</span>
        <span>Mismatch ${mismatchCount}</span>
      </div>
      <div class="pressure-pill ${pressureClass}">Pressure score ${pressureScore}</div>
      <div class="bed-grid"></div>
    `;

    const grid = wardCard.querySelector(".bed-grid");
    wardBeds.forEach((bed) => {
      const bedEl = document.createElement("div");
      bedEl.className = `bed ${bed.occupied ? "occupied" : "free"}`;
      bedEl.textContent = bed.bed_id.split("-").pop();
      grid.appendChild(bedEl);
    });

    container.appendChild(wardCard);
  });
}

function renderInpatientList(inpatients) {
  const tbody = document.getElementById("inpatient-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  const safeInpatients = Array.isArray(inpatients) ? inpatients : [];
  safeInpatients.slice(0, 12).forEach((patient) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${patient.patient_id}</td>
      <td>${patient.age}</td>
      <td>${Number(patient.frailty_score || 0).toFixed(2)}</td>
      <td>${patient.primary_diagnosis}</td>
      <td>${patient.admission_id}</td>
      <td>${patient.los_days}d</td>
    `;
    tbody.appendChild(row);
  });
}

function renderDischargeOpportunities(inpatients, kpis) {
  const container = document.getElementById("discharge-opportunities");
  if (!container) return;
  const safeInpatients = Array.isArray(inpatients) ? inpatients : [];
  const safeKpis = Array.isArray(kpis) ? kpis : [];
  const dtocCount = safeKpis.find((item) => item.name === "dtoc_count")?.value || 0;
  const predictedToday = safeInpatients.filter((patient) => Number(patient.los_days || 0) <= 2 && Number(patient.frailty_score || 0) <= 0.3).length;
  const longStayImproving = safeInpatients.filter((patient) => Number(patient.los_days || 0) > 14 && Number(patient.frailty_score || 0) <= 0.4).length;

  const samplePatients = safeInpatients.filter((patient) => Number(patient.los_days || 0) <= 2).slice(0, 3).map((patient) => patient.patient_id).join(", ");

  container.innerHTML = `
    <div class="ward-metrics">
      <span>Predicted to discharge today: <strong>${predictedToday}</strong></span>
      <span>Medically fit but waiting (DTOC): <strong>${Math.round(Number(dtocCount))}</strong></span>
      <span>Long-stay improving frailty: <strong>${longStayImproving}</strong></span>
    </div>
    <p>Priority candidates: ${samplePatients || "No immediate candidates"}</p>
  `;
}

function renderForecastPanel(forecastEd, forecastBeds) {
  const edValue = typeof forecastEd?.value === "number" ? forecastEd.value : 0;
  const bedValue = typeof forecastBeds?.value === "number" ? forecastBeds.value : 0;

  const forecastEdEl = document.getElementById("forecast-ed");
  const forecastBedsEl = document.getElementById("forecast-beds");
  if (forecastEdEl) forecastEdEl.textContent = `${Math.round(edValue)} patients`;
  if (forecastBedsEl) forecastBedsEl.textContent = `${Math.round(bedValue)} beds`;
}

async function runAgentFromUI() {
  const button = document.getElementById("run-agent-btn");
  if (!button) return;
  button.disabled = true;
  button.textContent = "Running...";

  try {
    const result = await runAgent();
    const taskEl = document.getElementById("agent-task");
    const summaryEl = document.getElementById("agent-summary");
    const explanationEl = document.getElementById("agent-explanation");
    const confidenceEl = document.getElementById("agent-confidence");
    const actionsEl = document.getElementById("agent-actions");

    if (taskEl) taskEl.textContent = result.task || "Agent run";
    if (summaryEl) summaryEl.textContent = result.summary || "No summary";
    const explanation = result.explanation || "No explanation available";
    const confidence = Number(result.confidence || 0);
    if (explanationEl) explanationEl.textContent = explanation;

    let confidenceLabel = "Low confidence";
    let confidenceClass = "low";
    if (confidence > 0.7) {
      confidenceLabel = "High confidence";
      confidenceClass = "high";
    } else if (confidence >= 0.4) {
      confidenceLabel = "Medium confidence";
      confidenceClass = "medium";
    }
    if (confidenceEl) {
      confidenceEl.textContent = `${confidenceLabel} (${confidence.toFixed(2)})`;
      confidenceEl.className = `agent-confidence ${confidenceClass}`;
    }

    if (actionsEl) {
      actionsEl.innerHTML = "";
      (result.priority_actions || []).forEach((action) => {
        const li = document.createElement("li");
        li.textContent = action;
        actionsEl.appendChild(li);
      });
    }
  } catch (error) {
    console.error("Agent run failed", error);
  } finally {
    button.disabled = false;
    button.textContent = "Run AI Agent";
  }
}

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

function startAutoRefresh() {
  stopAutoRefresh();
  const toggle = document.getElementById("autoRefreshToggle");
  if (!toggle || !toggle.checked) return;
  refreshInterval = setInterval(() => {
    loadKPIs();
    loadED();
    loadBeds();
    loadInpatients();
    loadForecasts();
  }, 60000);
}

function attachEvents() {
  const refreshButton = document.getElementById("refresh-btn");
  const runAgentButton = document.getElementById("run-agent-btn");
  const autoRefreshToggle = document.getElementById("autoRefreshToggle");
  const simToggle = document.getElementById("simToggle");

  if (refreshButton) {
    refreshButton.addEventListener("click", () => {
      loadKPIs();
      loadED();
      loadBeds();
      loadInpatients();
      loadForecasts();
    });
  }

  if (runAgentButton) {
    runAgentButton.addEventListener("click", runAgentFromUI);
  }

  if (autoRefreshToggle) {
    autoRefreshToggle.addEventListener("change", () => {
      localStorage.setItem("AUTO_REFRESH", autoRefreshToggle.checked ? "true" : "false");
      startAutoRefresh();
    });
  }

  if (simToggle) {
    simToggle.addEventListener("change", (event) => {
      if (event.target.checked) startSimulation();
      else stopSimulation();
    });
  }
}

window.onload = () => {
  console.log("Dashboard initializing...");
  const savedAutoRefresh = localStorage.getItem("AUTO_REFRESH");
  const autoRefreshToggle = document.getElementById("autoRefreshToggle");
  const simToggle = document.getElementById("simToggle");
  if (autoRefreshToggle) {
    autoRefreshToggle.checked = savedAutoRefresh !== "false";
  }
  if (simToggle) {
    simToggle.checked = false;
  }
  const apiBaseEl = document.getElementById("currentApiBase");
  if (apiBaseEl) {
    apiBaseEl.innerText = "API Base: " + localStorage.getItem("API_BASE");
  }
  toggleSimulationMode(false);
  attachEvents();
  checkConnection();
  loadKPIs();
  loadED();
  loadBeds();
  loadInpatients();
  loadForecasts();
  startAutoRefresh();
};
