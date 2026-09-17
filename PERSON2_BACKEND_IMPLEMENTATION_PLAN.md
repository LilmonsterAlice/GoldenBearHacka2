# CutScope: Person 2 Backend Implementation and Person 5 Integration Plan

Status: implementation plan only. Backend implementation has not started.

## 1. Purpose and project alignment

Person 2 will build the Product FastAPI service on port 8001. It will expose deterministic analysis results and provide the HTTP entry point for Person 4's AI Copilot. Person 5 will assemble and verify the complete system rather than implement unfinished backend features.

This plan is based on `GOLDENBEAR_FULL_PROJECT_STRUCTURE_CN(1).md` and `TEAM_INTEGRATION_RULES_CN(2).md`, supplied from Downloads. Their requirements are recorded below separately from this plan's proposed decisions. This file does not replace the future `PROJECT_SPEC.md`, `API_CONTRACT.md`, or `ANALYSIS_METHOD.md`.

The first working flow is:

```text
Summary and savings range
  -> idle-interactive opportunity
  -> calculation basis and cost-if-wrong
  -> affected job and supporting finding/evidence
  -> AI explanation with references, confidence, and caveats
```

### Requirements from the project documents

- Product backend: FastAPI at `:8001`; official MantisGrid API/MCP at `:8000`; Streamlit dashboard at `:3000`.
- Exactly five product endpoints under `/api`; official endpoints remain under `/v1`.
- Analytics computes GPU-hours, dollars, percentages, classifications, scenarios, and deduplication. Backend serves those results; LLM explains them.
- Shared synthetic fixture first; real `generated/analysis.json` later without changing the API.
- Snake-case JSON; missing measurements are null, not zero; percentages use 0–100.
- Monetary results identify a rate or price book. Savings have ranges, confidence, basis, and caveats.
- Results describe the four-month sample. CANCELLED does not automatically mean waste; overlapping finding impacts must not be added.
- Chat accepts questions and IDs, not client-supplied telemetry as an authoritative source.
- AI failures must leave the dashboard's core analysis usable.
- No database, authentication system, production streaming, automatic infrastructure changes, additional AI service, RAG, or multi-agent framework.
- Person 2 does not rewrite Person 4's AI service files.
- Person 5 owns shared project documents, Compose, submission artifacts, E2E, and integration merges.
- Do not commit real data, generated datasets, secrets, or `.env` files.

### Current repository baseline

The repository has a dummy Streamlit application, a second dummy dashboard, empty `src/*.py` modules, and an empty pipeline test. There is no `backend/`, shared fixture, generated analysis, API contract, or Compose file. Existing launch instructions use Streamlit port 8501. The target architecture therefore needs new modules; it is not an existing backend refactor.

## 2. Ownership and boundaries

| Area | Person 2 will do | Other owner's responsibility |
| --- | --- | --- |
| Contract | Propose complete types and behavior; implement approved models | Person 5 maintains shared contract and coordinates agreement |
| Synthetic fixture | Supply schema requirements and validate fixture | Person 5 coordinates shared fixture with Persons 1, 3, and 4 |
| Analysis store | Load, validate, index, and expose analysis records | Person 1 generates correctly calculated real analysis |
| Product routes | Implement all five routes, validation, errors, pagination, CORS | Person 3 consumes them through its API client |
| Copilot integration | Own chat HTTP adapter and authoritative ID resolution | Person 4 owns MantisGrid, context, LLM, grounding, and fallback content |
| Backend packaging | Provide requirements, Dockerfile, startup instructions | Person 5 owns root Compose and environment template |
| Tests | Backend contract, route, store, and chat adapter tests | Person 5 owns service-to-service E2E and fresh-clone verification |
| Submission | Provide backend limitations and validation evidence | Person 5 owns claims, report, README, and demo |

Person 2 works on `feature/product-api`. Person 5 reviews and merges runnable increments to `integration`. Main receives the integrated, checked result. This requested planning file is a shared reference, not a transfer of Person 5's root-file ownership.

## 3. Stage 0 — Make the interfaces complete

### What I will do

1. Read the shared specification, contract, analysis method, and fixture in full once Person 5 establishes them.
2. Provide Person 5 a concrete contract proposal covering each request, response, nested object, nullable value, and failure.
3. Review the proposal with Person 1 for file output, Person 3 for dashboard needs, and Person 4 for evidence and chat needs.
4. Record unresolved decisions explicitly rather than treating example JSON as a complete schema.

### Proposed defaults to review with Person 5

