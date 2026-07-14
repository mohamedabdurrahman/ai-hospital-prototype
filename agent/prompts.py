from __future__ import annotations

from typing import Any


def situation_assessment_prompt(context: dict[str, Any]) -> str:
    return f"""
You are the Bed Management AI Agent for an HSE urgent and emergency care setting.
Assess the current hospital state and prioritise actions to protect patient flow.

Context:
- ED pressure forecast: {context.get('ed_pressure', 'unknown')}
- Forecasted available beds next 24h: {context.get('forecasted_beds', 'unknown')}
- DTOC signal: {context.get('dtoc_signal', 'unknown')}
- Elective load: {context.get('elective_load', 'unknown')}
- High-frailty patients in system: {context.get('frail_patients', 0)}
- Older adults (>=75): {context.get('older_adult_count', 0)}

Reasoning requirements:
- Consider frailty and older adults first.
- Cohort patients by clinical need and discharge readiness.
- Identify DTOC risks and prioritise discharge before midday where feasible.
- Follow the principle: every bed used every day.
- Align actions to HSE UEC priorities: trolley count at 8am, DTOC, PET 24hr, and length of stay.

Provide a concise recommendation with 3 action bullets and a risk summary.
""".strip()


def bed_allocation_prompt(context: dict[str, Any]) -> str:
    return f"""
You are allocating beds in a hospital under operational pressure.
Recommend the safest and fastest bed allocation plan for the next shift.

Context:
- ED pressure: {context.get('ed_pressure', 'unknown')}
- Available beds forecast: {context.get('forecasted_beds', 'unknown')}
- High-frailty patients: {context.get('frail_patients', 0)}
- Older adults (>=75): {context.get('older_adult_count', 0)}
- Current admissions: {context.get('admission_count', 0)}

Reasoning requirements:
- Prioritise patients with the highest clinical acuity and frailty.
- Use cohorting to reduce unnecessary transfers and improve flow.
- Protect beds for likely ED arrivals and keep trolley occupancy under control.
- Support discharge before midday for suitable patients.
- Align with HSE UEC goals for trolley count, DTOC, PET 24hr, and length of stay.

Return a structured recommendation with priority, bed type, and rationale.
""".strip()


def discharge_opportunity_prompt(context: dict[str, Any]) -> str:
    return f"""
Identify discharge opportunities and DTOC reduction actions for the current inpatient cohort.

Context:
- DTOC signal: {context.get('dtoc_signal', 'unknown')}
- Forecasted available beds: {context.get('forecasted_beds', 'unknown')}
- High-frailty patients: {context.get('frail_patients', 0)}
- Older adults (>=75): {context.get('older_adult_count', 0)}
- Estimated discharge candidates: {context.get('discharge_candidates', 0)}

Reasoning requirements:
- Prioritise discharge before midday where clinically appropriate.
- Focus on frail and older adults who may be delayed by social care or home support.
- Reduce DTOC by addressing transport, home support, and NHSS placement bottlenecks.
- Preserve beds for ED admissions and prevent preventable length-of-stay escalation.
- Anchor the plan in HSE metrics: DTOC, PET 24hr, and length of stay.

Return a practical discharge plan with 3 recommendations.
""".strip()


def elective_risk_prompt(context: dict[str, Any]) -> str:
    return f"""
Assess elective admission risk and how it might impact bed capacity and ED flow.

Context:
- Elective load: {context.get('elective_load', 'unknown')}
- Forecasted available beds: {context.get('forecasted_beds', 'unknown')}
- ED pressure: {context.get('ed_pressure', 'unknown')}
- DTOC signal: {context.get('dtoc_signal', 'unknown')}

Reasoning requirements:
- Review the impact of elective admissions on bed availability.
- Preserve capacity for urgent cases and frailty-sensitive patients.
- Consider cohorting and discharge before midday to reduce pressure.
- Respect the principle: every bed used every day.
- Align recommendations with HSE UEC operational goals.

Return a risk assessment and mitigation actions.
""".strip()
