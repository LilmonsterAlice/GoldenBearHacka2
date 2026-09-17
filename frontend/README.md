# CutScope Streamlit frontend

Current stage: layout shell only, authorized before shared documents arrive.
Only `frontend/` is modified. There are no fabricated analytical values, API
payloads, or API calls from the page. All unavailable values display as an em dash.

Run from the repository root using the existing environment:

```sh
.venv/bin/python -m streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 3000 --browser.gatherUsageStats false
```

For a local-only preview, use `--server.address 127.0.0.1` instead.
The integration owner must wire this entry point into the root Docker setup;
the existing root app is not changed by this work.

Before connecting data, read PROJECT_SPEC.md, API_CONTRACT.md,
ANALYSIS_METHOD.md and fixtures/analysis.mock.json completely. These files were
absent when this shell was created. Do not infer missing response shapes.

Next stage: agreed mock and page integration, with bounded GET caching via
st.cache_data. Chat submissions must not be cached. Preserve opportunity
selection and chat history in st.session_state. The shared contract remains unchanged.

## Backend connection

All five transport functions in `services/api_client.py` use `API_BASE_URL`.
Default: `http://localhost:8001`. Person 5 should set
`API_BASE_URL=http://backend:8001` on the frontend service in Docker Compose.
The value is read at request time; trailing slashes are normalized.
The page is still a layout shell and does not call the client yet.
Requests have bounded timeouts and propagate HTTP errors for the UI to handle.
No endpoint or response schema was changed.

Run client tests from the repository root:

```sh
.venv/bin/python -m unittest discover -s frontend/tests -v
```