These are recommendations, not already-approved changes to the team's contract:

| Gap | Recommended decision | Why / affected owner |
| --- | --- | --- |
| First opportunity ID | Use `idle-interactive` throughout | API examples use this; prose also uses `idle-interactive-session`. All modules must agree |
| Opportunity detail | Include list-card fields plus method, basis, caveats, risk, and affected jobs | Detail must explain the exact savings shown on the dashboard; Persons 1 and 3 need the same shape |
| Job IDs | Integers, matching supplied API examples | Confirm against actual data before freezing; Persons 1 and 4 |
| Confidence | Number in 0–1, or null when genuinely unknown | Distinct from percentage fields in 0–100; Persons 1, 3, and 4 |
| Opportunity order | Analytics supplies ranked order; backend preserves it | Ranking should not silently change in a route |
| Pagination | Page affected jobs inside opportunity detail using `offset` and `limit`; proposed default 20, maximum 100 | No sixth product endpoint; Persons 1 and 3 agree job-reference shape and metadata |
| Evidence | Define typed findings/references, fact versus judgment, source, and any raw-evidence reference needed by UI | Empty arrays in examples do not specify a usable evidence contract; Persons 3 and 4 |
| Monetary provenance | Explicit rate/price-book references on responses containing USD, using the dataset's pricing metadata | Prevent ambiguous detail figures; Persons 1 and 3 |
| Chat fallback | Preserve the existing response fields; explain unavailability or insufficient evidence in answer/caveats | No fabricated answer or new numeric claims; Persons 3 and 4 |
| Shared Python models | Backend is authoritative for API validation; agree how frontend types are mirrored or shared | Avoid two independently drifting schemas; Persons 3 and 5 |

Agree the pagination envelope, risk enumeration, nullability, finding schema, evidence schema, ID rules, and error-code catalog before implementing affected fields. Do not add scenario parameters, point estimates, new enums, or extra product endpoints without the documented contract-change process.

### Proposed analysis-file boundary

Use one validated JSON snapshot containing:

```text
summary: the Summary model
opportunities: ordered complete OpportunityDetail records
jobs: complete JobDetail records
```

Opportunity detail records reference jobs by the agreed affected-job structure. Full job records live in `jobs`. Every referenced job must exist; opportunity and job IDs must be unique. Dataset pricing and sample provenance must be recoverable from the agreed fields. A backend-only file model may contain generation metadata if agreed with Person 1; those fields need not become public API fields.

This is a proposed storage contract, not an assumption about an existing `analysis.json`. Keep file parsing in `analysis_store.py` so a later storage-layout change can be adapted without changing the public responses. Validate one agreed layout rather than guessing among several layouts.

### What Person 5 receives / exit condition

- Complete contract decisions and a small synthetic fixture with one consistent idle-interactive opportunity, affected jobs, and evidence references.
- Fixture values explicitly identified as synthetic, not official results or submission claims.
- A named owner for every remaining dependency.
- Exit: file schema and first-slice API shapes are agreed and documented. Missing shared documents do not block this planning work, but their contents must be settled before implementing affected interfaces.

## 4. Stage 1 — Establish a validated mock-backed backend

### What I will do

- Create `backend/main.py`, `models.py`, `services/analysis_store.py`, backend requirements, and initial tests.
- Add Pydantic models for the agreed file and API contracts, with deliberate null handling and numeric bounds.
- Load the selected JSON once during application startup; validate it and build job/opportunity lookup indexes.
- Expose read-only lookup methods so routes and Person 4 can use the same authoritative snapshot.
- Implement `GET /api/summary` and verify Swagger reflects the contract.
- Configure allowed CORS origins from settings. Do not use an unrestricted credentials configuration.

### Proposed data-mode policy

- `ANALYSIS_MODE=mock` selects the shared synthetic fixture.
- `ANALYSIS_MODE=real` selects generated analysis.
- `ANALYSIS_PATH` specifies the file location; mode and path are explicit deployment settings.
- A missing, malformed, or inconsistent file fails startup with an actionable diagnostic. Real mode never silently falls back to mock.
- Replacing the snapshot requires restarting the backend for MVP. Live reload is outside scope.

### What Person 5 receives / exit condition

- Runnable mock-backed summary API and Swagger.
- Configuration names, path rules, dependency requirements, and test command.
- Exit: valid fixture starts successfully; invalid input is rejected; response preserves source values and nulls.

## 5. Stage 2 — Complete the read-only vertical slice

### What I will do

