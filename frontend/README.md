# CutScope Streamlit frontend

The dashboard reads the four GET endpoints in API_CONTRACT.md and preserves the
floating Copilot's POST /api/chat. No analytical values are calculated locally.
Null numeric values display as an em dash; zero remains zero.

## Run

From the repository root, with frontend/requirements.txt installed:

```sh
API_BASE_URL=http://localhost:8001 .venv/bin/python -m streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 3000
```

The existing root Compose sets API_BASE_URL=http://backend:8001. All transport
functions use _api_base_url(); the default is http://localhost:8001.
GET responses are cached for 30 seconds per server/resource/ID. Refresh data
clears this cache. Chat requests are not cached. Selections and chat history
survive reruns using session_state.

The three tiles show allocation/outcomes, the selected opportunity's savings,
and its cost-if-wrong range. Job evidence loads one selected integer ID from
detail.jobs via GET /api/jobs/{job_id}, with the returned findings shown separately.
Backend failures display friendly errors without hiding the Copilot. A job list
that disagrees with the shared contract is reported rather than silently adapted.
The existing Copilot retains its explicitly labeled local mock fallback.

The frontend does not establish whether the backend is serving mock or real
analysis. Check the backend's ANALYSIS_MODE before interpreting the numbers.

## Tests

```sh
.venv/bin/python -m unittest discover -s frontend/tests -v
```

Tests use synthetic contract-shaped responses, covering all endpoint URLs,
null versus zero, ranges, integer-ID drilldown, empty lists, backend errors,
contract mismatch and Copilot opening/closing. Shared contract unchanged.
