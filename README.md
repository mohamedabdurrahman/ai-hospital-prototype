
# **Decision Advantage — IPCI Hospital Operations Intelligence Platform**

## **Reducing decision latency. Optimising Patient flow. Supporting safer, more coordinated care.**

---

## **Overview**

Hospitals don’t fail because they lack data — they fail because decisions arrive too late.

**Decision Advantage — Integrated Predictive Care Intelligence (IPCI) Platform** is a governance‑first operational intelligence system that transforms fragmented hospital signals into **predictive insight**, **prioritised actions**, and **leadership‑ready decision support**.

Built during **OpenAI Build Week**, the platform uses **Codex** for deterministic engine generation and **GPT‑5.6** for operational reasoning.  
All data is **synthetic**, **privacy‑first**, and **fully reproducible**.

---

## **The Problem: Decision Latency**

Operational delays — ED boarding, staffing shortages, Delayed Transfers of Care (DTOC), winter surges — create cascading failures across hospitals.

Behind every delay is a person like **Mary**, a 72‑year‑old patient who waited 24 hours on a trolley due to slow operational decisions.

The co‑pilot is designed to eliminate this latency.

---

## **Why IPCI Matters**

**IPCI (Integrated Predictive Care Intelligence)** is a four‑layer decision architecture that links:

**Signals → Insight → Decision Support → Governance**

It ensures hospitals don’t just see pressure — they act on it earlier, faster, and with accountability.

---

# **IPCI Architecture (4‑Layer Decision System)**

---

## **1. Signals Layer — Synthetic, Privacy‑First**

Synthetic operational signals representing:

- ED surge  
- Staffing shortage  
- DTOC pressure  
- Bed status  
- Winter surge  
- Flow indicators  
- Human‑impact factors  

### **Minimum Viable Interoperability (MVI) & Data Sovereignty**

The platform connects only to essential operational signals — not full EHR data — ensuring:

- **No PHI**  
- **No patient‑level data**  
- **Full data sovereignty**  
- **GDPR / DPA alignment**  
- **EU AI Act‑aligned risk management**

This makes IPCI deployable across diverse hospital systems without centralising sensitive data.

---

## **2. Engines Layer (Codex‑Generated)**

Deterministic engines built using Codex:

- Flow Score engine  
- Pressure engine  
- Bed status engine  
- Human‑impact engine  
- Situation report engine  
- Scenario simulation engine  

---

## **3. Reasoning Layer (GPT‑5.6)**

GPT‑5.6 provides:

- Operational interpretation  
- Risk summarisation  
- Leadership‑ready insights  
- Judge Mode reasoning  
- Scenario comparison  
- Narrative generation  

---

## **4. Governance Layer**

Judge Mode compresses the entire hospital state into:

- **One headline**  
- **Five risks**  
- **Three actions**  
- **Human‑impact score**

This is the layer used by executives, flow managers, and clinical operations leaders.

### **Regulatory Alignment**

The governance layer is designed to support:

- **GDPR compliance**  
- **EU AI Act risk‑tier alignment**  
- **Operational transparency and auditability**  
- **Clear human‑in‑the‑loop decision pathways**

---

# **Key Features**

## **Baseline State**

Synthetic, privacy‑first hospital baseline with reproducible operational signals.

## **Pressure Scenarios**

Stress tests including:

- ED Surge  
- Staffing Shortage  
- DTOC Pressure  
- Bed Pressure  
- Winter Surge  

## **Flow Score**

A single operational pulse metric combining ED, inpatient, and discharge flow.

## **AI Recommendations (Actions Engine)**

Deterministic operational actions generated from pressure signals.

## **Judge Mode**

Leadership‑ready summary:

- 1 headline  
- 5 risks  
- 3 actions  
- human‑impact score  

## **Human Impact**

Quantifies how operational delays affect patients like Mary.

---

# **Build Week Development Summary**

This project builds on an early conceptual prototype created before Build Week.  
During Build Week, the majority of the system was developed, including:

### **Built During Build Week (Codex + GPT‑5.6):**

- FastAPI backend scaffolding  
- deterministic engines (Flow Score, Pressure, Human Impact)  
- synthetic hospital data models  
- scenario simulation endpoints  
- situation report engine  
- Judge Mode reasoning  
- leadership‑ready narrative generation  
- governance layer (headline, risks, actions)  
- operational deltas and scenario comparison  
- human impact scoring  
- integration between frontend and backend  
- IPCI alignment and architecture refinement  

### **Existed Before Build Week:**

- early UI concept  
- initial Lovable layout  
- high‑level IPCI framework  
- early synthetic data ideas  
- initial operational theory (Decision Latency, Flow Score concept)

Build Week transformed the prototype into a **fully functional Operations Intelligence Co‑Pilot** powered by Codex and GPT‑5.6.

---

# **How Codex Was Used**

Codex generated:

- FastAPI scaffolding  
- deterministic engines  
- synthetic data models  
- routing, validation, API structure  
- situation report logic  
- scenario simulation endpoints  

Codex accelerated:

- architecture iteration  
- engine refinement  
- data modelling  
- error handling  
- code cleanup  
- API consistency  

---

# **How GPT‑5.6 Was Used**

GPT‑5.6 powers the reasoning layer:

- converts raw signals into operational insight  
- summarises pressure scenarios  
- generates leadership‑ready narratives  
- produces Judge Mode outputs  
- evaluates human impact  
- compares baseline vs pressure states  
- recommends actions  

GPT‑5.6 transforms deterministic engines into actionable decision support.

---

# **Synthetic Data & Privacy**

- **No PHI**  
- **No patient‑level data**  
- **All data synthetic and reproducible**  
- **All scenarios simulated**  
- **Fully privacy‑first design**

---

# **Project Structure**

```
/api
  /models.py
  /synthetic_data.py
  /engines
  /routers
  /situation_report.py

/frontend
  Lovable UI components
  Scenario views
  Judge Mode panel
  Human Impact panel

/docs
  Architecture notes
  IPCI framework
  Build Week logs
```

---

# **Live Demo**

**Frontend (Lovable):**  
<https://operah-care.lovable.app>

**Backend (Render API):**  
<https://ai-hospital-prototype.onrender.com>

---

# **API Examples**

```
/api/demo?scenario=baseline&seed=42
/api/demo?scenario=ed_surge&seed=42
/api/situation-report?scenario=staff_shortage&seed=42
```

All endpoints are public and safe to test.

---
# **Build Week Session ID**
019f7694-3d0c-7e60-8cc4-4be4adc7fd9e.

# **Team**
**Mohamed Abdurrahman** -
AI & Data Consultant
Dublin, Ireland

**License**:
MIT License