- Implement `GET /api/opportunities`, `GET /api/opportunities/{id}`, and `GET /api/jobs/{job_id}`.
- Preserve analytics' ranking and numbers; select and serialize records without recalculating savings.
- Implement the approved pagination and stable affected-job order. Total count describes all matching jobs, not only the returned page.
- Include approved savings explanation, basis, caveats, cost-if-wrong, mitigation, findings, and evidence references.
- Add consistent handling for unknown IDs, invalid parameters, and unexpected failures. Client errors follow the shared error envelope; internal failures do not expose raw internals.
- Add contract and route tests covering both success and failure paths.

### What Person 5 receives / exit condition

- Four working read APIs and reproducible request examples.
- A fixture-backed path Person 3 can navigate from summary to opportunity to job/evidence.
- Exit: savings displayed in the list can be traced through detail to job and supporting evidence, with consistent IDs, pricing, and sample caveats.

## 6. Stage 3 — Attach the AI Copilot safely to the same data

### What I will do

- Implement the `POST /api/chat` route, request validation, ID resolution, and response validation.
- Agree a narrow callable boundary with Person 4: validated question and IDs plus access to the read-only analysis store; result must match ChatResponse.
- Reject unknown IDs and agree how to handle a supplied job that does not belong to a supplied opportunity.
- Ensure context comes from backend records and Person 4's MantisGrid evidence, not client-supplied telemetry.
- Bound the chat call with an agreed timeout and map failures to the approved fallback behavior.
- Test the adapter using a stub service before Person 4's real service is available. A stub is test infrastructure, not evidence that live AI integration is complete.

### What Person 4 supplies

- `mantisgrid_client.py`, `context_builder.py`, `llm.py`, and `grounding.py`.
- MantisGrid API/MCP evidence calls, structured response, evidence-grounding checks, and deterministic fallback content.
- Defined handling for missing credentials, timeout, unavailable upstream, and insufficient evidence.
- At least three first-slice questions for integration validation.

### What Person 5 receives / exit condition

- Fifth product route and a documented service boundary.
- Working first-slice responses with job/finding references, confidence, risk, recommendation, and caveats.
- Exit: actual Person 4 integration works; failure and `cannot_determine` cases do not invent numeric results; read APIs remain usable without external AI.

## 7. Stage 4 — Adopt real analysis without changing the UI contract

### What I will do

- Validate Person 1's real JSON against the file schema and detect broken references, duplicate IDs, and invalid types/ranges.
- Run the same route/contract checks using real input locally without committing it.
- Resolve differences at the file-adapter boundary when public semantics remain unchanged.
- If a public shape must change, document the reason and impact, obtain Backend/Integration agreement, and synchronize contract, models, frontend, and fixture before continuing that implementation.
- Confirm requests serve the stored snapshot efficiently and pagination prevents huge detail responses.

### What Person 5 receives / exit condition

- Exact configuration needed to switch from mock to real mode.
- Evidence that the public shape is unchanged and that mock values cannot be mistaken for verified analysis.
- A list of upstream data issues, if any, assigned to Person 1.
- Exit: frontend consumes real analysis without component changes. Analytics' deduplication and savings-method correctness remain Person 1's responsibility and Person 5's submission checks.

## 8. Stage 5 — Package and integrate with Person 5

### What I will do

- Supply `backend/Dockerfile`, production runtime requirements, separate test dependencies if needed, and the backend startup command.
- Bind the backend to `0.0.0.0:8001` in its container.
- Document the configuration, read-only analysis-file mount, and chat-service dependencies.
- Add an operational health/readiness endpoint if Person 5 agrees. It is outside the five product APIs and must not depend on an external LLM being available.
- Debug backend integration failures and rerun the affected checks.

### What Person 5 will do

- Create root Compose wiring for official API `:8000`, product backend `:8001`, and Streamlit `:3000`.
- Set frontend `BACKEND_URL` to the backend's Compose service hostname. A container's `localhost` points to that container, not a sibling service.
- Set Person 4's MantisGrid connection to the official service using its actual agreed API/MCP transport; do not assume API and MCP URLs are interchangeable.
- Mount fixture or generated analysis read-only at the configured backend path. Keep real datasets outside image build context and out of Git.
- Coordinate frontend port/bind updates with Person 3 and replace the prototype launch instructions.
- Update ignore/build-context rules so data, generated analysis, secrets, and local environments are excluded.
- Document prerequisites for mock startup and official-data preparation for real startup; no network dataset generation during backend startup.

### Proposed deployment settings to finalize

