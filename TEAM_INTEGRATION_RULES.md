# Team Integration Rules v1.0

1. Everyone works in the same repository on their assigned branch.
2. Read `PROJECT_SPEC.md`, `API_CONTRACT.md`, `ANALYSIS_METHOD.md`, and the shared
   fixture before editing code.
3. Modify only the assigned module unless an owner approves otherwise.
4. Do not silently rename endpoints, fields, enums, or null semantics.
5. Contract changes require an impact statement and Person 2/5 approval.
6. Never commit official data, generated datasets, `.env`, or secrets.
7. The first vertical slice is `idle-interactive-session`.
8. Frontend develops against the shared mock and does not wait for real data.
9. Integrate a runnable slice every 45–60 minutes.
10. Every handoff reports changed files, tests, assumptions, limitations,
    integration steps, and whether the contract changed.

## Branches

```text
feature/data-analysis
feature/product-api
feature/frontend-dashboard
feature/ai-copilot
integration
```

Feature branches must incorporate the current `main` baseline before development.
PRs merge into `integration` for E2E verification before `main`.

## First integration acceptance

- Product endpoints match `API_CONTRACT.md`.
- Savings are not double-counted.
- Values include units/source, range, confidence, and caveat.
- AI cites finding/job IDs and fails safely.
- `docker compose up` ultimately serves the dashboard on port `3000`.
