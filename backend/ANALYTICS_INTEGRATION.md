# Stage 4: connecting Person 1's analytics later

Status: adoption tooling and contract tests are implemented. Person 1's analytics
modules are still empty and no `generated/analysis.json` exists. No official
analysis was generated, adapted, or verified. This guide prepares the handoff;
it does not require Person 1 to finish or freeze their internal format now.

## Stable API, adaptable storage

The current API shapes are documented in `API_STAGE2.md` and
`COPILOT_INTEGRATION.md`. Shared root contracts remain empty, so these are
backend implementation drafts for team review.

The backend's current input envelope is:

```text
summary: Summary
opportunities: complete OpportunityRecord[]
jobs: complete JobRecord[]
metadata: optional JSON object (producer-only; never exposed in API)
```

Person 1 may use different structures internally. If their eventual output
uses another layout (for example, jobs indexed by ID), agree a small explicit
adapter in `backend/services/analysis_store.py` after seeing that output.
Convert layout into the existing models there, preserving meanings, nulls,
pricing, ordering, IDs, and stored values. Do not add guessed layout detection,
change public API fields, or move analytics calculations into routes.

Optional `metadata` can hold generator version, sample bounds, price-book
provenance, or methodology references. It does not need to match an invented
versioning scheme. Unknown top-level fields are rejected deliberately: extra
producer information belongs in metadata or an agreed layout adapter.

## Incremental handoff for Person 1

1. **Summary first:** provide the existing summary fields with
   `opportunities: []` and `jobs: []`. This starts the summary API without
   requiring opportunity classification or evidence generation to be finished.
2. **First opportunity:** add `idle-interactive` once method, basis, ranges,
   confidence, caveats, cost-if-wrong, and affected job records are ready.
3. **More opportunities:** append analytics-ranked records as their calculations
   complete. Ranking and job-reference order are preserved.
4. **Final verification:** analytics owner verifies deduplication, pricing math,
   primary physical job-hour assignment, and the four-month scope. Backend
   validation cannot establish those analytical claims.

Only referenced job records are necessary for an opportunity's drill-down;
the initial file need not contain every official job. Every included reference
must resolve. `job_count` currently means the full number of affected job
references in that opportunity, not the size of a UI page or partial shortlist.
If analytics needs a different total-versus-evidence distinction, review the
contract with Person 5 instead of silently changing that meaning.

Keep unfinished measurements explicitly null; do not populate unknowns with
zero. Arrays may be empty when no records have been delivered. Required fields
do not disappear, and the backend does not invent missing amounts or risks.

Findings remain upstream JSON objects, allowing Person 1 and Person 4 to agree
actual evidence later without an invented MantisGrid enum. Risk-level and
job-state fields have no new enumerations. Multiple opportunities may reference
the same job when justified by analytics' job-hour assignments; backend does
not assume one entire job belongs exclusively to one opportunity.

## Export the current file schema

From the repository root:

```bash
.venv/bin/python -m backend.validate_analysis --schema
```

This prints JSON Schema from the actual models. It writes no files and reads
no dataset. The local synthetic fixture is a complete shape example, not
official output or a demand that analytics adopt its synthetic values.

For exact current types, see `backend/models.py`. The schema export includes
nullable values, ranges, full detail models, references, and optional metadata.

## Validate a supplied file without serving it

Once Person 1 produces a file:

```bash
.venv/bin/python -m backend.validate_analysis generated/analysis.json
.venv/bin/python -m backend.validate_analysis generated/analysis.json --check-api
```

Default validation mode is real. `--mode mock` validates synthetic development
files without claiming real-data adoption:

```bash
.venv/bin/python -m backend.validate_analysis --mode mock --check-api
```

The path can be absolute or repository-relative. If omitted, the validator
uses `ANALYSIS_PATH`, or the selected mode's default path. It ignores AI/CORS
configuration and imports the isolated application factory for API checks;
no external service is loaded or called.

Exit 0 means compatibility checks passed; exit 1 means the file/configuration
failed. Success prints mode, record counts, number of sampled API requests,
and an explicit statement that this is schema/reference compatibility only.
Errors report actionable locations/types without dumping raw record values.
Neither command modifies input, writes generated data, or commits anything.
`--check-api` needs `backend/requirements-dev.txt`.

## What the checks cover

- Required field types, finite numbers, nonnegative quantities, ordered known
  ranges, 0–100 percentages, and 0–1 confidence.
- Duplicate opportunity/job IDs, duplicate references within an opportunity,
  broken references, and count consistency.
- Strict JSON: duplicate object keys and non-finite values are rejected,
  including values nested inside opaque evidence or metadata. Invalid values
  are not silently converted to null.
- Real mode rejects known fixture paths and explicitly mock/synthetic-labeled
  price-book/caveat markers, including a copied fixture renamed `analysis.json`.
  These checks do not certify unlabeled arbitrary content as official data.
- API mode header, summary fidelity, complete ranked card list, and sampled
  first/last/out-of-range detail pages for up to three opportunities.
- Job values/evidence for jobs reached through those sampled pages. The loader
  checks all records; API sampling does not exercise every job route.

The checks do not recompute dollars, percentages, recoverability, cost-if-wrong,
confidence, or finding impacts. They do not validate claims, analytical overlap,
actual MantisGrid tool calls, or the frontend.

## Efficient snapshot serving

Load once at startup and restart after replacing the input file. Backend owns
no database or producer polling. Opportunity-list routes copy only card fields;
detail routes copy only metadata and the requested job-reference page. The
existing full-record lookups remain available to Person 4's context builder.
API shapes and pagination behavior are unchanged by these internal changes.

## Person 5 switch-over checklist

1. Obtain a candidate file and methodology notes from Person 1; review the
   schema/layout and agree any adapter before changing shared contracts.
2. Validate the candidate with both commands above. Resolve generator/value
   issues with Person 1; resolve layout-only issues at the backend adapter.
3. Keep real generated data local and ignored by Git. `generated/*` is already
   ignored. During later Docker work, mount it read-only and exclude it from
   the image build context; this stage does not modify Compose/build files.
4. Start the backend with:

   ```bash
   ANALYSIS_MODE=real ANALYSIS_PATH=generated/analysis.json .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
   ```

5. Keep frontend `BACKEND_URL` and components unchanged; verify actual summary,
   ranking, savings, method, caveats, job links, and evidence in the UI.
6. Verify AI's context reads the same snapshot once Person 4 supplies its service.
7. Record actual analytics validation and remaining limitations for submission.

An explicit switch to `ANALYSIS_MODE=mock` with the local fixture is available
for development/demo recovery, but must remain visibly synthetic. A missing
real file fails startup rather than triggering silent mock fallback.

## Remaining dependencies and scope

- Person 1: actual output format/sample, correct computations, methodology,
  and eventually at least three ranked real opportunities.
- Person 4: live evidence and grounded Copilot service.
- Person 5: shared contract/fixture adoption, frontend E2E, packaging, claims,
  and fresh-clone checks.

Stage 4 adds backend-only validation tooling, optional input metadata,
real-mode mock-label checks, and efficient store projections. No public API
field or endpoint changes. Analytics, AI files, shared fixtures/contracts,
frontend, and Compose remain untouched. Real-data adoption is ready to test
when Person 1 supplies a candidate; it is not marked completed prematurely.
