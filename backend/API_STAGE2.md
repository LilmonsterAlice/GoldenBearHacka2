# CutScope read API — Stage 2 implementation draft

Status: implemented backend behavior for review/adoption by Person 5. The
shared root contract and fixtures are still empty. This document is not an
approved team contract and does not replace `API_CONTRACT.md`.

Existing endpoint and field names come from the supplied project description.
Additions from the implementation plan are pricing metadata on cards/details,
complete opportunity details, job references, and pagination metadata. Person 5
should synchronize the root contract, shared fixture, and frontend models when
adopting these decisions. No shared document, fixture, AI file, or frontend file
was modified for Stage 2.

## Common semantics

- JSON uses snake_case. All declared fields are required, even when nullable.
- Unknown measurements are `null`; a genuine zero stays `0`.
- GPU-hours, USD, utilization, and confidence must be finite. Quantities are
  nonnegative; utilization/capacity percentages are 0–100; confidence is 0–1.
- IDs: nonempty strings without whitespace for opportunities; nonnegative
  integers for jobs. No risk-level or job-state enumeration is introduced.
- The backend preserves stored values, analytics ranking, and affected-job
  order. It does not calculate savings, convert cancellations into waste,
  combine finding impacts, or assess analytical deduplication correctness.
- Monetary response objects carry `price_per_gpu_hour` and
  `price_book_version`, copied from the summary snapshot. This MVP assumes one
  snapshot-wide price book; multiple pricing schemes require agreement with
  analytics before changing the schema. Nested cost-if-wrong amounts use the
  enclosing response's pricing context.
- `X-Analysis-Mode: mock|real` identifies the operator-selected dataset mode.
  It is not a certificate that arbitrary input is verified official data.

## GET /api/summary

Unchanged from Stage 1: `total_gpu_hours`, `total_cost_usd`,
`price_per_gpu_hour`, `price_book_version`, `completed_percent`, `outcomes`,
and `scope_caveat`.

Outcome records contain `name`, `jobs`, `gpu_hours`, `cost_usd`, and
`capacity_percent`. Unknown numerical values may be null. Summary preserves
the supplied sample caveat.

## GET /api/opportunities

Returns `{"opportunities": [card, ...]}` in analytics-supplied order. This small
ranked opportunity list is not paginated.

Each card has:

| Fields | Type / interpretation |
| --- | --- |
| `id`, `title` | Required nonempty strings |
| `action`, `owner`, `risk_level` | String or null |
| `savings_usd_low`, `savings_usd_high` | Nonnegative USD or null |
| `gpu_hours_low`, `gpu_hours_high` | Nonnegative GPU-hours or null |
| `capacity_percent_low`, `capacity_percent_high` | 0–100 or null |
| `confidence` | 0–1 or null |
| `job_count` | Integer count of affected job references |
| `price_per_gpu_hour`, `price_book_version` | Snapshot pricing metadata |

If both ends of a range are known, low must not exceed high. One unknown end
remains null rather than being inferred from the other end.

## GET /api/opportunities/{id}?offset=0&limit=20

Returns all card fields plus:

| Field | Type / interpretation |
| --- | --- |
| `method`, `basis` | String or null; supplied analytical explanation |
| `caveats` | Array of strings |
| `cost_if_wrong` | Object described below |
| `jobs` | Requested page of integer job IDs, e.g. `[123, 124]` |
| `jobs_pagination` | `{"total": integer, "offset": integer, "limit": integer}` |

Cost-if-wrong fields: `description` (string/null), `usd_low` and `usd_high`
(nonnegative USD/null), `reversible` (boolean/null), and `mitigation`
(string/null). Known USD range ends must be ordered.

Pagination:

- `offset` defaults to 0 and must be nonnegative.
- `limit` defaults to 20 and must be from 1 through 100.
- Pagination metadata reports the requested offset/limit and full affected-job
  total, not the page size. `job_count` is never replaced with page length.
- An offset at or beyond the end returns an empty page with status 200.
- Pagination never changes savings values, ranking, or stored job references.
- To retrieve evidence, pass a returned integer to `/api/jobs/{job_id}`.

