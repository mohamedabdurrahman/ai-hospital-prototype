# AI Hospital Prototype

## Purpose

This prototype provides a Phase 1 data foundation for an AI-first hospital operations simulation aligned with the HSE Urgent and Emergency Care Operational Plan 2024–2026. It focuses on realistic synthetic data for patient flow, emergency department demand, admissions, discharge delay, and daily operational KPIs.

## Alignment with the HSE UEC Operational Plan

The synthetic data model reflects several operational priorities from the HSE Urgent and Emergency Care Operational Plan:

- Older adults and frailty-aware pathways
- Emergency department pressure and trolley occupancy monitoring
- Delayed transfer of care (DTOC) tracking
- Long-stay inpatient risk and length of stay analysis
- Ward-level operational planning for medicine, geriatrics, surgery, and ICU

## How the Synthetic Data Supports KPIs

The data generator creates structured records for:

- patients
- emergency department visits
- hospital admissions
- discharge planning and DTOC cases
- daily KPI tracking for trolley occupancy, DTOC, PET 24-hour performance, and length of stay over 14 days

These outputs are designed to support downstream analytics, forecasting, and machine learning in later phases.

## Next Steps

Phase 2 extends this foundation with:

- ML models for length of stay and discharge forecasting
- FastAPI tools for predictive endpoints
- Dashboard-ready analytics views

## Phase 2 ML + API

Train the models:

```bash
python models/train_models.py
```

Run the API:

```bash
uvicorn api.main:app --reload
```

## Phase 3 Bed Management AI Agent

Run the agent:

```bash
python agent/agent_main.py
```

The agent uses structured prompts to reason about bed allocation, discharge opportunities, and ED pressure, and can call the FastAPI-backed prediction tools when available.

## Run the Prototype

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the CSV outputs:

```bash
python data_generator.py
```
