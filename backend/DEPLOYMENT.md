# Stage 5: backend deployment and Person 5 handoff

Backend packaging is implemented and verified on Docker Desktop Linux/arm64.
Full-system integration remains pending: analytics and Person 4's service are
empty, and the dashboard is a dummy prototype.

## Compose integration artifact

From the repository root:

```bash
docker compose -f docker-compose.yml -f backend/compose.integration.yml up --build
```

This overlays `product-backend` onto the existing dashboard configuration,
exposes backend `:8001` and dashboard `:3000`, mounts the synthetic analysis
read-only, waits for backend health, and sets the dashboard's
`BACKEND_URL=http://product-backend:8001`. Person 3 must still implement API
consumption before the dummy dashboard displays backend results.

Backend-only startup and configuration review:

```bash
docker compose -f docker-compose.yml -f backend/compose.integration.yml up --build product-backend
docker compose -f docker-compose.yml -f backend/compose.integration.yml config --quiet
```

Stop with the same file combination:

```bash
docker compose -f docker-compose.yml -f backend/compose.integration.yml down
```

Person 5 owns root Compose. The overlay is ready for review/merging there;
root `docker compose up` still launches only the dashboard until adoption.
No official MantisGrid service configuration is invented here.

## Backend image alone

```bash
docker build -f backend/Dockerfile -t cutscope-backend:stage5 .
docker run --rm -p 8001:8001 cutscope-backend:stage5
```

Without overrides the image uses its explicitly synthetic development fixture.
Swagger: `http://localhost:8001/docs`.

Image behavior:

- Python 3.13 slim, `/app` working directory, binding `0.0.0.0:8001`.
- Non-root UID/GID 10001; snapshot must be readable by this user.
- Exact runtime/transitive versions in `requirements.lock.txt`, included by
  `requirements.txt`. Development dependencies are not installed.
- Dockerfile-specific build allowlist admits runtime Python files, pinned
  requirements, and only the named synthetic fixture. Data, generated files,
  secrets, local environments, tests, and frontend files are excluded.
- Shared `.dockerignore` additionally excludes `generated/` for dashboard
  builds. Root Compose, frontend files, and shared API contracts are unchanged.
- Dependencies are pinned; the base `python:3.13-slim` tag is mutable. Person 5
  may freeze an image digest once integrated dependencies are final.
- Coordinate and pin Person 4's additional SDK dependencies when supplied.

## Operational readiness

`GET /health` returns `{"status":"ready","analysis_mode":"mock"}` (or real).
Ready means the configured snapshot loaded and passed startup checks, not
verified analytics or an available external LLM. Missing/invalid real data
fails startup. Both Docker and Compose health checks use this endpoint.

Health is outside `/api` and excluded from product Swagger. The five product
endpoints and their response fields are unchanged. Missing AI leaves core
readiness healthy and chat returns the documented `cannot_determine` fallback.

## Configuration and mounts

`deployment.env.example` is an optional non-secret template for Person 5.
Compose reads shell variables or root `.env`; it does not automatically read
this example file. Do not commit credentials or host `.env`.

| Setting | Overlay behavior |
| --- | --- |
| `ANALYSIS_MODE` | Default mock; real after candidate verification |
| `ANALYSIS_HOST_PATH` | Host file; default backend synthetic fixture |
| `ANALYSIS_PATH` | Fixed container target `/snapshot/analysis.json` |
| `CORS_ORIGINS` | Default `http://localhost:3000` |
| `CHAT_SERVICE` | Unset until Person 4 supplies the async callable |
| `CHAT_TIMEOUT_SECONDS` | Default 20; finite positive seconds |
| `BACKEND_URL` | Dashboard uses `http://product-backend:8001` |

Long-form bind mounts are read-only and disable automatic host-path creation.
A missing file fails explicitly. Relative paths resolve from the first/root
Compose file; always keep that file first in the command.

After Person 1 supplies a compatible candidate:

```bash
.venv/bin/python -m backend.validate_analysis generated/analysis.json --check-api
ANALYSIS_MODE=real ANALYSIS_HOST_PATH=./generated/analysis.json docker compose -f docker-compose.yml -f backend/compose.integration.yml up --build
```

No generator runs during build/startup. Real analysis stays local, ignored by
Git and excluded from image context, mounted read-only. Restart/recreate after
snapshot replacement. Summary-only adoption and layout adaptation remain
available as described in `ANALYTICS_INTEGRATION.md`.

## Person 4 and official service

Obtain actual API/MCP transport, hostname, credentials, and model settings from
Person 4. API and MCP endpoints are not assumed interchangeable. Person 5 adds
the official service at `:8000` once those requirements are known and supplies
its Compose hostname to the backend. Container localhost refers to itself.

Configure the agreed `CHAT_SERVICE` export and provider-specific environment
settings explicitly; no SDK, endpoint, or secret name is guessed here.
Do not make core health depend on external AI availability.

## Person 5 adoption checklist

1. Review the overlay, environment example, health endpoint, and runtime lock.
2. Merge backend wiring into root Compose for final one-command startup.
3. Coordinate Person 3's actual API client and verify UI drill-down/pagination.
4. Add official API/MCP and Person 4's service; verify grounded answers and
   unavailable/timeout behavior with core numbers still usable.
5. Adopt Person 1's candidate after backend compatibility and analytics-method
   checks; do not treat schema validity as verified savings.
6. Run full Compose E2E and fresh-clone checks, documenting data prerequisites
   separately from service startup. Packaging alone is not submission DoD.

## Verification performed

- 122 backend tests passed; health remains independent of absent AI, with five
  product paths in Swagger.
- Merged Compose configuration validated with `config --quiet`.
- Backend image built successfully with pinned Linux/arm64 dependencies.
- Temporary image container ran with read-only root filesystem and read-only
  snapshot bind mount; Docker reported healthy and mount writable=false.
- Live HTTP checks inside that container passed: health, all five product APIs,
  pagination, job/raw evidence, fallback, and Swagger paths.
- Verified UID 10001, absent pytest/test files, and absent data/generated folders.
  Temporary container was stopped and automatically removed after checks.
- Full dashboard Compose startup, frontend API consumption, real analysis,
  actual AI evidence, and fresh-clone E2E remain unverified.

Build filtering and path resolution follow Docker's documented
[build contexts](https://docs.docker.com/build/concepts/context/) and
[Compose merge rules](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/).
