# CutScope Streamlit frontend

Current stage: layout shell only, authorized before shared documents arrive.
Only `frontend/` is modified. There are no fabricated analytical values, API
payloads, or API calls. All unavailable values display as an em dash.

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

Next stage: agreed mock, then BACKEND_URL client with bounded GET caching via
st.cache_data. Chat submissions must not be cached. Preserve opportunity
selection and chat history in st.session_state. The shared contract remains unchanged.
