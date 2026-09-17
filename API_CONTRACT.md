# CutScope — Product API Contract v1.0

This file is the shared contract. Product endpoints use `/api`; official
MantisGrid endpoints retain `/v1`. JSON field names use `snake_case`.

Contract changes require Person 2 and Person 5 approval and synchronized updates
to backend models, frontend consumers, fixtures, and contract tests.

## Common rules

- Missing values are `null`, never fake zeroes.
- Capacity percentages use the `0..100` scale.
- USD values must identify the applicable price/rate in the containing response.
- Errors use the common error envelope below.

## `GET /api/summary`

```json
{
  "total_gpu_hours": 594004.0,
  "total_cost_usd": 1485010.0,
  "price_per_gpu_hour": 2.5,
  "price_book_version": "2026-Q3",
  "completed_percent": 38.6,
  "outcomes": [
    {
      "name": "COMPLETED",
      "jobs": 45334,
      "gpu_hours": 229041.0,
      "cost_usd": 572602.5,
      "capacity_percent": 38.6
    }
  ],
  "scope_caveat": "Four-month workload sample"
}
```

## `GET /api/opportunities`

```json
{
  "opportunities": [
    {
      "id": "idle-interactive",
      "title": "Idle interactive sessions",
      "action": "Introduce a warning and idle timeout",
      "owner": "Platform Operations",
      "savings_usd_low": 10000.0,
      "savings_usd_high": 20000.0,
      "gpu_hours_low": 4000.0,
      "gpu_hours_high": 8000.0,
      "capacity_percent_low": 0.67,
      "capacity_percent_high": 1.35,
      "confidence": 0.7,
      "risk_level": "medium",
      "job_count": 25
    }
  ]
}
```

The numbers above illustrate response shape only and are not competition claims.

## `GET /api/opportunities/{id}`

```json
{
  "id": "idle-interactive",
  "title": "Idle interactive sessions",
  "action": "Introduce a warning and idle timeout",
  "method": "Documented deterministic method",
  "basis": "Documented inclusion and exclusion rules",
  "caveats": ["Illustrative mock response"],
  "confidence": 0.7,
  "cost_if_wrong": {
    "description": "A legitimate interactive session could be terminated.",
    "usd_low": 1000.0,
    "usd_high": 5000.0,
    "reversible": true,
    "mitigation": "Warn first and provide an exception path."
  },
  "jobs": [123]
}
```

## `GET /api/jobs/{job_id}`

```json
{
  "job_id": 123,
  "state": "CANCELLED",
  "gpu_count": 4,
  "gpu_hours": 32.0,
  "cost_usd": 80.0,
  "sm_util_avg": 2.1,
  "sm_util_max": 18.0,
  "walltime_hours": 8.0,
  "primary_node": "node-id",
  "findings": []
}
```

## `POST /api/chat`

Request:

```json
{
  "question": "Why is this recoverable?",
  "opportunity_id": "idle-interactive",
  "job_id": null
}
```

Response:

```json
{
  "answer": "Evidence-grounded answer",
  "evidence": [],
  "risk": "Evidence-grounded downside",
  "recommendation": "Action and mitigation",
  "confidence": 0.7,
  "finding_ids": [],
  "job_ids": [123],
  "caveats": []
}
```

## Error envelope

```json
{
  "error": {
    "code": "OPPORTUNITY_NOT_FOUND",
    "message": "Opportunity not found",
    "retryable": false
  }
}
```
