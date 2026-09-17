# CutScope — Project Specification v1.0

## Product

CutScope is an AI GPU Efficiency Command Center for the MantisGrid Track 2
challenge. It tells a CFO:

1. where GPU money went;
2. where to cut;
3. what it costs if the recommendation is wrong.

The dashboard is a single Streamlit application served on port `3000`. A user
must be able to move from a business number to an opportunity, supporting jobs,
MantisGrid findings, and raw evidence.

## Scope

The official four-month sample contains 74,849 GPU jobs, 225 machines, 195 GPU
users, and approximately 594,004 GPU-hours. The statement that 83% of allocated
GPU time did not become completed work is an investigation starting point, not a
recoverable-savings claim.

## First vertical slice

The first shared integration target is `idle-interactive-session`:

```text
savings range -> opportunity method -> jobs -> finding/evidence
-> AI explanation -> cost if wrong
```

## Runtime architecture

```text
official-api     :8000  MantisGrid findings, causal, rules
product-backend  :8001  Product API and AI orchestration
frontend         :3000  Streamlit dashboard
```

Final submission must start from the repository root with `docker compose up`.

## Module ownership

- Person 1: `analytics/` and deterministic calculations.
- Person 2: `backend/` Product API, excluding Person 4 service files.
- Person 3: `frontend/` / Streamlit dashboard.
- Person 4: MantisGrid client, context builder, LLM, grounding.
- Person 5: root integration files, fixtures, Compose, E2E, submission.

## Non-goals

No authentication, database, production streaming, autonomous remediation,
multi-agent system, RAG, vector database, or model training.

## Required invariants

- Financial values are computed by deterministic code, never by the LLM.
- CANCELLED is not automatically waste.
- Overlapping findings are not naively summed.
- Every claim has units, provenance, caveats, and an honest range/confidence.
- Results describe the four-month sample and are not fleet-wide extrapolations.
- Core dashboard functionality remains available if the LLM is unavailable.
