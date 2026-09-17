# Stage 3: Person 4 Copilot interface and Person 5 handoff

Status: Person 2's HTTP adapter and failure handling are implemented and tested.
Person 4's `mantisgrid_client.py`, `context_builder.py`, `llm.py`, and
`grounding.py` are still empty and were not changed. Actual AI/MantisGrid
integration, evidence grounding, and the full Stage 3 exit condition remain
pending Person 4's implementation. Shared specification, contract, methodology,
and fixture files remain empty; decisions below are implementation defaults
for team review, not an approved shared contract.

## Product endpoint

`POST /api/chat` accepts only:

```json
{
  "question": "Why is this recoverable?",
  "opportunity_id": "idle-interactive",
  "job_id": 123
}
```

- `question` is required, must be a string of 1–4000 characters, and is trimmed.
  Whitespace-only questions are rejected. The length bound applies before
  trimming. This bound is a proposed operational default for the shared contract.
- Both IDs are optional and default to null. Neither ID means a summary-scoped
  question; either can be supplied on its own.
- Unknown IDs return the existing 404 resource-specific errors.
- If both IDs exist but the job is not in the opportunity's affected-job list,
  return 422 `JOB_OPPORTUNITY_MISMATCH` with `retryable=false`.
- Extra client fields, including raw telemetry or fabricated analysis values,
  are rejected with 422 `VALIDATION_ERROR` before the AI service is called.
- Normal POST requests and JSON preflight are supported by configured CORS.

Response fields follow the project description:

```text
answer: nonempty string
evidence: JSON object[]
risk: string
recommendation: string
confidence: 0–1 or null
finding_ids: nonempty whitespace-free string[]
job_ids: nonnegative integer[]
caveats: string[]
```

All response fields are required. Extra fields are rejected. Evidence objects
remain opaque until Person 4 provides the official schema, but must be finite,
JSON-serializable data. A model instance is revalidated rather than assumed
valid. Stored sample/opportunity caveats and an explicit mock-mode notice are
appended when missing; other provider response fields are preserved.

## Callable boundary for Person 4

Export an async callable from an owner-controlled module, for example
`backend.services.llm:answer_chat`, with this signature:

```python
from backend.models import ChatResponse
from backend.services.chat_adapter import ChatContext

# Signature only; Person 4 implements the body and evidence-grounding logic.
async def answer_chat(*, question: str, context: ChatContext) -> ChatResponse | dict:
    ...
```

The backend resolves client IDs against its loaded snapshot before calling the
service. `ChatContext` contains:

| Attribute | Authoritative data |
| --- | --- |
| `summary` | Defensive-copy Summary model, including pricing and sample caveat |
| `opportunity` | Full selected opportunity dictionary or null, including all affected jobs, not a page |
| `job` | Full selected job dictionary or null, including stored findings |
| `analysis_mode` | Explicit mock or real mode |
| `analysis` | Read-only lookup interface returning defensive copies |

The lookup interface exposes `get_summary()`, `get_pricing()`,
`list_opportunities()`, `get_opportunity(id)`, and `get_job(id)`. It has no
reload or replacement operation. Service-owned dictionaries and summary
collections can be changed without changing the stored analysis snapshot.

Person 4 builds the AI prompt/context inside their `context_builder.py`, using
these authoritative records and actual MantisGrid tool returns. Person 2 does
not implement those prompts, calls, or grounding in the adapter.

Person 4's implementation must:

- Use actual MantisGrid API/MCP evidence; select findings, causal, and rules
  tools as appropriate. Do not hardcode synthetic fixture IDs as live evidence.
- Explain stored numbers without computing or inventing new dollars,
  GPU-hours, savings percentages, or verified claims.
- Keep observed facts distinct from recommendation judgments.
- Validate finding/job references against the evidence actually used; verify
  root causes with causal evidence when available.
- Return `cannot_determine` with confidence/caveats when evidence is insufficient.
- Respect mock mode and disclose synthetic analysis.
- Use async network calls with upstream request timeouts. Release resources
  and propagate cancellation; do not block the event loop or swallow cancellation.
- Return the complete response shape, with grounded evidence, risk, action,
  confidence, and caveats. Provider-specific deterministic analytical fallback
  content remains Person 4's responsibility.

