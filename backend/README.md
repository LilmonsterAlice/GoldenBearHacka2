# CutScope backend — Stages 1–3

Implemented: FastAPI, typed summary/opportunity/job models, startup snapshot
validation, reference integrity checks, defensive-copy lookups, configurable
CORS, four read APIs, affected-job pagination, consistent application errors,
chat HTTP adapter, authoritative context lookup, timeout/fallback handling,
Swagger, and tests. Core analysis works without external AI.

See [the Stage 2 contract draft](API_STAGE2.md) for exact fields, pagination,
error codes, storage layout, and Person 5's adoption checklist.
See [Copilot integration](COPILOT_INTEGRATION.md) for Person 4's async callable,
chat schemas/configuration, and remaining live-integration work.

## Local startup

From the repository root, using Python 3.10 or newer:

```bash
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

Summary: <http://localhost:8001/api/summary>

Swagger: <http://localhost:8001/docs>

Opportunities: <http://localhost:8001/api/opportunities>

First detail: <http://localhost:8001/api/opportunities/idle-interactive?offset=0&limit=1>

Job evidence: <http://localhost:8001/api/jobs/123>

```bash
.venv/bin/python -m pytest backend/tests -q
```

## Configuration

| Variable | Default | Behavior |
| --- | --- | --- |
| `ANALYSIS_MODE` | `mock` | `mock` or `real`; returned in `X-Analysis-Mode` header |
| `ANALYSIS_PATH` | Backend-local fixture in mock mode; `generated/analysis.json` in real mode | Absolute path or repository-relative path |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated origins; empty disables allowed origins; credentials disabled |
| `CHAT_SERVICE` | Unset | Optional `module:async_callable` owned by Person 4 |
| `CHAT_TIMEOUT_SECONDS` | `20` | Finite positive cooperative service timeout |

Environment is captured when the application is created. The snapshot loads
once during startup. Restart after changing environment or snapshot contents.
Missing/invalid files fail startup; no silent mock fallback exists. Known
fixture paths are rejected in real mode, but mode is operator-selected and
cannot certify arbitrary file contents as official or verified.

Example real-mode startup after Person 1 supplies the file:

```bash
ANALYSIS_MODE=real ANALYSIS_PATH=generated/analysis.json .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

## Person 5 handoff and assumptions

The shared `PROJECT_SPEC.md`, `API_CONTRACT.md`, `ANALYSIS_METHOD.md`, and
`fixtures/analysis.mock.json` remain empty through Stage 3 adapter work. Summary fields
follow the supplied project-description examples. Required numeric fields
accept explicit null for unknown values; absent fields are rejected. Values
are served unchanged, with finite nonnegative numbers and 0–100 percentages.
No monetary arithmetic or analytics methodology is implemented here.

The temporary synthetic fixture lives at
`backend/fixtures/analysis.stage1.mock.json`; it is not official analysis and
now includes one idle-interactive opportunity and two jobs. Its original
filename remains stable for existing configuration. Its price-book label, caveat, response
header, and startup warning identify mock operation. Shared files are untouched.

The provisional file envelope is `{summary, opportunities, jobs}`. All three
record types are validated. Findings remain opaque upstream JSON objects
until the official finding schema is supplied. The backend-local contract
draft records new pagination, job-reference, and pricing fields; these are
implemented defaults for team review, not a frozen shared contract.
Read-only consumers obtain defensive copies: `get_summary()`, `get_pricing()`,
`list_opportunities()`, `get_opportunity(id)`, `get_job(id)`.

Person 5 can adopt the shared fixture by setting
`ANALYSIS_PATH=fixtures/analysis.mock.json` once that file contains the agreed
schema. Any different storage layout belongs in `analysis_store.py`, with
coordinated schema tests. Do not silently change the summary API.

For later Compose integration, use repository root as working directory,
the startup command above, container port 8001, and a read-only snapshot mount
at the configured path. The existing root Compose still launches only the
dashboard. Backend Docker packaging and Compose changes are later-stage work.

Limitations: Person 4's four AI service files remain empty. The chat adapter
works with injected/configured async services and defaults to an honest
`cannot_determine` fallback; live service integration and evidence grounding
are pending. Health endpoint, live MantisGrid evidence, real-data adoption,
Docker packaging, and full frontend/container E2E are not yet implemented.
The only opportunity is synthetic first-slice development data; final MVP's
three ranked real opportunities depend on Person 1. Dependency ranges are
bounded but not locked; finalize reproducible deployment versions during
packaging. No shared contract was edited or claimed to be approved.

## Verification at handoff

`python -m pytest backend/tests -q`: 105 passed. Tested with Python 3.13.5,
FastAPI 0.141.1, Pydantic 2.13.5, Uvicorn 0.53.0, pytest 9.1.1, and
httpx 0.28.1. The installed Starlette/AnyIO test stack emitted two dependency
deprecation warnings; tests passed. Container/network E2E was not run in this
stage. In-process API tests cover the full read-only drill-down, pagination,
null/zero preservation, pricing, failure sanitization, CORS, OpenAPI, and
snapshot integrity. Chat tests cover authoritative context, importable async
services, invalid requests/responses, reference checks, cancellation/timeout,
fallback, CORS, and read-API independence. These use test stubs, not live AI.
Startup snapshot loading uses FastAPI's documented
[lifespan mechanism](https://fastapi.tiangolo.com/advanced/events/).
