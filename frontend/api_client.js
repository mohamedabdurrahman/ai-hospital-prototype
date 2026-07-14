console.log("api_client.js loaded");

const API_BASE = (localStorage.getItem("api_base") || "http://127.0.0.1:8000/ui").trim().replace(/\/$/, "");
localStorage.setItem("api_base", API_BASE);

async function fetchBeds() {
  try {
    const response = await fetch(`${API_BASE}/beds`);
    if (!response.ok) throw new Error("Failed to fetch beds");
    return await response.json();
  } catch (error) {
    console.error("fetchBeds error", error);
    return [];
  }
}

async function fetchED() {
  try {
    const response = await fetch(`${API_BASE}/ed`);
    if (!response.ok) throw new Error("Failed to fetch ED data");
    return await response.json();
  } catch (error) {
    console.error("fetchED error", error);
    return [];
  }
}

async function fetchInpatients() {
  try {
    const response = await fetch(`${API_BASE}/inpatients`);
    if (!response.ok) throw new Error("Failed to fetch inpatients");
    return await response.json();
  } catch (error) {
    console.error("fetchInpatients error", error);
    return [];
  }
}

async function fetchForecastED() {
  try {
    const response = await fetch(`${API_BASE}/forecast/ed`);
    if (!response.ok) throw new Error("Failed to fetch ED forecast");
    return await response.json();
  } catch (error) {
    console.error("fetchForecastED error", error);
    return {};
  }
}

async function fetchForecastBeds() {
  try {
    const response = await fetch(`${API_BASE}/forecast/beds`);
    if (!response.ok) throw new Error("Failed to fetch bed forecast");
    return await response.json();
  } catch (error) {
    console.error("fetchForecastBeds error", error);
    return {};
  }
}

async function fetchKPIs() {
  try {
    const response = await fetch(`${API_BASE}/kpis`);
    if (!response.ok) throw new Error("Failed to fetch KPIs");
    return await response.json();
  } catch (error) {
    console.error("fetchKPIs error", error);
    return [];
  }
}

async function runAgent() {
  try {
    const response = await fetch(`${API_BASE}/run_agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    if (!response.ok) throw new Error("Failed to run agent");
    return await response.json();
  } catch (error) {
    console.error("runAgent error", error);
    return {
      task: "Agent unavailable",
      summary: "Unable to run agent",
      priority_actions: []
    };
  }
}
