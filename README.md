# GoldenBearHacka2

CutScope is an AI GPU Efficiency Command Center for MantisGrid Track 2.

Shared contracts and team rules:

- `PROJECT_SPEC.md`
- `API_CONTRACT.md`
- `ANALYSIS_METHOD.md`
- `TEAM_INTEGRATION_RULES.md`
- `fixtures/analysis.mock.json`

The current `main` branch contains a Streamlit prototype. Feature modules are
integrated through the five endpoints frozen in `API_CONTRACT.md`.

## Run with Docker (submission workflow)

Docker Desktop must be installed and running. From the repository root, start
the complete application with one command after preparing the analytics snapshot.
The backend defaults to real mode and reads a read-only mounted snapshot.
For the merged four-opportunity analysis:

```bash
mkdir -p generated
# Preserve any existing analysis.json before replacing it with this version.
cp analytics/CutScope_analysis.json generated/analysis.json
```

Alternatively, generate a fresh snapshot from your local official data:

```bash
.venv/bin/python -m analytics.build_analysis --data-dir "/path/to/official/data" --with-opportunities
```

Validate it using the backend development dependencies, then start the services:

```bash
.venv/bin/python -m backend.validate_analysis generated/analysis.json --check-api
docker compose up
```

Check <http://localhost:8001/health> for `analysis_mode: real` and
<http://localhost:8001/api/opportunities> for the ranked analytics results.
The Streamlit entry point remains a layout preview pending dashboard API integration.
Missing or invalid input fails explicitly; it does not fall back to mock data.
After replacing the snapshot, recreate the backend to remount the file:

```bash
docker compose up -d --force-recreate backend
```

Use another host snapshot via `ANALYSIS_HOST_PATH=/absolute/path/analysis.json`.
For explicitly synthetic development data:

```bash
ANALYSIS_MODE=mock ANALYSIS_HOST_PATH=./backend/fixtures/analysis.stage1.mock.json docker compose up
```

Open the dashboard at:

<http://localhost:3000>

Stop the application with `Control + C`, or run:

```bash
docker compose down
```

The Docker workflow is the submission entry point used by the judges.

## Run locally without Docker (development workflow)

### First-time setup

Open Terminal and run:

```bash
cd ~/Documents/Codex/hackathon/GoldenBearHacka2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Start the dashboard locally

From the project directory, start the dashboard with one command:

```bash
python3 run_dashboard.py
```

If you are not in the project directory, use:

```bash
python3 ~/Documents/Codex/hackathon/GoldenBearHacka2/run_dashboard.py
```

Streamlit should open the dashboard automatically. If it does not, open:

<http://localhost:8501>

Keep the Terminal window running while using the dashboard. Closing the window
or pressing `Control + C` stops the local server.

### Stop the dashboard

Press `Control + C` in the Terminal window running Streamlit.

## Integration smoke tests

With the current dashboard running:

```bash
python tests/e2e/smoke_test.py --services dashboard
```

After the Product Backend is merged and running on port `8001`:

```bash
python tests/e2e/smoke_test.py --services all
```