## GET /api/jobs/{job_id}

| Fields | Type / interpretation |
| --- | --- |
| `job_id` | Nonnegative integer |
| `state`, `primary_node` | String or null |
| `gpu_count` | Nonnegative integer or null |
| `gpu_hours`, `cost_usd`, `walltime_hours` | Nonnegative number or null |
| `sm_util_avg`, `sm_util_max` | 0–100 or null |
| `findings` | Array of upstream finding objects, preserved as supplied |
| `price_per_gpu_hour`, `price_book_version` | Snapshot pricing metadata |

The official finding schema has not been provided. Finding objects remain
opaque JSON objects, so upstream identifiers, source, raw evidence, and the
fact/judgment distinction are not lost or renamed. The local fixture shows
synthetic references and embedded raw evidence; these fields are illustrations,
not a claim about the official MantisGrid schema or a live MantisGrid call.
Person 4 and Person 5 must agree the finding/evidence structure before live
integration. This route serves snapshot evidence and has no AI dependency.

## Errors

All application error responses use:

```json
{
  "error": {
    "code": "OPPORTUNITY_NOT_FOUND",
    "message": "Opportunity not found",
    "retryable": false
  }
}
```

| HTTP | Code | Trigger |
| --- | --- | --- |
| 404 | `OPPORTUNITY_NOT_FOUND` | Unknown opportunity ID |
| 404 | `JOB_NOT_FOUND` | Unknown well-formed job ID |
| 404 | `NOT_FOUND` | Unknown route |
| 405 | `METHOD_NOT_ALLOWED` | Unsupported HTTP method; preserves Allow header |
| 422 | `VALIDATION_ERROR` | Invalid job ID or pagination parameter |
| 500 | `INTERNAL_ERROR` | Unexpected backend failure |

Validation messages include failing parameter locations, not raw submitted
values. Internal responses do not expose exception text, traces, or dataset
paths. These errors use `retryable=false`: the frontend should not blindly
retry invalid inputs or unknown internal failures. CORS protocol preflight
rejections are middleware transport responses, not product error envelopes.
API success/error schemas and pagination bounds appear in Swagger.

## Snapshot format and startup integrity

```text
summary: Summary
opportunities: complete OpportunityRecord[]
jobs: complete JobRecord[]
```

Stored opportunity records contain all detail fields except pricing metadata
and `jobs_pagination`; their `jobs` contain all affected references. Stored job
records omit pricing metadata, which is supplied from summary. The API only
slices references and attaches stored pricing; no monetary math occurs here.

Stored opportunity job references retain `{"job_id": integer}` objects for
existing analytics/AI-context compatibility. The paginated response transforms
these into integer IDs to match the root API contract. No stored fixture or
chat-context format migration is required.

Startup rejects malformed models, invalid bounds/ranges, duplicate IDs,
duplicate job references within an opportunity, nonexistent referenced jobs,
and `job_count` inconsistent with the full reference list. It intentionally
does not forbid a job appearing in multiple opportunities: job-hour primary
assignment and analytical overlap require Person 1's methodology and tests.

See [the local synthetic fixture](fixtures/analysis.stage1.mock.json) for a
complete input example. Its original filename is retained to preserve Stage 1
configuration; its contents now support Stage 2. It is safe development data,
not generated official analysis or submission evidence.

## Person 5 adoption checklist

1. Review these provisional additions with Persons 1, 3, and 4; document the
   resulting agreed contract in the root file.
2. Populate the shared fixture with consistent IDs, complete records, and
   explicit mock labels; synchronize frontend models/API client.
3. Configure `ANALYSIS_PATH` to select that fixture in mock mode and mount it
   read-only during later Compose integration.
4. Verify summary -> list -> detail -> paginated job -> evidence navigation.
5. Run backend tests; retain the snapshot-wide pricing and sample caveats.
6. Keep live AI/MantisGrid verification, real-data adoption, Docker packaging,
   and fresh-clone E2E as later-stage tasks.

Error handling and parameter validation use the documented FastAPI
[exception handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/)
and [query validation](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/).