| Setting | Meaning | Owner |
| --- | --- | --- |
| `ANALYSIS_MODE` | Explicit mock or real operation | Person 2 defines; Person 5 configures |
| `ANALYSIS_PATH` | Backend-visible snapshot path | Persons 1, 2, and 5 agree |
| `CORS_ORIGINS` | Allowed browser origins; parsing format documented | Person 2 defines; Person 5 configures |
| `BACKEND_URL` | Frontend's reachable backend base URL | Persons 3 and 5 |
| AI/MantisGrid settings | Actual transport, upstream address, timeout, and optional credentials | Person 4 defines; Person 5 configures |

Exit: root `docker compose up` starts a documented mode, dashboard is reachable at `:3000`, and the complete first slice works across services.

## 9. Stage 6 — Stabilize, expand, and hand off

### What I will do

- Fix backend defects discovered by E2E; provide final test results and known limitations.
- Serve additional opportunities through the existing models once Person 1 supplies them, in the planned order: GPU Not Needed, Slow Cancel, GPU Card Imbalance, then Node/Hardware Risk.
- Check at least three ranked opportunities can be served for the final MVP; do not fabricate missing opportunities or analytics.
- Support Person 5's fresh-clone check and provide backend limitations for the report and demo.

Person 5 validates claims, full-system behavior, one-command startup, and the four-minute demo. Backend readiness alone is not project completion.

## 10. Verification responsibilities

| Check | Person 2 verification | Person 5 integration verification |
| --- | --- | --- |
| Contracts | Validate nested responses, types, required fields, nulls, bounds, and error envelope | Frontend and AI consume the same fixture and contract |
| Snapshot | Missing/malformed file; duplicate IDs; broken job references; explicit mode | Correct file mounted; real mode never displays synthetic fixture |
| Routes | Unknown IDs; invalid inputs; stable ordering; pagination boundaries | Selection flows correctly across dashboard panels |
| Numeric fidelity | Responses preserve stored values; no route-side savings calculations | Analytics methodology, provenance, deduplication, and claims validated |
| Chat | Validated IDs, service result, timeout/failure mapping, read API independence | Actual MantisGrid evidence and grounding; AI unavailable dashboard still usable |
| Packaging | Backend image/startup and configured file access | Fresh clone, prerequisites, Compose, ports, and frontend hostname |

Tests should protect these behavioral boundaries, not duplicate every implementation detail. Grounding tests belong with Person 4; full E2E belongs with Person 5.

## 11. Practical merge and adaptation procedure

Use four initial PRs, each with a runnable handoff:

1. Models, store, summary, and initial configuration.
2. Opportunity/job routes, pagination, errors, and contract tests.
3. Chat adapter and actual Person 4 service integration, clearly identifying any still-stubbed dependency.
4. Docker packaging, real-input compatibility, and integration fixes.

Person 5 should integrate runnable slices about every 45–60 minutes rather than wait for all four. Keep subsequent fixes small and tied to one module goal.

Each Person 2 handoff contains:

- Changed files and concrete behavior now available.
- Startup/test commands and results.
- Required configuration and dataset mode.
- Assumptions, limitations, and unresolved dependency owners.
- Integration steps and whether the shared contract changed.

### How to adapt later without restarting the implementation

- Different host/container paths: change configuration and mounts.
- Different analysis JSON organization: update the validated file adapter with Person 1; preserve approved API semantics.
- Additional opportunities: add analytics records; existing routes remain reusable.
- Changed AI implementation: preserve the agreed chat-service boundary; Person 4 updates service internals.
- New field, enum, null meaning, or endpoint: use the documented contract-change process and synchronized tests.
- Unavailable upstream service: fix configuration or use approved fallback; do not invent evidence or relabel synthetic data as real.

## 12. Person 5's starting checklist

1. Establish the four shared inputs: project specification, API contract, analysis method, and synthetic analysis fixture. Person 1 owns the methodology content.
2. Review Stage 0 defaults with module owners and freeze the first-slice interfaces.
3. Create or confirm the `integration` branch and PR review flow.
4. Consume Person 2's first summary handoff while Person 3 builds against the fixture and Person 4 develops the agreed service boundary.
5. Wire Compose as service startup/configuration requirements arrive; use explicit mock mode first.
6. Run first-slice E2E, then adopt real analysis and actual AI evidence.
7. Complete fresh-clone checks, claims, report, and demo after module behavior is verified.

This sequence gives Person 5 concrete integration artifacts at each stage and leaves deployment paths, transport details, and approved contract refinements adaptable without moving backend development into Person 5's scope.