The adapter only checks response shape and basic job references. Cited jobs
must exist; when an opportunity is selected, they must be affected jobs in that
opportunity. With only a selected job, citations must refer to that job. With
neither selection, any existing job may be cited. Finding IDs may originate
from live MantisGrid and need not be in the snapshot; verifying them and the
answer's factual/numeric grounding belongs to Person 4. The adapter's checks
are not a replacement for `grounding.py`.

## Optional-service configuration

| Setting | Default | Behavior |
| --- | --- | --- |
| `CHAT_SERVICE` | Unset | `python.module:async_callable`; no configured service means unavailable fallback |
| `CHAT_TIMEOUT_SECONDS` | `20` | Finite positive timeout in seconds |

Example after Person 4 supplies the export:

```bash
CHAT_SERVICE=backend.services.llm:answer_chat CHAT_TIMEOUT_SECONDS=20 .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

The callable loads once at startup; restart after changing settings or code.
A missing module/export, import failure, or synchronous callable results in
unavailable Copilot and does not prevent core read APIs from starting. Invalid
timeout configuration is an explicit operator configuration error. Upstream
URLs, transport, model selection, credentials, and their environment variable
names remain Person 4's responsibility; none are guessed here.

The adapter uses Python's documented
[asyncio.wait_for](https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for).
Its timeout is cooperative: it cancels the service and waits for cancellation.
A blocking service or one that suppresses cancellation can exceed the timeout,
so Person 4 must also enforce timeouts in its network clients.

## Failure behavior

An unavailable service, timeout, provider exception, invalid response, or
invalid cited job produces HTTP 200 with a structured ChatResponse:

- Answer starts with `cannot_determine`.
- Evidence and finding/job citations are empty.
- Confidence is null, never an invented zero or certainty.
- Risk cannot be determined, and no analytical/financial recommendation is generated.
- Caveats explain the failure category and sample/mock scope without exposing
  raw upstream messages, keys, traces, or internal paths.

HTTP 200 allows the Copilot panel to display a valid fallback response while
the dashboard continues to function. Client errors remain HTTP 404/422 with
the existing error envelope. Provider failures do not disable any read API.
No retry loop is added; UI may allow a new user-triggered question.

Default behavior can be checked without credentials:

```bash
curl -X POST http://localhost:8001/api/chat -H 'Content-Type: application/json' -d '{"question":"Why is this recoverable?","opportunity_id":"idle-interactive","job_id":123}'
```

Until a real service is configured this returns `cannot_determine`; it is not
an AI demo or proof of actual MantisGrid evidence.

## Person 5 integration checklist

1. Review request defaults, length limit, mismatch code, nullable confidence,
   opaque evidence shape, and HTTP-200 fallback with Persons 3 and 4; synchronize
   the shared contract and client models.
2. Have Person 4 provide the callable above, or add a small compatibility
   wrapper in their service module preserving this adapter boundary.
3. Set `CHAT_SERVICE` and timeout in later Compose/environment wiring; obtain
   actual MantisGrid/LLM settings from Person 4.
4. Run the three first-slice questions: recoverability, cost-if-wrong, and
   supporting evidence. Verify actual tool calls and grounded references.
5. Repeat with credentials/upstream service unavailable, service timeout, and
   insufficient evidence. Verify the Copilot panel displays fallback and all
   core numbers/drill-downs stay usable.
6. Mark live integration complete only after actual Person 4 service and
   MantisGrid evidence pass; stub tests alone do not satisfy the project DoD.

## Verification and changed scope

Backend tests exercise authoritative context selection, service-copy isolation,
three fixture-based preset questions, configurable service import, selection
variants, unknown/mismatched IDs, rejected telemetry, malformed JSON, timeouts
with cancellation, provider exceptions, invalid references/responses, finite
evidence, CORS, Swagger, and read-API independence. Test stubs exist only in
tests; no mock AI provider is shipped as the production service.

Stage 3 changes are limited to backend models/settings, main application wiring,
chat route, new `chat_adapter.py`, tests, and backend documentation. Person 4's
four files and grounding tests, root contracts, shared fixtures, frontend, and
Compose remain unchanged. No new framework, database, service, RAG, or financial
calculation is introduced.
