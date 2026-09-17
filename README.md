# GoldenBearHacka2

## Run the Streamlit dashboard

### First-time setup

Open Terminal and run:

```bash
cd ~/Documents/Codex/hackathon/GoldenBearHacka2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Start the dashboard

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
